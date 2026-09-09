from sqlalchemy.orm import Session

from app.services.rag_service import ask_question


def chat_with_case(
    db: Session,
    session_id: str,
    question: str
):
    """
    Chat using RAG + conversation memory.
    """

    return ask_question(
        db=db,
        session_id=session_id,
        question=question
    )