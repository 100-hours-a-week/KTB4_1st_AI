# router.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from features.smart_search.exceptions import SmartSearchException
from features.smart_search.schemas import RankCandidatesRequest, RankCandidatesResponse
from features.smart_search.service import rank_candidates_by_preference

router = APIRouter(tags=["smart-search"])


@router.post(
    "/api/search/rank-candidates",
    response_model=RankCandidatesResponse,
)
async def rank_candidates(request: RankCandidatesRequest):
    try:
        results = await rank_candidates_by_preference(
            request.candidates,
            request.preferenceText,
        )
        return {"results": results}
    except SmartSearchException as error:
        return JSONResponse(
            status_code=500,
            content={"error": error.error, "message": error.message},
        )
