from fastapi import APIRouter
from app.service.chat.chat import chat
from app.model.chat.chat_request import ChatRequest
from app.model.chat.chat_response import ChatResponse

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    return chat(req)