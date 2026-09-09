from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import Base, engine

from app.models.conversation_model import Conversation
from app.models.knowledge_document_model import KnowledgeDocument

from app.core.exception_handler import register_exception_handlers

from app.api.chat_routes import router as chat_router
from app.api.conversation_history_routes import router as conversation_history_router
from app.routes.knowledge_routes import router as knowledge_router


# Create database tables
Base.metadata.create_all(bind=engine)


# Create FastAPI application
app = FastAPI(
    title="CA Knowledge Base API",
    version="1.0.0"
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
register_exception_handlers(app)


# Register routers
app.include_router(chat_router)
app.include_router(conversation_history_router)
app.include_router(knowledge_router)


# Root endpoint
@app.get("/")
def root():
    return {
        "message": "CA Knowledge Base API is running"
    }