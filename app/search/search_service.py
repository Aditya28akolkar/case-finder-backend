from sqlalchemy.orm import Session

from app.models.case_model import Case
from app.embeddings.embedding_service import generate_embedding
from app.vector.chroma_db import search_chunks


def semantic_search(db: Session, query: str, top_k: int = 10):
    # Generate embedding for the user's query
    query_embedding = generate_embedding(query)

    # Search ChromaDB
    results = search_chunks(query_embedding, top_k)

    # Group results by case_id
    case_scores = {}

    for metadata, distance in zip(
        results["metadatas"][0],
        results["distances"][0]
    ):
        case_id = metadata["case_id"]

        if case_id not in case_scores:
            case_scores[case_id] = distance
        else:
            case_scores[case_id] = min(case_scores[case_id], distance)

    # Fetch matching cases from PostgreSQL
    case_ids = list(case_scores.keys())

    cases = db.query(Case).filter(
        Case.id.in_(case_ids)
    ).all()

    # Build response
    response = []

    for case in cases:
        response.append({
            "case_id": case.id,
            "title": case.title,
            "court": case.court,
            "citation": case.citation,
            "text": case.full_text,
            "score": case_scores[case.id]
        })
    # Sort by similarity (lowest distance is best)
    response.sort(key=lambda x: x["score"])

    return response