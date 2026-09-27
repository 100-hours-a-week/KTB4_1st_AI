# image_loader.py
import httpx2

from features.vision.exceptions import (
    VisionFileTooLargeException,
    VisionInvalidInputException,
    VisionProcessingException,
)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024
DOWNLOAD_TIMEOUT = 10.0


def _guess_content_type_from_url(url: str) -> str:
    path = url.split("?")[0].lower()
    if path.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if path.endswith(".png"):
        return "image/png"
    if path.endswith(".webp"):
        return "image/webp"
    return "application/octet-stream"


async def _fetch_one(client: httpx2.AsyncClient, url: str) -> tuple[bytes, str]:
    try:
        async with client.stream("GET", url) as response:
            response.raise_for_status()

            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > MAX_FILE_SIZE:
                    raise VisionFileTooLargeException()
                chunks.append(chunk)

            content = b"".join(chunks)

            content_type = (
                response.headers.get("content-type", "").split(";")[0].strip()
            )
            if content_type not in ALLOWED_CONTENT_TYPES:
                content_type = _guess_content_type_from_url(url)
            if content_type not in ALLOWED_CONTENT_TYPES:
                raise VisionInvalidInputException()

            return content, content_type
    except httpx2.HTTPError as error:
        raise VisionProcessingException() from error


async def fetch_images(urls: list[str]) -> tuple[list[bytes], list[str]]:
    image_bytes_list: list[bytes] = []
    content_types: list[str] = []

    async with httpx2.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
        for url in urls:
            content, content_type = await _fetch_one(client, url)
            image_bytes_list.append(content)
            content_types.append(content_type)

    return image_bytes_list, content_types
