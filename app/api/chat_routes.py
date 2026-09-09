from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.schemas.chat_schema import (
    ChatRequest,
    ChatResponse
)
from app.services.rag_service import ask_question

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)
print("✅ chat_routes.py loaded")

@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):

    result = ask_question(
        db=db,
        session_id=request.session_id,
        question=request.question
    )

    return ChatResponse(
        session_id=result["session_id"],
        answer=result["answer"],
        sources=result["sources"]
    )