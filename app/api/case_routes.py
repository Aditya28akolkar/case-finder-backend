from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.db.session import get_db

from app.schemas.case_schema import (
    ChatRequest,
    ChatResponse
)

from app.chat.chat_service import chat_with_case

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):

    answer = chat_with_case(
        db,
        request.case_id,
        request.question
    )

    return ChatResponse(answer=answer)