import asyncio
import logging
import time

import httpx2

from core.config import settings
from features.message_refine.exceptions import (
    InvalidRefineResponseError,
    RefineServerApiError,
    RefineServerAuthError,
    RefineServerConnectionError,
    RefineServerOverloadedError,
    RefineServerTimeoutError,
)
from features.message_refine.schemas import (
    MessageRefineRequest,
    MessageRefineResponse,
)

logger = logging.getLogger(__name__)

REFINE_PATH = "/refine"

# 일시적인 오류만 재시도, 인증이나 응답 형식 오류는 재시도 X
RETRYABLE_ERRORS = (
    RefineServerConnectionError,
    RefineServerTimeoutError,
    RefineServerOverloadedError,
)

client = httpx2.AsyncClient(timeout=settings.refine_server_timeout)


# 상태 코드 -> 예외
def _raise_for_status(response: httpx2.Response) -> None:
    status = response.status_code
    if status < 400:
        return
    detail = f"status={status}"
    if status in (401, 403):
        raise RefineServerAuthError(stage="request", detail=detail)
    if status in (429, 503):
        raise RefineServerOverloadedError(stage="request", detail=detail)
    raise RefineServerApiError(stage="request", detail=detail)


# 다듬기 서버에 요청 한 번 보냄
async def _post_refine(payload: dict) -> dict:
    try:
        response = await client.post(
            f"{settings.refine_server_url}{REFINE_PATH}",
            json=payload,
            headers={"Authorization": f"Bearer {settings.refine_server_api_key}"},
        )
    except httpx2.TimeoutException as error:
        raise RefineServerTimeoutError(stage="request") from error
    except httpx2.TransportError as error:
        raise RefineServerConnectionError(
            stage="connect", detail=type(error).__name__
        ) from error
    _raise_for_status(response)

    try:
        return response.json()
    except ValueError as error:
        raise InvalidRefineResponseError(
            stage="validate", detail="응답이 JSON이 아님"
        ) from error


# 응답이 약속한 형식인지 확인하기
def _parse_response(data: object) -> MessageRefineResponse:
    refined = data.get("refined") if isinstance(data, dict) else None
    if not isinstance(refined, str) or not refined.strip():
        raise InvalidRefineResponseError(
            stage="validate", detail="refined 필드가 없거나 비어 있음"
        )
    return MessageRefineResponse(refined=refined)


async def refine_message(request: MessageRefineRequest) -> MessageRefineResponse:
    payload = request.model_dump()
    start = time.perf_counter()

    for attempt in range(settings.refine_server_max_retries + 1):
        try:
            data = await _post_refine(payload)
            break
        except RETRYABLE_ERRORS:
            if attempt >= settings.refine_server_max_retries:
                raise
            await asyncio.sleep(2**attempt)

    logger.info("다듬기 서버 호출 소요 시간: %.2f초", time.perf_counter() - start)
    return _parse_response(data)
