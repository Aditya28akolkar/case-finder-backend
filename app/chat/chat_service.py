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