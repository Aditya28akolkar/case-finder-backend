from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.search.search_service import semantic_search
from app.services.hybrid_search_service import hybrid_search
from app.services.rag_service import ask_question

router = APIRouter(
    prefix="/search",
    tags=["Search"]
)


@router.get("/semantic")
def semantic(
    query: str,
    db: Session = Depends(get_db)
):
    return semantic_search(db, query)


@router.post("/")
def search(
    session_id: str,
    query: str,
    db: Session = Depends(get_db)
):
    return hybrid_search(
        db=db,
        session_id=session_id,
        query=query
    )


@router.get("/ask")
def ask(
    question: str,
    db: Session = Depends(get_db)
):
    return ask_question(db, question)