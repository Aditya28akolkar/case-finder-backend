from sqlalchemy.orm import Session

from app.models.case_model import Case


def load_cases(db: Session):
    """
    Load all cases from PostgreSQL.
    """

    cases = db.query(Case).all()

    documents = []

    for case in cases:
        documents.append({
            "case_id": case.id,
            "title": case.title,
            "court": case.court,
            "citation": case.citation,
            "text": case.full_text
        })

    return documents

from rank_bm25 import BM25Okapi


def build_bm25_index(documents):
    """
    Build a BM25 index from all case documents.
    """

    tokenized_documents = []

    for doc in documents:
        tokens = doc["text"].lower().split()
        tokenized_documents.append(tokens)

    bm25 = BM25Okapi(tokenized_documents)

    return bm25


def bm25_search(query: str, documents, bm25, top_k: int = 5):
    """
    Search documents using BM25.
    """

    # Tokenize the query
    query_tokens = query.lower().split()

    # Get BM25 scores
    scores = bm25.get_scores(query_tokens)

    # Pair each document with its score
    results = []

    for doc, score in zip(documents, scores):
        results.append({
            "case_id": doc["case_id"],
            "title": doc["title"],
            "court": doc["court"],
            "citation": doc["citation"],
            "text": doc["text"],
            "score": float(score)
        })

    # Sort by highest score
    results.sort(key=lambda x: x["score"], reverse=True)

    # Return top results
    return results[:top_k]