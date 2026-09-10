from sentence_transformers import SentenceTransformer

model = None


def get_model():
    global model

    if model is None:
        model = SentenceTransformer(
            "BAAI/bge-base-en-v1.5",
            device="cpu"
        )

    return model


def generate_embedding(text: str):
    """
    Generate embedding for a single text chunk.
    """
    model = get_model()

    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()