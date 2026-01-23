import asyncio
import json
from collections.abc import Callable

from app.model.chat.chat_request import ChatRequest
from app.model.chat.chat_response import ChatResponse
from sqlalchemy import select

from app.client.llm.chatgpt import call_llm
from app.client.db.psql import session_scope
from app.db.models.user import User

import app.config.config as configs

async def ai_service(req: ChatRequest) -> ChatResponse:
    intent = await _detect_intent_llm(req.message)
    handler = _get_intent_handler(intent)
    return await handler(req)

def _ensure_user(user_id: str) -> bool:
    if not user_id:
        return False
    with session_scope() as db:
        existing = db.execute(select(User).where(User.user_id == user_id)).scalar_one_or_none()
        
        if existing is None:
            return False
        else:
            return True
        

async def _detect_intent_llm(message: str) -> str:
    system_prompt = (
        "You are an intent classifier for a live commerce chatbot. "
        "Choose exactly one intent from: delivery_status, order_status, "
        "smalltalk, sheet_compose, fallback. "
        "Return JSON only: {\"intent\":\"<one_of_intents>\"}. "
        "If ambiguous, use fallback."
    )

    raw = await asyncio.to_thread(call_llm, system_prompt, message)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return "fallback"

    intent = data.get("intent", "fallback")
    if intent not in configs.INTENTS:
        return "fallback"
    return intent


def _get_intent_handler(intent: str) -> Callable[[ChatRequest], "asyncio.Future[ChatResponse]"]:
    if intent == "delivery_status":
        return delivery_status_service
    if intent == "order_status":
        return order_status_service
    if intent == "smalltalk":
        return smalltalk_service
    if intent == "sheet_compose":
        return sheet_compose_service
    return fallback_service


async def delivery_status_service(req: ChatRequest) -> ChatResponse:
    # TODO: session_id 기반으로 주문/배송 조회 로직 연결
    return ChatResponse(
        session_id=req.session_id,
        reply="배송 상태 조회를 진행할게요. 주문번호나 운송장 번호를 알려주세요.",
        usage=[],
    )


async def order_status_service(req: ChatRequest) -> ChatResponse:
    # TODO: session_id 기반으로 주문 조회 로직 연결
    return ChatResponse(
        session_id=req.session_id,
        reply="주문 내역을 확인할게요. 주문번호를 알려주세요.",
        usage=[],
    )


async def smalltalk_service(req: ChatRequest) -> ChatResponse:
    return ChatResponse(
        session_id=req.session_id,
        reply=f"return: {req.message}",
        usage=[],
    )


async def fallback_service(req: ChatRequest) -> ChatResponse:
    return ChatResponse(
        session_id=req.session_id,
        reply="요청을 이해하기 어려워요. 주문/배송 관련 질문인지 알려줄 수 있을까요?",
        usage=[],
    )

async def sheet_compose_service(req: ChatRequest) -> ChatResponse:
    # check user is in DB for this feature only
    result = await asyncio.to_thread(_ensure_user, req.session_id)
    
    if result is False:
        return ChatResponse(
            session_id=req.session_id,
            reply="해당 사용자는 사용할 수 없는 기능입니다!",
            usage=[],
        )
    
    #do something
    
    return ChatResponse(
        session_id=req.session_id,
        reply="동작 완료! Google Sheet 확인을 부탁드립니다.",
        usage=[],
    )
