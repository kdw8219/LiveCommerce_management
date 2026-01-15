from fastapi import APIRouter
from app.service.chat.chat import chat_service
from app.model.chat.chat_request import ChatRequest
from app.model.chat.chat_response import ChatResponse

api_router = APIRouter()

@api_router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    return await chat_service(req)
