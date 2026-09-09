from sqlalchemy.orm import Session
import chromadb

from app.models.knowledge_document_model import KnowledgeDocument
from app.embeddings.embedding_service import generate_embedding


# ==========================================
# CHROMA CLIENT
# ==========================================

chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)


# Separate collection for Direct Tax
collection = chroma_client.get_or_create_collection(
    name="direct_tax"
)


# ==========================================
# STORE DIRECT TAX EMBEDDINGS
# ==========================================

def create_direct_tax_embeddings(db: Session):

    documents = (
        db.query(KnowledgeDocument)
        .all()
    )

    print(
        "TOTAL DIRECT TAX CHUNKS:",
        len(documents)
    )

    if not documents:
        print("No Direct Tax documents found.")
        return

    added = 0

    for document in documents:

        try:

            embedding = generate_embedding(
                document.content
            )

            collection.upsert(
                ids=[
                    str(document.id)
                ],

                embeddings=[
                    embedding
                ],

                documents=[
                    document.content
                ],

                metadatas=[
                    {
                        "file_name": document.file_name,
                        "subject": document.subject,
                        "module": document.module,
                        "chapter": document.chapter,
                        "page_number": document.page_number,
                        "chunk_index": document.chunk_index,
                        "source": document.source,
                    }
                ]
            )

            added += 1

            if added % 10 == 0:

                print(
                    f"Embedded {added} chunks..."
                )

        except Exception as e:

            print(
                f"Embedding failed for ID "
                f"{document.id}: {e}"
            )

    print(
        "\nDIRECT TAX EMBEDDING COMPLETE"
    )

    print(
        "TOTAL EMBEDDED:",
        added
    )

    print(
        "CHROMA COUNT:",
        collection.count()
    )