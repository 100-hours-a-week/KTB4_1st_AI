# service.py
import json

from features.moderation.exceptions import ModerationProcessingException
from features.moderation.prompts import MODERATION_PROMPT
from features.moderation.rule_filter import RuleViolation, run_rule_filter
from features.moderation.schemas import ModerationResponse
from shared.llm.claude_provider import ClaudeTransientError, generate


def _extract_json(raw_text: str) -> dict:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("응답에 JSON이 없습니다.")
    return json.loads(raw_text[start : end + 1])


async def _call_claude_moderation(title: str, content: str) -> dict:
    prompt = f"{MODERATION_PROMPT}\n\n제목: {title}\n내용: {content}"
    last_error: Exception | None = None

    for _ in range(2):
        try:
            raw_text = await generate(prompt=prompt)
            return _extract_json(raw_text)
        except ClaudeTransientError as error:
            raise ModerationProcessingException() from error
        except Exception as error:  # noqa: BLE001
            last_error = error

    raise ModerationProcessingException() from last_error


async def check_text(title: str, content: str) -> ModerationResponse:
    try:
        run_rule_filter(title, content)
    except RuleViolation as violation:
        return ModerationResponse(
            isAppropriate=False,
            rejectionReason=violation.reason,
            keyword=None,
        )

    result = await _call_claude_moderation(title, content)

    try:
        is_appropriate = result["isAppropriate"]
        rejection_reason = result.get("rejectionReason")
        keyword = result.get("keyword")
    except (KeyError, TypeError) as error:
        raise ModerationProcessingException() from error

    if not isinstance(is_appropriate, bool):
        raise ModerationProcessingException()

    if not is_appropriate:
        return ModerationResponse(
            isAppropriate=False, rejectionReason=rejection_reason, keyword=None
        )

    if not keyword:
        raise ModerationProcessingException()

    return ModerationResponse(isAppropriate=True, rejectionReason=None, keyword=keyword)
