from fastapi import APIRouter
from app.service.chat.chat import ai_service
from app.model.chat.chat_request import ChatRequest
from app.model.chat.chat_response import ChatResponse

api_router = APIRouter()

@api_router.post("/chat", response_model=ChatResponse)
async def ai_request(req: ChatRequest):
    return await ai_service(req)
