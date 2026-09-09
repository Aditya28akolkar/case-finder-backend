import chromadb
from rank_bm25 import BM25Okapi


# --------------------------------------------------
# ChromaDB
# --------------------------------------------------

client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_collection(
    name="direct_tax"
)


# --------------------------------------------------
# Load ICAI chunks from ChromaDB
# --------------------------------------------------

def load_knowledge_chunks():

    data = collection.get(
        include=["documents", "metadatas"]
    )

    documents = data["documents"]
    metadatas = data["metadatas"]

    chunks = []

    for document, metadata in zip(documents, metadatas):

        chunks.append({
            "text": document,
            "metadata": metadata
        })

    return chunks


# --------------------------------------------------
# Build BM25 Index
# --------------------------------------------------

chunks = load_knowledge_chunks()

tokenized_documents = [
    chunk["text"].lower().split()
    for chunk in chunks
]

bm25 = BM25Okapi(tokenized_documents)


# --------------------------------------------------
# BM25 Search
# --------------------------------------------------

def bm25_search(query: str, top_k: int = 10):

    query_tokens = query.lower().split()

    scores = bm25.get_scores(query_tokens)

    results = []

    for chunk, score in zip(chunks, scores):

        results.append({
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "score": float(score)
        })

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:top_k]