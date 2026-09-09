from pydantic import BaseModel


class KnowledgeAskRequest(BaseModel):

    question: str

    session_id: str