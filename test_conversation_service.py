from app.db.session import SessionLocal
from app.services.conversation_service import (
    save_message,
    get_conversation_history
)

db = SessionLocal()

session_id = "test123"

save_message(
    db,
    session_id,
    "user",
    "What is breach of contract?"
)

save_message(
    db,
    session_id,
    "assistant",
    "A breach of contract occurs when..."
)

history = get_conversation_history(
    db,
    session_id
)

for msg in history:
    print(msg.role)
    print(msg.message)
    print("------")