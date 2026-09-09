from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.db.database import Base


class KnowledgeDocument(Base):

    __tablename__ = "knowledge_documents"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    file_name = Column(
        String,
        nullable=False
    )

    subject = Column(
        String,
        nullable=False
    )

    module = Column(
        String,
        nullable=True
    )

    chapter = Column(
        String,
        nullable=True
    )

    page_number = Column(
        Integer,
        nullable=True
    )

    chunk_index = Column(
        Integer,
        nullable=True
    )

    content = Column(
        Text,
        nullable=False
    )

    source = Column(
        String,
        nullable=True
    )

    embedding = Column(
        Vector(768),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )