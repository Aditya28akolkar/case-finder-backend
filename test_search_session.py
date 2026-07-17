from app.db.session import SessionLocal
from app.services.search_session_service import (
    save_search_results,
    get_search_results
)
from app.models.case_model import Case
from app.models.search_session_model import SearchSession


db = SessionLocal()

session_id = "demo-session"

case_ids = [1, 2, 3, 4, 5]

save_search_results(
    db=db,
    session_id=session_id,
    case_ids=case_ids
)

print(get_search_results(db, session_id))

db.close()