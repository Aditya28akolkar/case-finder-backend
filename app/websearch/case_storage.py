from sqlalchemy.orm import Session

from app.schemas.case_schema import CaseCreate
from app.services.case_service import create_case


def store_web_cases(db: Session, web_cases: list):

    stored_cases = []

    for item in web_cases:

        case = CaseCreate(
            title=item["title"],
            citation=item["citation"],
            court=item["court"],
            judge=item["judge"],
            summary=item["summary"],
            full_text=item["full_text"],
            source=item["source"]
        )

        stored = create_case(db, case)

        stored_cases.append(stored)

    return stored_cases