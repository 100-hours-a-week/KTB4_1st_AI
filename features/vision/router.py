# router.py
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from features.vision.exceptions import (
    VisionFileTooLargeException,
    VisionInvalidInputException,
    VisionProcessingException,
)
from features.vision.image_loader import fetch_images
from features.vision.schemas import VisionRequest, VisionResponse
from features.vision.service import analyze_item

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vision", tags=["vision"])

MAX_IMAGES = 3


@router.post("/analyze-item", response_model=VisionResponse)
async def analyze_item_endpoint(request: VisionRequest):
    try:
        image_urls = request.imageUrls

        if not image_urls or len(image_urls) > MAX_IMAGES:
            raise VisionInvalidInputException()

        image_bytes_list, content_types = await fetch_images(image_urls)

        return await analyze_item(images=image_bytes_list, content_types=content_types)

    except VisionInvalidInputException as error:
        return JSONResponse(
            status_code=400, content={"error": error.error, "message": error.message}
        )
    except VisionFileTooLargeException as error:
        return JSONResponse(
            status_code=413, content={"error": error.error, "message": error.message}
        )
    except VisionProcessingException as error:
        logger.error("vision 처리 실패", exc_info=error)
        return JSONResponse(
            status_code=500, content={"error": error.error, "message": error.message}
        )
