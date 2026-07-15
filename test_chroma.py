from app.vector.chroma_db import collection
from app.embeddings.embedding_service import generate_embedding

query = "contract breach"

embedding = generate_embedding(query)

results = collection.query(
    query_embeddings=[embedding],
    n_results=3
)

print(results)