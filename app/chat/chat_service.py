from sqlalchemy.orm import Session

from app.models.case_model import Case


def get_case_context(db: Session, case_id: int):

    case = db.query(Case).filter(Case.id == case_id).first()

    if not case:
        return None

    return f"""
Title:
{case.title}

Court:
{case.court}

Citation:
{case.citation}

Summary:
{case.summary}

Judgement:

{case.full_text}
"""


def chat_with_case(db: Session, case_id: int, question: str):
    """
    Temporary placeholder.
    We'll replace this with RAG + chunk retrieval later.
    """
    context = get_case_context(db, case_id)

    if context is None:
        return {
            "answer": "Case not found."
        }

    return {
        "answer": "Chat functionality is under development.",
        "question": question,
        "case_id": case_id
    }