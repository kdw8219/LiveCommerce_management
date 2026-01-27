import pytest
import json
from datetime import date, timedelta

import app.service.chat.chat as chat_module
from app.model.chat.chat_response import ChatResponse
from app.model.chat.chat_request import ChatRequest
from openai import AuthenticationError

@pytest.mark.asyncio
async def test_ai_service_smalltalk_success_check(monkeypatch):
    async def fake_detect_intent(_):
        return "smalltalk"
    
    async def fake_smalltalk(req):
        return ChatResponse(session_id=req.session_id, reply="patched", usage=["mock"])
    
    monkeypatch.setattr(chat_module, "_detect_intent_llm", fake_detect_intent)
    monkeypatch.setattr(chat_module, "smalltalk_service", fake_smalltalk)

    response = await chat_module.ai_service(ChatRequest(session_id="chat_session", user_id="tempuser", message="smalltalk", context=["previous"]))
    
    data = json.loads(response.model_dump_json())
    assert data["reply"] == "patched"
    assert data["session_id"] == "chat_session"
    assert data["usage"] == ["mock"]


@pytest.mark.asyncio
async def test_ai_service_delivery_status_success_check(monkeypatch):
    async def fake_detect_intent(_):
        return "delivery_status"
    
    async def fake_delivery_status(req):
        return ChatResponse(session_id=req.session_id, reply="patched", usage=["mock"])
    
    monkeypatch.setattr(chat_module, "_detect_intent_llm", fake_detect_intent)
    monkeypatch.setattr(chat_module, "delivery_status_service", fake_delivery_status)

    response = await chat_module.ai_service(ChatRequest(session_id="chat_session", user_id="tempuser",message="delivery check", context=["previous"]))
    
    data = json.loads(response.model_dump_json())
    assert data["reply"] == "patched"
    assert data["session_id"] == "chat_session"
    assert data["usage"] == ["mock"]
    

@pytest.mark.asyncio
async def test_ai_service_order_status_success_check(monkeypatch):
    async def fake_detect_intent(_):
        return "order_status"
    
    async def fake_order_status(req):
        return ChatResponse(session_id=req.session_id, reply="patched", usage=["mock"])
    
    monkeypatch.setattr(chat_module, "_detect_intent_llm", fake_detect_intent)
    monkeypatch.setattr(chat_module, "order_status_service", fake_order_status)

    response = await chat_module.ai_service(ChatRequest(session_id="chat_session", user_id="tempuser", message="order check", context=["previous"]))
    
    data = json.loads(response.model_dump_json())
    assert data["reply"] == "patched"
    assert data["session_id"] == "chat_session"
    assert data["usage"] == ["mock"]


class _StubWorksheet:
    def __init__(self, title: str, rows: list[list[str]]):
        self.title = title
        self._rows = rows

    def get_all_values(self):
        return self._rows


class _StubSpreadsheet:
    def __init__(self, worksheets):
        self._worksheets = worksheets

    def worksheets(self):
        return self._worksheets


def _md_title(d: date) -> str:
    return f"{d.month}/{d.day}"


def _make_spreadsheet(third_tab_rows: list[list[str]], days_ago: int = 3):
    ref_date = date.today() - timedelta(days=days_ago)
    ws1 = _StubWorksheet(_md_title(ref_date - timedelta(days=2)), [])
    ws2 = _StubWorksheet(_md_title(ref_date - timedelta(days=1)), [])
    ws3 = _StubWorksheet(_md_title(ref_date), third_tab_rows)
    return _StubSpreadsheet([ws1, ws2, ws3])

def _make_dated_spreadsheet(date_to_rows: list[tuple[date, list[list[str]]]]):
    worksheets = [_StubWorksheet(_md_title(d), rows) for (d, rows) in date_to_rows]
    return _StubSpreadsheet(worksheets)


@pytest.mark.asyncio
async def test_parse_order_query_rule_range_and_item(monkeypatch):
    async def fake_llm(_message: str):
        return None

    monkeypatch.setattr(chat_module, "_parse_order_query_llm", fake_llm)

    query = await chat_module._parse_order_query("1/20부터 1/22까지 후드 주문 확인")
    assert query["date_from"] is not None
    assert query["date_to"] is not None
    assert query["range_text"] == "1/20~1/22"


@pytest.mark.asyncio
async def test_delivery_status_keep(monkeypatch):
    rows = [
        ["10000", "user1", "아이템"],
        ["12000", "user1", "킵"],
    ]
    stub = _make_spreadsheet(rows, days_ago=1)
    monkeypatch.setattr(chat_module, "_get_spreadsheet", lambda: stub)

    res = await chat_module.delivery_status_service(
        ChatRequest(session_id="s", user_id="user1", message="배송", context=None)
    )
    assert "킵" in res.reply


@pytest.mark.asyncio
async def test_delivery_status_delivered_when_paid_and_old(monkeypatch):
    rows = [
        ["10000", "user1"],
        ["5000", "user1"],
        ["16000", "user1"],
    ]
    stub = _make_spreadsheet(rows, days_ago=3)
    monkeypatch.setattr(chat_module, "_get_spreadsheet", lambda: stub)

    res = await chat_module.delivery_status_service(
        ChatRequest(session_id="s", user_id="user1", message="배송", context=None)
    )
    assert "배송" in res.reply and "2~3일" in res.reply


