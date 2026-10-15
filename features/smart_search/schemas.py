# schemas.py
from pydantic import BaseModel


class Candidate(BaseModel):
    itemId: int
    title: str


class RankCandidatesRequest(BaseModel):
    candidates: list[Candidate]
    preferenceText: str | None = None


class RankCandidatesResponse(BaseModel):
    results: list[int]


class ErrorResponse(BaseModel):
    error: str
    message: str
