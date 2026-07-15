from sentence_transformers import SentenceTransformer

# Load once when application starts
model = SentenceTransformer("BAAI/bge-base-en-v1.5")


def generate_embedding(text: str):
    """
    Generate embedding for a single text chunk.
    """
    embedding = model.encode(text, normalize_embeddings=True)

    return embedding.tolist()