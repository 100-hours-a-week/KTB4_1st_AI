# router.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from features.moderation.exceptions import (
    ModerationMissingContentException,
    ModerationMissingTitleException,
    ModerationProcessingException,
)
from features.moderation.schemas import ModerationRequest, ModerationResponse
from features.moderation.service import check_text

router = APIRouter(prefix="/api/moderation", tags=["moderation"])


@router.post("/check-text", response_model=ModerationResponse)
async def check_text_endpoint(request: ModerationRequest):
    try:
        if not request.title:
            raise ModerationMissingTitleException()
        if not request.content:
            raise ModerationMissingContentException()

        return await check_text(request.title, request.content)

    except (
        ModerationMissingTitleException,
        ModerationMissingContentException,
    ) as error:
        return JSONResponse(
            status_code=400, content={"error": error.error, "message": error.message}
        )
    except ModerationProcessingException as error:
        return JSONResponse(
            status_code=500, content={"error": error.error, "message": error.message}
        )
