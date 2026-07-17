from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CaseCreate(BaseModel):
    title: str
    citation: Optional[str] = None
    court: Optional[str] = None
    judge: Optional[str] = None
    summary: Optional[str] = None
    full_text: Optional[str] = None
    source: Optional[str] = None


class CaseUpdate(BaseModel):
    title: Optional[str] = None
    citation: Optional[str] = None
    court: Optional[str] = None
    judge: Optional[str] = None
    summary: Optional[str] = None
    full_text: Optional[str] = None
    source: Optional[str] = None


class CaseResponse(BaseModel):
    id: int
    title: str
    citation: Optional[str]
    court: Optional[str]
    judge: Optional[str]
    summary: Optional[str]
    full_text: Optional[str]
    source: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CaseSearchRequest(BaseModel):
    query: str
    top_k: int = 10


class ChatRequest(BaseModel):
    session_id: str
    question: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list