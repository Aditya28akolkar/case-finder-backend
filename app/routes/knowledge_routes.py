
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.rag_service import ask_question
from app.services.conversation_service import (
    get_conversation_history,
    get_all_conversations,
    rename_conversation,
    delete_conversation
)
from app.schemas.knowledge_schema import (
    KnowledgeAskRequest,
    ConversationRenameRequest
)


router = APIRouter(
    prefix="/knowledge",
    tags=["Knowledge"]
)


@router.post("/ask")
def ask_knowledge(
    request: KnowledgeAskRequest,
    db: Session = Depends(get_db)
):

    result = ask_question(
        db=db,
        question=request.question,
        session_id=request.session_id
    )

    return {
        "question": request.question,
        "session_id": request.session_id,
        "answer": result["answer"],
        "sources": result["sources"]
    }


@router.get("/history/{session_id}")
def get_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    history = get_conversation_history(
        db=db,
        session_id=session_id,
        limit=3
    )

    return {
        "session_id": session_id,
        "messages": [
            {
                "role": message.role,
                "message": message.message
            }
            for message in history
        ]
    }
@router.get("/conversations")
def get_conversations(
    db: Session = Depends(get_db)
):
    conversations = get_all_conversations(db)

    return {
        "conversations": conversations
    }


@router.put("/conversations/{session_id}")
def rename_chat(
    session_id: str,
    request: ConversationRenameRequest,
    db: Session = Depends(get_db)
):
    result = rename_conversation(
        db=db,
        session_id=session_id,
        title=request.title.strip()
    )

    if result is None:
        return {
            "success": False,
            "message": "Conversation not found"
        }

    return {
        "success": True,
        "conversation": result
    }

@router.delete("/conversations/{session_id}")
def delete_chat(
    session_id: str,
    db: Session = Depends(get_db)
):
    deleted_count = delete_conversation(
        db=db,
        session_id=session_id
    )

    return {
        "success": True,
        "session_id": session_id,
        "deleted_messages": deleted_count
    }