@pytest.mark.asyncio
async def test_order_status_requests_payment_check_when_not_paid(monkeypatch):
    rows = [
        ["10000", "user1"],
        ["5000", "user1"],
        ["15000", "user1"],
    ]
    stub = _make_spreadsheet(rows, days_ago=0)
    monkeypatch.setattr(chat_module, "_get_spreadsheet", lambda: stub)

    res = await chat_module.order_status_service(
        ChatRequest(session_id="s", user_id="user1", message="주문", context=None)
    )
    assert "입금" in res.reply and "확인" in res.reply

@pytest.mark.asyncio
async def test_order_status_range_and_item_paid(monkeypatch):
    async def fake_llm(_message: str):
        return None

    monkeypatch.setattr(chat_module, "_parse_order_query_llm", fake_llm)

    d1 = date.today() - timedelta(days=4)
    d2 = date.today() - timedelta(days=3)

    rows_d1 = [
        ["10000", "user1", "후드"],
        ["16000", "user1", "후드"],
    ]
    rows_d2 = [
        ["9000", "user1", "티셔츠"],
        ["10000", "user1", "티셔츠"],
    ]

    stub = _make_dated_spreadsheet([(d1, rows_d1), (d2, rows_d2)])
    monkeypatch.setattr(chat_module, "_get_spreadsheet", lambda: stub)

    message = f"{_md_title(d1)}부터 {_md_title(d2)}까지 '후드' 주문 어때?"
    res = await chat_module.order_status_service(
        ChatRequest(session_id="s", user_id="user1", message=message, context=None)
    )
    assert "배송 완료" in res.reply or "배송된" in res.reply

@pytest.mark.asyncio
async def test_ai_service_fallback_status_success_check(monkeypatch):
    async def fake_detect_intent(_):
        return "fallback"
    
    async def fake_fallback_status(req):
        return ChatResponse(session_id=req.session_id, reply="patched", usage=["mock"])
    
    monkeypatch.setattr(chat_module, "_detect_intent_llm", fake_detect_intent)
    monkeypatch.setattr(chat_module, "fallback_service", fake_fallback_status)

    response = await chat_module.ai_service(ChatRequest(session_id="chat_session", user_id="tempuser", message="order check", context=["previous"]))
    
    data = json.loads(response.model_dump_json())
    assert data["reply"] == "patched"
    assert data["session_id"] == "chat_session"
    assert data["usage"] == ["mock"]
    
    
@pytest.mark.asyncio
async def test_ai_service_sheet_compose_status_success_check(monkeypatch):
    async def fake_detect_intent(_):
        return "sheet_compose"

    called = {"value": False}

    def fake_ensure_user(user_id: str) -> None:
        assert user_id == "chat_session"
        called["value"] = True
        
    monkeypatch.setattr(chat_module, "_detect_intent_llm", fake_detect_intent)
    monkeypatch.setattr(chat_module, "_ensure_user", fake_ensure_user)

    response = await chat_module.ai_service(ChatRequest(session_id="chat_session", user_id="tempuser", message="order check", context=["previous"]))
    
    data = json.loads(response.model_dump_json())
    assert data["session_id"] == "chat_session"
    assert called["value"] is True
    
    
@pytest.mark.asyncio
async def test_ai_service_sheet_compose_status_fail_check(monkeypatch):
    async def fake_detect_intent(_):
        return "sheet_compose"

    def fake_ensure_user(_user_id: str) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(chat_module, "_detect_intent_llm", fake_detect_intent)
    monkeypatch.setattr(chat_module, "_ensure_user", fake_ensure_user)

    response = None

    with pytest.raises(RuntimeError, match="db down"):
        await chat_module.ai_service(ChatRequest(session_id="chat_session", user_id="tempuser", message="order check", context=["previous"]))

def test_ensure_user(monkeypatch):
    
    result = chat_module._ensure_user("testuser")
    assert result == False
    
    result = chat_module._ensure_user("")
    assert result == False
    
    
@pytest.mark.asyncio
async def test_detect_intent_llm_test(monkeypatch):
    
    with pytest.raises(AuthenticationError) as exc:
        await chat_module._detect_intent_llm("send me delivery_status as an intent")
    assert exc.value.status_code == 401
    
    # #---------------------------------------------------------------#
    
    # result = await chat_module._detect_intent_llm("send me delivery_status as an intent")
    # assert result == "delivery_status"
    
    # #---------------------------------------------------------------#
    
    # result = await chat_module._detect_intent_llm("send me order_status as an intent")
    # assert result == "order_status"
    
    # #---------------------------------------------------------------#
    
    # result = await chat_module._detect_intent_llm("send me smalltalk as an intent")
    # assert result == "smalltalk"
    
    # #---------------------------------------------------------------#
    
    # result = await chat_module._detect_intent_llm("send me sheet_compose as an intent")
    # assert result == "sheet_compose"
    
    # #---------------------------------------------------------------#
    
    # result = await chat_module._detect_intent_llm("send me fallback as an intent")
    # assert result == "fallback"
