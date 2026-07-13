from sqlalchemy.orm import Session

from app.models.case_model import Case
from app.schemas.case_schema import CaseCreate, CaseUpdate
from app.embeddings.embedding_service import generate_embedding
from app.vector.chroma_db import store_case_embedding

def create_case(db: Session, case: CaseCreate):
    db_case = Case(**case.model_dump())

    db.add(db_case)
    db.commit()
    db.refresh(db_case)

    return db_case


def get_all_cases(db: Session):
    return db.query(Case).all()


def get_case(db: Session, case_id: int):
    return db.query(Case).filter(Case.id == case_id).first()


def update_case(db: Session, case_id: int, case: CaseUpdate):
    db_case = get_case(db, case_id)

    if not db_case:
        return None

    for key, value in case.model_dump(exclude_unset=True).items():
        setattr(db_case, key, value)

    db.commit()
    db.refresh(db_case)

    return db_case


def delete_case(db: Session, case_id: int):
    db_case = get_case(db, case_id)

    if not db_case:
        return None

    db.delete(db_case)
    db.commit()

    return db_case


def create_case(db: Session, case: CaseCreate):
    db_case = Case(**case.model_dump())

    db.add(db_case)
    db.commit()
    db.refresh(db_case)

    # Combine searchable fields
    searchable_text = f"""
    {db_case.title}
    {db_case.summary}
    {db_case.full_text}
    """

    embedding = generate_embedding(searchable_text)

    metadata = {
        "title": db_case.title,
        "court": db_case.court,
        "citation": db_case.citation
    }

    store_case_embedding(
        db_case.id,
        embedding,
        metadata
    )

    return db_case