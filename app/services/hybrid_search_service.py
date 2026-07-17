from sqlalchemy.orm import Session
from app.services.rerank_service import rerank
from app.search.search_service import semantic_search
from app.services.bm25_service import (
    load_cases,
    build_bm25_index,
    bm25_search
)


from app.services.search_session_service import save_search_results


def hybrid_search(
    db: Session,
    session_id: str,
    query: str,
    top_k: int = 10
):
    # Semantic Search
    semantic_results = semantic_search(
        db=db,
        query=query,
        top_k=top_k
    )

    # BM25 Search
    documents = load_cases(db)
    bm25 = build_bm25_index(documents)

    keyword_results = bm25_search(
        query=query,
        documents=documents,
        bm25=bm25,
        top_k=top_k
    )

    # Merge results
    merged = {}

    # Add semantic results
    for result in semantic_results:
        merged[result["case_id"]] = result

    # Add BM25 results
    for result in keyword_results:

        case_id = result["case_id"]

        if case_id not in merged:
            merged[case_id] = result


    merged_results = list(merged.values())

    merged_results = rerank(query, merged_results)

    case_ids = [case["case_id"] for case in merged_results]

    save_search_results(
        db=db,
        session_id=session_id,
        case_ids=case_ids
    )

    return merged_results
    