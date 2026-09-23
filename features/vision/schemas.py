# schemas.py
from pydantic import BaseModel


class VisionRequest(BaseModel):
    imageUrls: list[str]


class VisionResponse(BaseModel):
    isAppropriate: bool
    rejectionReason: str | None
    title: str | None
    content: str | None


class ErrorResponse(BaseModel):
    error: str
    message: str
