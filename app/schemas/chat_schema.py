from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=3, max_length=100)
    question: str = Field(..., min_length=5, max_length=1000)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list