import time

from app.db.database import SessionLocal
from app.models.knowledge_document_model import KnowledgeDocument

from sentence_transformers import SentenceTransformer


# ============================================
# CPU CONFIGURATION
# ============================================

MODEL_NAME = "BAAI/bge-base-en-v1.5"

# For CPU, start with 16.
# If your PC has enough RAM and CPU is handling it well,
# you can increase this to 32.
BATCH_SIZE = 16


def generate_embeddings():

    print("\n========================================")
    print("LOADING EMBEDDING MODEL")
    print("========================================")

    # ========================================
    # CPU ONLY
    # ========================================

    device = "cpu"

    print("GPU is not being used.")
    print("Using CPU.")
    print(f"Batch size: {BATCH_SIZE}")

    # ========================================
    # LOAD MODEL
    # ========================================

    model = SentenceTransformer(
        MODEL_NAME,
        device=device
    )

    print("Embedding model loaded successfully.")

    # ========================================
    # DATABASE
    # ========================================

    db = SessionLocal()

    try:

        # ====================================
        # GET ONLY DOCUMENTS WITHOUT EMBEDDING
        # ====================================

        documents = (
            db.query(KnowledgeDocument)
            .filter(
                KnowledgeDocument.embedding.is_(None)
            )
            .order_by(
                KnowledgeDocument.id
            )
            .all()
        )

        total = len(documents)

        print("\n========================================")
        print("EMBEDDING STATUS")
        print("========================================")

        print(
            f"Documents without embeddings: {total}"
        )

        if total == 0:

            print(
                "\nAll documents already have embeddings."
            )

            return

        # ====================================
        # START PROCESSING
        # ====================================

        completed = 0

        overall_start = time.time()

        total_batches = (
            (total + BATCH_SIZE - 1)
            // BATCH_SIZE
        )

        for start in range(
            0,
            total,
            BATCH_SIZE
        ):

            batch = documents[
                start:start + BATCH_SIZE
            ]

            texts = [
                document.content
                for document in batch
            ]

            batch_number = (
                start // BATCH_SIZE
            ) + 1

            print("\n----------------------------------------")
            print(
                f"Batch {batch_number}/{total_batches}"
            )

            print(
                f"Documents: "
                f"{start + 1} - "
                f"{min(start + BATCH_SIZE, total)} "
                f"of {total}"
            )

            batch_start = time.time()

            # =================================
            # GENERATE EMBEDDINGS
            # =================================

            embeddings = model.encode(
                texts,
                batch_size=BATCH_SIZE,
                normalize_embeddings=True,
                show_progress_bar=True,
                convert_to_numpy=True
            )

            # =================================
            # SAVE EMBEDDINGS
            # =================================

            for document, embedding in zip(
                batch,
                embeddings
            ):

                document.embedding = (
                    embedding.tolist()
                )

            # IMPORTANT:
            # Save every batch.
            db.commit()

            completed += len(batch)

            # =================================
            # PROGRESS
            # =================================

            batch_time = (
                time.time() - batch_start
            )

            elapsed = (
                time.time() - overall_start
            )

            speed = (
                completed / elapsed
                if elapsed > 0
                else 0
            )

            remaining = total - completed

            estimated_seconds = (
                remaining / speed
                if speed > 0
                else 0
            )

            print(
                f"\nSaved: {completed}/{total}"
            )

            print(
                f"Batch time: "
                f"{batch_time:.2f} seconds"
            )

            print(
                f"Speed: "
                f"{speed:.2f} documents/sec"
            )

            print(
                f"Estimated remaining: "
                f"{estimated_seconds / 60:.1f} minutes"
            )

        # ====================================
        # COMPLETED
        # ====================================

        total_time = (
            time.time() - overall_start
        )

        print("\n========================================")
        print("EMBEDDING GENERATION COMPLETED")
        print("========================================")

        print(
            f"Total documents processed: {completed}"
        )

        print(
            f"Total time: "
            f"{total_time / 60:.2f} minutes"
        )

    except Exception as e:

        # ====================================
        # ROLLBACK CURRENT UNSAVED CHANGES
        # ====================================

        db.rollback()

        print("\n========================================")
        print("ERROR")
        print("========================================")

        print(e)

        raise

    finally:

        db.close()


if __name__ == "__main__":

    generate_embeddings()