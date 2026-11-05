import asyncio
import logging
import time

import openai
from openai import AsyncOpenAI

from core.config import settings
from features.message_refine.exceptions import (
    InvalidRefineResponseError,
    MessageRefineException,
    RefineServerApiError,
    RefineServerAuthError,
    RefineServerConnectionError,
    RefineServerOverloadedError,
    RefineServerTimeoutError,
)
from features.message_refine.prompts import build_system_prompt
from features.message_refine.schemas import (
    MessageRefineRequest,
    MessageRefineResponse,
)
from shared.llm.claude_provider import ClaudeTransientError, generate

logger = logging.getLogger(__name__)

# 일시적인 오류만 재시도, 인증이나 응답 형식 오류는 재시도 X
RETRYABLE_ERRORS = (
    RefineServerConnectionError,
    RefineServerTimeoutError,
    RefineServerOverloadedError,
)

client = AsyncOpenAI(
    base_url=f"{settings.refine_server_url}/v1",
    api_key=settings.refine_server_api_key or "EMPTY",
    timeout=settings.refine_server_timeout,
    max_retries=0,
)


# SDK 예외 -> 서비스 예외
def _convert_error(error: openai.OpenAIError) -> MessageRefineException:
    if isinstance(error, openai.APITimeoutError):
        return RefineServerTimeoutError(stage="request")
    if isinstance(error, openai.APIConnectionError):
        return RefineServerConnectionError(stage="connect", detail=type(error).__name__)
    if isinstance(error, openai.APIStatusError):
        status = error.status_code
        detail = f"status={status}"
        if status in (401, 403):
            return RefineServerAuthError(stage="request", detail=detail)
        if status in (429, 503):
            return RefineServerOverloadedError(stage="request", detail=detail)
        if status == 502:
            return RefineServerConnectionError(stage="connect", detail=detail)
        if status == 504:
            return RefineServerTimeoutError(stage="request", detail=detail)
        return RefineServerApiError(stage="request", detail=type(error).__name__)
    return RefineServerApiError(stage="request", detail=type(error).__name__)


# RunPod(vLLM)에 요청 한 번 보냄
async def _call_refine_server(system_prompt: str, message: str) -> str:
    try:
        response = await client.chat.completions.create(
            model=settings.refine_server_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0,
            max_tokens=settings.message_refine_max_tokens,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
    except openai.OpenAIError as error:
        raise _convert_error(error) from error

    if not response.choices:
        raise InvalidRefineResponseError(stage="validate", detail="choices가 비어 있음")
    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise InvalidRefineResponseError(stage="validate", detail="출력이 잘림")
    return choice.message.content or ""


# RunPod이 안 될 때 대신 Claude 호출
async def _call_claude(system_prompt: str, message: str) -> str:
    prompt = (
        f"{system_prompt}\n\n"
        "아래 <message> 안의 내용만 다듬어서 출력해.\n"
        f"<message>\n{message}\n</message>"
    )
    try:
        return await generate(
            prompt,
            model=settings.claude_model_haiku,
            max_tokens=settings.message_refine_max_tokens,
        )
    except (ClaudeTransientError, RuntimeError) as error:
        cause = error.__cause__ or error
        raise RefineServerApiError(
            stage="fallback", detail=type(cause).__name__
        ) from error


# 응답이 비어있지 않은지 확인
def _parse_response(text: str) -> MessageRefineResponse:
    refined = text.strip()
    if not refined:
        raise InvalidRefineResponseError(
            stage="validate", detail="다듬어진 메시지가 비어 있음"
        )
    return MessageRefineResponse(refined=refined)


async def _refine_with_retry(system_prompt: str, message: str) -> str:
    for attempt in range(settings.refine_server_max_retries + 1):
        try:
            return await _call_refine_server(system_prompt, message)
        except RETRYABLE_ERRORS:
            if attempt >= settings.refine_server_max_retries:
                raise
            await asyncio.sleep(2**attempt)
    raise AssertionError("unreachable")


async def refine_message(request: MessageRefineRequest) -> MessageRefineResponse:
    styles = {item.question: item.answer for item in request.answers}
    system_prompt = build_system_prompt(styles)
    start = time.perf_counter()
    source = "runpod"

    try:
        text = await _refine_with_retry(system_prompt, request.message)
        result = _parse_response(text)
    except MessageRefineException as error:
        if not settings.refine_fallback_enabled:
            raise
        logger.warning(
            "RunPod 실패, Claude로 대체: stage=%s error=%s detail=%s",
            error.stage,
            error.error,
            error.detail,
        )
        source = "claude"
        try:
            result = _parse_response(await _call_claude(system_prompt, request.message))
        except MessageRefineException as fallback_error:
            logger.error(
                "Claude 대체도 실패: stage=%s error=%s detail=%s",
                fallback_error.stage,
                fallback_error.error,
                fallback_error.detail,
            )
            raise error

    logger.info(
        "다듬기 완료: source=%s 소요 시간=%.2f초", source, time.perf_counter() - start
    )
    return result
