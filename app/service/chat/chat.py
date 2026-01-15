from app.model.chat.chat_request import ChatRequest
from app.model.chat.chat_response import ChatResponse

async def chat_service(req: ChatRequest):
    return ChatResponse(
        session_id=req.session_id,
        reply=f"return: {req.message}",
        usage=[],
    )
