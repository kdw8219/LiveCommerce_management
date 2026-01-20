from pydantic import BaseModel
from typing import List


class MessageItem(BaseModel):
    role: str
    content: str


class ConversationResponse(BaseModel):
    session_id: str
    messages: List[MessageItem]
