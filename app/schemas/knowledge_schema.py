from pydantic import BaseModel

from pydantic import BaseModel


class ConversationRenameRequest(BaseModel):
    title: str
class KnowledgeAskRequest(BaseModel):

    question: str

    session_id: str