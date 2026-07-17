from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.database import Base


class SearchSession(Base):
    __tablename__ = "search_sessions"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(String, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id")
    )

    rank = Column(Integer)