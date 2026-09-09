from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.db.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(String, index=True)

    role = Column(String, nullable=False)
    # "user" or "assistant"

    message = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )