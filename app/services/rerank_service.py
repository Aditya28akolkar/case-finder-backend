from sentence_transformers import CrossEncoder

# Load once at startup
model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank(query: str, results: list):
    """
    Rerank retrieved cases using a CrossEncoder.
    """

    if not results:
        return []

    pairs = []

    for result in results:
        pairs.append((query, result["text"]))

    scores = model.predict(pairs)

    for result, score in zip(results, scores):
        result["rerank_score"] = float(score)

    results.sort(
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    return results