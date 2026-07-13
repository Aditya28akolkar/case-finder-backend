import chromadb

# Persistent storage
client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_or_create_collection(
    name="legal_cases"
)

def store_case_embedding(case_id: int, embedding: list, metadata: dict):
    """
    Store a case embedding in ChromaDB.
    """

    collection.add(
        ids=[str(case_id)],
        embeddings=[embedding],
        metadatas=[metadata]
    )

def search_similar_cases(query_embedding: list, top_k: int = 10):
    """
    Search for similar cases.
    """

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    return results