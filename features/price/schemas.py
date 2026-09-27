from pydantic import BaseModel


class PriceEstimateRequest(BaseModel):
    title: str
    content: str
    valueGapToleranceScore: float
    exchangeUrgencyScore: float


class PriceEstimateResponse(BaseModel):
    keyword: str
    unitPrice: int
    minUnitPrice: int
    maxUnitPrice: int
