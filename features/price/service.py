# service.py
import json

from features.price.exceptions import PriceEstimationException
from features.price.prompts import PRICE_ESTIMATE_PROMPT
from features.price.schemas import PriceEstimateRequest, PriceEstimateResponse
from shared.llm.claude_provider import ClaudeTransientError, generate_with_web_search

K_SKEW = 0.15  # 근거 약함: 클리어런스 마크다운 1단계(25%)의 60% 수준 — 생필품 특화 데이터 없음
K_SPREAD = 0.19  # 근거: Kaplan & Menzio (2014, NBER WP 19877) Table 2, UPC 기준 가격 표준편차 19%


def calculate_price_range(
    unit_price: int, value_tolerance: float, trade_speed: float
) -> tuple[int, int]:
    discount_ratio = value_tolerance * K_SPREAD + trade_speed * K_SKEW
    min_price = round(unit_price * (1 - discount_ratio))
    min_price = max(min_price, 0)
    return min_price, unit_price


async def call_claude_price(request: PriceEstimateRequest) -> dict:
    last_error: Exception | None = None

    for _ in range(2):
        try:
            raw_text = await generate_with_web_search(
                prompt=PRICE_ESTIMATE_PROMPT.format(
                    title=request.title,
                    content=request.content,
                )
            )
            return json.loads(raw_text)
        except ClaudeTransientError as error:
            raise PriceEstimationException() from error
        except Exception as error:  # noqa: BLE001
            last_error = error

    raise PriceEstimationException() from last_error


async def estimate_price(request: PriceEstimateRequest) -> PriceEstimateResponse:
    if request.keyword is not None and request.unitPrice is not None:
        keyword = request.keyword
        unit_price = request.unitPrice
    else:
        result = await call_claude_price(request)

        try:
            keyword = result["keyword"]
            unit_price = result["referenceUnitPrice"]
        except (KeyError, TypeError) as error:
            raise PriceEstimationException() from error

        if not isinstance(unit_price, int):
            raise PriceEstimationException()

    min_unit_price, max_unit_price = calculate_price_range(
        unit_price, request.valueTolerance, request.tradeSpeed
    )

    return PriceEstimateResponse(
        keyword=keyword,
        unitPrice=unit_price,
        minUnitPrice=min_unit_price,
        maxUnitPrice=max_unit_price,
    )
