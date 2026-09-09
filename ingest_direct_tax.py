from app.db.database import SessionLocal

from app.services.knowledge_ingestion_service import (
    process_all_pdfs
)


PDF_FOLDER = "data/01_Direct_Tax"

db = SessionLocal()

try:

    process_all_pdfs(
        base_folder=PDF_FOLDER,
        db=db
    )

finally:

    db.close()