from fastapi import APIRouter
from fastapi.responses import JSONResponse

from features.price.exceptions import PriceEstimationException
from features.price.schemas import PriceEstimateRequest, PriceEstimateResponse
from features.price.service import estimate_price

router = APIRouter()


@router.post("/value/estimate-price", response_model=PriceEstimateResponse)
async def price_estimate(
    request: PriceEstimateRequest,
) -> PriceEstimateResponse | JSONResponse:
    if not (0 <= request.valueTolerance <= 1) or not (0 <= request.tradeSpeed <= 1):
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_input",
                "message": "valueTolerance와 tradeSpeed는 0~1 사이여야 합니다.",
            },
        )

    has_cached = request.keyword is not None and request.unitPrice is not None
    has_uncached = request.title is not None and request.content is not None

    if not has_cached and not has_uncached:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_input",
                "message": "keyword+unitPrice 또는 title+content 중 하나는 반드시 있어야 합니다.",
            },
        )

    try:
        return await estimate_price(request)
    except PriceEstimationException as error:
        return JSONResponse(
            status_code=500, content={"error": error.error, "message": error.message}
        )
