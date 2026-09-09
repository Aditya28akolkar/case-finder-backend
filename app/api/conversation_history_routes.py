from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.services.conversation_history_service import (
    get_conversation_history,
    delete_conversation_history
)

router = APIRouter(
    prefix="/conversation-history",
    tags=["Conversation History"]
)


@router.get("/{session_id}")
def get_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    return get_conversation_history(
        db=db,
        session_id=session_id
    )


@router.delete("/{session_id}")
def delete_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    return delete_conversation_history(
        db=db,
        session_id=session_id
    )