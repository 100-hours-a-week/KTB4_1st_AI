import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from features.chatbot.exceptions import ChatbotException
from features.chatbot.schemas import ChatbotRequest, ChatbotResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/chatbot/ask", response_model=ChatbotResponse)
async def ask(request: ChatbotRequest) -> ChatbotResponse | JSONResponse:
    if not request.message.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "empty_message", "message": "메시지를 입력해주세요"},
        )

    try:
        return ChatbotResponse(answer="(임시 응답) 챗봇 연결 확인용입니다.")
    except ChatbotException as error:
        logger.exception(
            "chatbot 실패: stage=%s error=%s detail=%s",
            error.stage,
            error.error,
            error.detail,
        )
        return JSONResponse(
            status_code=500, content={"error": error.error, "message": error.message}
        )
