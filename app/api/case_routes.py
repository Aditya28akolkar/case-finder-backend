from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.case_schema import CaseCreate, CaseUpdate
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


from fastapi import APIRouter
from app.services.search_service import semantic_search

router = APIRouter()

@router.get("/search")
def search_cases(query: str):
    return semantic_search(query)



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