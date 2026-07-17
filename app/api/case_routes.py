from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.search.search_service import semantic_search
from app.services.hybrid_search_service import hybrid_search
from app.db.session import get_db
from app.schemas.case_schema import CaseCreate, CaseUpdate
from app.services.rag_service import ask_question


from app.services.case_service import (
    create_case,
    get_all_cases,
    get_case,
    update_case,
    delete_case
)

router = APIRouter(
    prefix="/cases",
    tags=["Cases"]
)


@router.post("/")
def create(case: CaseCreate, db: Session = Depends(get_db)):
    return create_case(db, case)


@router.get("/")
def read_all(db: Session = Depends(get_db)):
    return get_all_cases(db)







@router.get("/search")
def search_cases(
    query: str,
    db: Session = Depends(get_db)
):
    return semantic_search(db, query)




@router.get("/hybrid-search")
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



@router.get("/{case_id}")
def read_one(case_id: int, db: Session = Depends(get_db)):
    case = get_case(db, case_id)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return case


@router.put("/{case_id}")
def update(case_id: int, case: CaseUpdate, db: Session = Depends(get_db)):
    updated = update_case(db, case_id, case)

    if not updated:
        raise HTTPException(status_code=404, detail="Case not found")

    return updated




@router.delete("/{case_id}")
def delete(case_id: int, db: Session = Depends(get_db)):
    deleted = delete_case(db, case_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found")

    return {
        "message": "Case deleted successfully"
    }

