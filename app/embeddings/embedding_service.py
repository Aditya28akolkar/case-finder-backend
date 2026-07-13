from sentence_transformers import SentenceTransformer

# Load the model only once when the application starts
model = SentenceTransformer("BAAI/bge-base-en-v1.5")


def generate_embedding(text: str) -> list[float]:
    """
    Generate embedding for the given text.
    """
    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()