from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.db.database import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    citation = Column(String, nullable=True)

    court = Column(String, nullable=True)

    judge = Column(String, nullable=True)

    summary = Column(Text, nullable=True)

    full_text = Column(Text, nullable=True)

    source = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )