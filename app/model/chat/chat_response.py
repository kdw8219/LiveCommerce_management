from pydantic import BaseModel, Field
from typing import List, Optional


class ChatResponse(BaseModel):
    session_id : str = Field(..., description="Unique identifier for the chat session")
    reply: str = Field(..., description="Chatbot's reply to the user's message")
    usage: Optional[List[str]] = None