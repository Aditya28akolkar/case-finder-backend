import chromadb

client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_or_create_collection(
    name="legal_cases"
)


def store_chunk(
    case_id: int,
    chunk_id: int,
    text: str,
    embedding: list,
    metadata: dict
):
    collection.add(
        ids=[f"{case_id}_{chunk_id}"],
        documents=[text],
        embeddings=[embedding],
        metadatas=[metadata]
    )

def search_chunks(query_embedding, top_k=5):
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )