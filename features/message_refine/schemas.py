from pydantic import BaseModel


class PreferenceAnswer(BaseModel):
    question: str
    answer: str


class MessageRefineRequest(BaseModel):
    message: str
    answers: list[PreferenceAnswer] = []


class MessageRefineResponse(BaseModel):
    refined: str
