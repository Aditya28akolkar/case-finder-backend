from sqlalchemy.orm import Session

from app.models.case_model import Case

from app.schemas.case_schema import (
    CaseCreate,
    CaseUpdate
)
from app.vector.chroma_db import store_chunk
from app.chunking.chunk_service import ChunkService
from app.embeddings.embedding_service import generate_embedding
chunk_service = ChunkService()

def create_case(db: Session, case: CaseCreate):

    db_case = Case(**case.model_dump())

    db.add(db_case)
    db.commit()
    db.refresh(db_case)

    # If full_text is empty, don't try to chunk it
    if db_case.full_text:

        chunks = chunk_service.split_text(db_case.full_text)
        print("================================")
        print("TOTAL CHUNKS:", len(chunks))

        for chunk in chunks:
            print(chunk)

        print("================================")





        print("=" * 70)
        print(f"Case ID : {db_case.id}")
        print(f"Total Chunks : {len(chunks)}")
        print("=" * 70)

        for chunk in chunks:

            embedding = generate_embedding(chunk["text"])
            print("Chunk:", chunk["chunk_id"])
            print("Embedding Length:", len(embedding))




            metadata = {
                "case_id": db_case.id,
                "chunk_id": chunk["chunk_id"],
                "title": db_case.title,
                "court": db_case.court,
                "citation": db_case.citation
            }

            store_chunk(
                case_id=db_case.id,
                chunk_id=chunk["chunk_id"],
                text=chunk["text"],
                embedding=embedding,
                metadata=metadata
            )
            print(f"Stored Chunk {chunk['chunk_id']} in ChromaDB")

            print(f"Stored Chunk {chunk['chunk_id']} in ChromaDB")
    return db_case


def get_all_cases(db: Session):
    return db.query(Case).all()


def get_case(db: Session, case_id: int):
    return db.query(Case).filter(Case.id == case_id).first()


def update_case(db: Session, case_id: int, case: CaseUpdate):
    db_case = get_case(db, case_id)

    if not db_case:
        return None

    for key, value in case.model_dump(exclude_unset=True).items():
        setattr(db_case, key, value)

    db.commit()
    db.refresh(db_case)

    return db_case


def delete_case(db: Session, case_id: int):
    db_case = get_case(db, case_id)

    if not db_case:
        return None

    db.delete(db_case)
    db.commit()

    return db_case