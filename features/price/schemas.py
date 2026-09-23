from pydantic import BaseModel


class PriceEstimateRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    keyword: str | None = None
    unitPrice: int | None = None
    valueTolerance: float
    tradeSpeed: float


class PriceEstimateResponse(BaseModel):
    keyword: str
    unitPrice: int
    minUnitPrice: int
    maxUnitPrice: int
