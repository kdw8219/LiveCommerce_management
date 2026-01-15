import pytest
import json

import app.service.chat.chat as chat_module
from app.model.chat.chat_response import ChatResponse
from app.model.chat.chat_request import ChatRequest

@pytest.mark.asyncio
async def test_chat_service_success_check(client, monkeypatch):
    async def fake_detect_intent(_):
        return "smalltalk"
    
    async def fake_smalltalk(req):
        return ChatResponse(session_id=req.session_id, reply="patched", usage=["mock"])
    
    monkeypatch.setattr(chat_module, "_detect_intent_llm", fake_detect_intent)
    monkeypatch.setattr(chat_module, "smalltalk_service", fake_smalltalk)

    response = await chat_module.chat_service(ChatRequest(session_id="chat_session", message="smalltalk", context=["previous"]))
    
    data = json.loads(response.model_dump_json())
    assert data["reply"] == "patched"
    assert data["session_id"] == "chat_session"
    assert data["usage"] == ["mock"]

    