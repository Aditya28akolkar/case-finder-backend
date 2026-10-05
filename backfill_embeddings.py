from app.db.database import SessionLocal
from app.models.knowledge_document_model import KnowledgeDocument
from app.embeddings.embedding_service import generate_embedding


def backfill_embeddings():

    db = SessionLocal()

    try:

        documents = (
            db.query(KnowledgeDocument)
            .filter(
                KnowledgeDocument.embedding.is_(None)
            )
            .all()
        )

        print("\n========================================")
        print("EMBEDDING BACKFILL")
        print("========================================")

        print("Documents without embeddings:", len(documents))

        if not documents:
            print("All documents already have embeddings.")
            return

        processed = 0

        for document in documents:

            print(
                f"\nProcessing {processed + 1}/{len(documents)}"
            )

            print(
                "ID:",
                document.id
            )

            print(
                "Subject:",
                document.subject
            )

            print(
                "File:",
                document.file_name
            )

            print(
                "Page:",
                document.page_number
            )

            embedding = generate_embedding(
                document.content
            )

            document.embedding = embedding

            processed += 1

            # Save every 50 documents
            if processed % 50 == 0:

                db.commit()

                print(
                    f"Saved {processed} embeddings."
                )

        db.commit()

        print("\n========================================")
        print("BACKFILL COMPLETED")
        print("========================================")
        print(
            "Embeddings generated:",
            processed
        )

    except Exception as e:

        db.rollback()

        print("\nERROR:")
        print(e)

        raise

    finally:

        db.close()


if __name__ == "__main__":
    backfill_embeddings()