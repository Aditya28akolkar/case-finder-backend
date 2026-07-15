from sqlalchemy.orm import Session

from app.models.case_model import Case


from app.vector.chroma_db import search_similar_cases

from app.websearch.web_search_service import search_cases_from_web
from app.websearch.case_storage import store_web_cases


def search_cases(db: Session, query: str, top_k: int = 10):

    query_embedding = generate_embedding(query)

    results = search_similar_cases(query_embedding, top_k)

    ids = results["ids"][0]

    # ------------------------
    # LOCAL SEARCH SUCCESS
    # ------------------------

    if ids:

        cases = (
            db.query(Case)
            .filter(Case.id.in_([int(i) for i in ids]))
            .all()
        )

        case_map = {case.id: case for case in cases}

        ordered = [
            case_map[int(i)]
            for i in ids
            if int(i) in case_map
        ]

        return ordered

    # ------------------------
    # WEB SEARCH FALLBACK
    # ------------------------

    print("[INFO] No local cases found.")

    web_cases = search_cases_from_web(query)

    store_web_cases(db, web_cases)

    # Search again after inserting

    results = search_similar_cases(query_embedding, top_k)

    ids = results["ids"][0]

    if not ids:
        return []

    cases = (
        db.query(Case)
        .filter(Case.id.in_([int(i) for i in ids]))
        .all()
    )

    case_map = {case.id: case for case in cases}

    ordered = [
        case_map[int(i)]
        for i in ids
        if int(i) in case_map
    ]

    return ordered