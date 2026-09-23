# claude_provider.py
import asyncio
import base64

import anthropic
from anthropic import AsyncAnthropic

from core.config import settings

client = AsyncAnthropic(
    api_key=settings.anthropic_api_key,
    timeout=settings.claude_timeout,
    max_retries=0,
)


class ClaudeTransientError(Exception):
    pass


async def _call_with_retry(**request) -> anthropic.types.Message:
    last_error: Exception | None = None
    for attempt in range(settings.claude_max_retries + 1):
        try:
            return await client.messages.create(**request)
        except (
            anthropic.RateLimitError,
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
            anthropic.InternalServerError,
        ) as error:
            last_error = error
            if attempt < settings.claude_max_retries:
                await asyncio.sleep(2**attempt)
    raise ClaudeTransientError() from last_error


async def generate(
    prompt: str,
    images: list[bytes] | None = None,
    content_types: list[str] | None = None,
    model: str = settings.claude_model_sonnet,
    max_tokens: int = settings.claude_max_tokens,
) -> str:
    content: list[dict] = []

    if images:
        if not content_types or len(content_types) != len(images):
            raise ValueError("images와 content_types의 개수가 일치해야 합니다.")

        for image_bytes, content_type in zip(images, content_types):
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": content_type,
                        "data": base64.b64encode(image_bytes).decode("utf-8"),
                    },
                }
            )

    content.append({"type": "text", "text": prompt})

    response = await _call_with_retry(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
    )

    text_blocks = [block.text for block in response.content if block.type == "text"]
    if not text_blocks:
        raise RuntimeError("Claude 응답에 텍스트가 없습니다.")
    return "".join(text_blocks)


async def generate_with_web_search(
    prompt: str,
    model: str = settings.claude_model_sonnet,
    max_tokens: int = settings.claude_max_tokens,
    max_uses: int = 5,
) -> str:
    response = await _call_with_retry(
        model=model,
        max_tokens=max_tokens,
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_uses,
            }
        ],
        messages=[{"role": "user", "content": prompt}],
    )

    text_blocks = [block.text for block in response.content if block.type == "text"]
    if not text_blocks:
        raise RuntimeError("Claude 응답에 텍스트가 없습니다.")
    return "".join(text_blocks)
