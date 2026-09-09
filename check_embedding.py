from app.db.database import SessionLocal
from app.models.knowledge_document_model import KnowledgeDocument


db = SessionLocal()

try:

    document = (
        db.query(KnowledgeDocument)
        .filter(
            KnowledgeDocument.embedding.isnot(None)
        )
        .first()
    )

    if document is None:

        print("No embeddings found in knowledge_documents.")

    else:

        print("======================================")
        print("EMBEDDING INFORMATION")
        print("======================================")

        print("Document ID:", document.id)
        print("File:", document.file_name)

        print(
            "Embedding dimensions:",
            len(document.embedding)
        )

        print(
            "First 10 values:",
            document.embedding[:10]
        )

finally:

    db.close()