from app.db.database import SessionLocal
from app.services.bm25_service import (
    load_cases,
    build_bm25_index,
    bm25_search
)

db = SessionLocal()

documents = load_cases(db)

bm25 = build_bm25_index(documents)

results = bm25_search(
    query="contract breach",
    documents=documents,
    bm25=bm25,
    top_k=5
)

for result in results:
    print(result)

db.close()