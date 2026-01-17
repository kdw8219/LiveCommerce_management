from pydantic import BaseModel


class ConversationRequest(BaseModel):
    session_id: str
