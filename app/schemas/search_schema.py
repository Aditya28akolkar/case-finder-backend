from pydantic import BaseModel


class SearchRequest(BaseModel):
    session_id: str
    query: str


class SearchResult(BaseModel):
    case_id: int
    title: str
    court: str | None = None
    citation: str | None = None
    score: float


class SearchResponse(BaseModel):
    session_id: str
    results: list[SearchResult]