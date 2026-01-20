import pytest
import json

import app.service.chat.chat as chat_module
from app.model.chat.chat_response import ChatResponse
from app.model.chat.chat_request import ChatRequest

@pytest.mark.asyncio
async def test_chat_service_smalltalk_success_check(monkeypatch):
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


@pytest.mark.asyncio
async def test_chat_service_delivery_status_success_check(monkeypatch):
    async def fake_detect_intent(_):
        return "delivery_status"
    
    async def fake_delivery_status(req):
        return ChatResponse(session_id=req.session_id, reply="patched", usage=["mock"])
    
    monkeypatch.setattr(chat_module, "_detect_intent_llm", fake_detect_intent)
    monkeypatch.setattr(chat_module, "delivery_status_service", fake_delivery_status)

    response = await chat_module.chat_service(ChatRequest(session_id="chat_session", message="delivery check", context=["previous"]))
    
    data = json.loads(response.model_dump_json())
    assert data["reply"] == "patched"
    assert data["session_id"] == "chat_session"
    assert data["usage"] == ["mock"]
    

@pytest.mark.asyncio
async def test_chat_service_order_status_success_check(monkeypatch):
    async def fake_detect_intent(_):
        return "order_status"
    
    async def fake_order_status(req):
        return ChatResponse(session_id=req.session_id, reply="patched", usage=["mock"])
    
    monkeypatch.setattr(chat_module, "_detect_intent_llm", fake_detect_intent)
    monkeypatch.setattr(chat_module, "order_status_service", fake_order_status)

    response = await chat_module.chat_service(ChatRequest(session_id="chat_session", message="order check", context=["previous"]))
    
    data = json.loads(response.model_dump_json())
    assert data["reply"] == "patched"
    assert data["session_id"] == "chat_session"
    assert data["usage"] == ["mock"]
    
@pytest.mark.asyncio
async def test_chat_service_fallback_status_success_check(monkeypatch):
    async def fake_detect_intent(_):
        return "fallback"
    
    async def fake_fallback_status(req):
        return ChatResponse(session_id=req.session_id, reply="patched", usage=["mock"])
    
    monkeypatch.setattr(chat_module, "_detect_intent_llm", fake_detect_intent)
    monkeypatch.setattr(chat_module, "fallback_service", fake_fallback_status)

    response = await chat_module.chat_service(ChatRequest(session_id="chat_session", message="order check", context=["previous"]))
    
    data = json.loads(response.model_dump_json())
    assert data["reply"] == "patched"
    assert data["session_id"] == "chat_session"
    assert data["usage"] == ["mock"]
    
# @pytest.mark.asyncio
# async def test_delivery_status_service(monkeypatch):
#     # # TODO: session_id 기반으로 주문/배송 조회 로직 연결
#     # return ChatResponse(
#     #     session_id=req.session_id,
#     #     reply="배송 상태 조회를 진행할게요. 주문번호나 운송장 번호를 알려주세요.",
#     #     usage=[],
#     # )
    
#     response = await chat_module.delivery_status_service()