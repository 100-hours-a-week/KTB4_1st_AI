import json
import logging

import anthropic

from core.config import settings
from features.chatbot.exceptions import (
    ClaudeApiError,
    ClaudeRateLimitedError,
    ClaudeTimeoutError,
    InvalidModelResponseError,
)
from features.chatbot.prompts import (
    INTENT_CLASSIFY_PROMPT,
    NOT_FOUND_ANSWER,
    OUT_OF_SCOPE_ANSWER,
    POLICY_ANSWER_PROMPT,
    SCREEN_LABELS,
)
from features.chatbot.retriever import retrieve
from features.chatbot.schemas import (
    ChatbotAction,
    ChatbotRequest,
    ChatbotResponse,
    ChatMessage,
    Screen,
)
from shared.llm.claude_provider import ClaudeTransientError, generate

logger = logging.getLogger(__name__)

INTENTS = {"policy", "navigation", "out_of_scope"}


# 이전 대화를 글 하나로 바꾸기
def _format_history(history: list[ChatMessage]) -> str:
    # 대화 목록의 뒤에서 10개만 가져오기
    recent = history[-settings.chatbot_history_limit :]
    if not recent:
        return "(없음)"
    names = {"user": "사용자", "assistant": "챗봇"}
    return "\n".join(
        f"{names.get(item.role, item.role)}: {item.content}" for item in recent
    )


# 응답에서 JSON 뽑기
def _extract_json(raw_text: str) -> dict:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("응답에 JSON이 없습니다.")
    return json.loads(raw_text[start : end + 1])


# Claude 부르고 JSON 돌려받기
async def _call_json(prompt: str, model: str, stage: str) -> dict:
    # Claude 요청 최대 2번 시도
    for attempt in range(2):
        try:
            raw_text = await generate(prompt, model=model)
        except ClaudeTransientError as error:
            cause = error.__cause__
            if isinstance(cause, anthropic.RateLimitError):
                raise ClaudeRateLimitedError(stage=stage) from error
            if isinstance(cause, anthropic.APITimeoutError):
                raise ClaudeTimeoutError(stage=stage) from error
            raise ClaudeApiError(stage=stage, detail=str(cause)) from error
        except RuntimeError as error:
            raise ClaudeApiError(stage=stage, detail=str(error)) from error

        # 응답에서 JSON을 뽑아 보고 성공하면 return, 실패하면 경고 로그만 남김
        try:
            return _extract_json(raw_text)
        except ValueError:
            logger.warning(
                "chatbot JSON 파싱 실패: stage=%s attempt=%s raw=%s",
                stage,
                attempt + 1,
                raw_text[:200],
            )
    raise InvalidModelResponseError(stage=stage)


# 의도 분류
async def _classify(message: str, history_text: str) -> tuple[str, str | None]:
    prompt = INTENT_CLASSIFY_PROMPT.format(history=history_text, message=message)
    result = await _call_json(prompt, settings.claude_model_haiku, "intent")
    intent = result.get("intent")
    # 목록 밖의 값이면 비정상 응답으로 던지기
    if intent not in INTENTS:
        raise InvalidModelResponseError(stage="intent", detail=f"intent={intent}")
    return intent, result.get("screen")


# 화면 이동 버튼 만들기
def _build_action(screen: str | None) -> ChatbotAction | None:
    # 화면 값이 없거나 "null" 문자열이면 버튼 안 만듦
    if not screen or screen == "null":
        return None
    try:
        value = Screen(screen)
    # 목록에 없는 화면 이름은 버튼을 만들지 않음
    except ValueError:
        logger.warning("알 수 없는 화면 값: %s", screen)
        return None
    # 버튼 문구 코드에서 정함
    label = SCREEN_LABELS[value.value]
    return ChatbotAction(label=f"{label} 화면으로 이동", screen=value)


# 정책 질문 처리
async def _answer_policy(message: str, history_text: str) -> ChatbotResponse:
    results = await retrieve(message)
    # 거리가 설정한 값(0.45) 이상이면 Claude 호출 X
    if not results or results[0]["distance"] > settings.chatbot_max_distance:
        return ChatbotResponse(
            answer=NOT_FOUND_ANSWER, action=_build_action(Screen.INQUIRY.value)
        )

    documents = "\n\n".join(f"[{item['title']}]\n{item['content']}" for item in results)
    prompt = POLICY_ANSWER_PROMPT.format(
        documents=documents, history=history_text, message=message
    )
    # 답변 프롬프트 채워서 Claude 호출
    result = await _call_json(prompt, settings.claude_model_sonnet, "answer")
    answer = result.get("answer")
    # 답변이 문자열이 아니거나 비어있으면 예외 처리
    if not isinstance(answer, str) or not answer.strip():
        raise InvalidModelResponseError(stage="answer", detail="answer가 비어 있음")
    # 답변 + 화면버튼으로 응답 돌려줌
    return ChatbotResponse(
        answer=answer.strip(), action=_build_action(result.get("screen"))
    )


# 전체 흐름
async def ask_chatbot(request: ChatbotRequest) -> ChatbotResponse:
    message = request.message.strip()
    history_text = _format_history(request.history)

    intent, screen = await _classify(message, history_text)
    logger.info("chatbot intent=%s screen=%s", intent, screen)

    if intent == "out_of_scope":
        return ChatbotResponse(answer=OUT_OF_SCOPE_ANSWER)

    if intent == "navigation":
        action = _build_action(screen)
        if action is None:
            return ChatbotResponse(answer=OUT_OF_SCOPE_ANSWER)
        label = SCREEN_LABELS[action.screen.value]
        return ChatbotResponse(
            answer=f"{label} 화면으로 이동할 수 있어요.", action=action
        )

    return await _answer_policy(message, history_text)
