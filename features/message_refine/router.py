import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.config import settings
from features.message_refine.exceptions import (
    MessageRefineException,
    UnrefinableMessageError,
)
from features.message_refine.schemas import (
    MessageRefineRequest,
    MessageRefineResponse,
)
from features.message_refine.service import refine_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/message-refine/refine", response_model=MessageRefineResponse)
async def refine(
    request: MessageRefineRequest,
) -> MessageRefineResponse | JSONResponse:
    if not request.message.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "empty_message", "message": "메시지를 입력해주세요"},
        )
    if not any(char.isalnum() for char in request.message):
        return JSONResponse(
            status_code=400,
            content={
                "error": UnrefinableMessageError.error,
                "message": UnrefinableMessageError.message,
            },
        )
    if len(request.message) > settings.message_refine_max_length:
        return JSONResponse(
            status_code=400,
            content={"error": "message_too_long", "message": "메시지가 너무 길어요"},
        )
    try:
        return await refine_message(request)
    except UnrefinableMessageError as error:
        logger.warning(
            "message_refine 다듬을 수 없는 입력: stage=%s detail=%s",
            error.stage,
            error.detail,
        )
        return JSONResponse(
            status_code=400, content={"error": error.error, "message": error.message}
        )
    except MessageRefineException as error:
        logger.error(
            "message_refine 실패: stage=%s error=%s detail=%s",
            error.stage,
            error.error,
            error.detail,
        )
        return JSONResponse(
            status_code=500, content={"error": error.error, "message": error.message}
        )
