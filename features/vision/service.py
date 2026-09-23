# service.py
import json

from features.vision.exceptions import VisionProcessingException
from features.vision.prompts import VISION_ANALYZE_PROMPT
from features.vision.schemas import VisionResponse
from shared.llm.claude_provider import ClaudeTransientError, generate

TITLE_MAX_LENGTH = 30
CONTENT_MAX_LENGTH = 500


def _extract_json(raw_text: str) -> dict:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("응답에 JSON이 없습니다.")
    return json.loads(raw_text[start : end + 1])


async def call_claude_vision(images: list[bytes], content_types: list[str]) -> dict:
    last_error: Exception | None = None

    for _ in range(2):
        try:
            raw_text = await generate(
                prompt=VISION_ANALYZE_PROMPT, images=images, content_types=content_types
            )
            return _extract_json(raw_text)
        except ClaudeTransientError as error:
            raise VisionProcessingException() from error
        except Exception as error:  # noqa: BLE001
            last_error = error

    raise VisionProcessingException() from last_error


async def analyze_item(images: list[bytes], content_types: list[str]) -> VisionResponse:
    result = await call_claude_vision(images, content_types)

    try:
        is_appropriate = result["is_appropriate"]
        is_identifiable = result["is_identifiable"]
        rejection_reason = result["rejection_reason"]
        title = result["title"]
        content = result["content"]
    except (KeyError, TypeError) as error:
        raise VisionProcessingException() from error

    if not isinstance(is_appropriate, bool) or not isinstance(is_identifiable, bool):
        raise VisionProcessingException()

    if not is_appropriate:
        return VisionResponse(
            isAppropriate=False,
            rejectionReason=rejection_reason,
            title=None,
            content=None,
        )

    if not is_identifiable:
        return VisionResponse(
            isAppropriate=True, rejectionReason=None, title=None, content=None
        )

    if title and len(title) > TITLE_MAX_LENGTH:
        title = title[:TITLE_MAX_LENGTH]
    if content and len(content) > CONTENT_MAX_LENGTH:
        content = content[:CONTENT_MAX_LENGTH]

    return VisionResponse(
        isAppropriate=True, rejectionReason=None, title=title, content=content
    )
