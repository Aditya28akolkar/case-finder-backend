from app.services.embedding_service import generate_embedding
from app.vector.chroma_db import search_chunks

def semantic_search(query: str, top_k: int = 5):
    # Generate embedding for the user's query
    query_embedding = generate_embedding(query)

    # Search ChromaDB
    results = search_chunks(query_embedding, top_k)
    # Group results by case_id and keep the best (lowest) distance

    case_scores = {}

    for metadata, distance in zip(
        results["metadatas"][0],
        results["distances"][0]
    ):

        case_id = metadata["case_id"]

        # Keep the best score for each case
        if case_id not in case_scores:
            case_scores[case_id] = distance
        else:
            case_scores[case_id] = min(case_scores[case_id], distance)

    print(case_scores)






    return results


def semantic_search(db: Session, query: str, top_k: int = 10):

    query_embedding = generate_embedding(query)

    results = search_chunks(query_embedding, top_k)

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

    case_ids = list(case_scores.keys())

    cases = db.query(Case).filter(
        Case.id.in_(case_ids)
    ).all()

    response = []

    for case in cases:
        response.append({
            "case_id": case.id,
            "title": case.title,
            "court": case.court,
            "citation": case.citation,
            "score": case_scores[case.id]
        })

    response.sort(key=lambda x: x["score"])

    return response