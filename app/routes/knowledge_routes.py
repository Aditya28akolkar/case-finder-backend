
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.rag_service import ask_question
from app.schemas.knowledge_schema import KnowledgeAskRequest


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

