# schemas.py
from pydantic import BaseModel


class ModerationRequest(BaseModel):
    title: str
    content: str


class ModerationResponse(BaseModel):
    isAppropriate: bool
    rejectionReason: str | None
    keyword: str | None


class ErrorResponse(BaseModel):
    error: str
    message: str
