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
    if not (0 <= request.valueGapToleranceScore <= 1) or not (
        0 <= request.exchangeUrgencyScore <= 1
    ):
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_input",
                "message": "valueGapToleranceScore와 exchangeUrgencyScore는 0~1 사이여야 합니다.",
            },
        )

    try:
        return await estimate_price(request)
    except PriceEstimationException as error:
        return JSONResponse(
            status_code=500, content={"error": error.error, "message": error.message}
        )