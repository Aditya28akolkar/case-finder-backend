from fastapi import FastAPI

from app.db.database import Base, engine
from app.models.case_model import Case
from app.api.case_routes import router as case_router



# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Case Finder API",
    version="1.0.0"
)

# Register routes
app.include_router(case_router)


@app.get("/")
def root():
    return {
        "message": "Case Finder API is running"
    }