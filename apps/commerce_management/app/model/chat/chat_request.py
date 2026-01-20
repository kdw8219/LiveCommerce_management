from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the chat session")
    message: str = Field(..., description="User's message to the chatbot")
    context: Optional[List[str]] = None