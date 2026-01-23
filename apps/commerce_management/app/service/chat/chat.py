import asyncio
import json
from collections.abc import Callable
from typing import list, dict, Any

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

async def call_sheet_compose_llm(message:str) -> list[list[str]]:
    system_prompt = (
        "채팅 메시지 전체를 전달해줄건데, 그 중에서 주문 정보만 추려내는거야."
        "이 때 포맷은 일반적으로 인스타아이디 카톡아이디 주문아이템 색상 이런 식이야"
        "이런 내용인 걸 문맥의 의도를 보고 딱 주문한다 싶은 내용만 추려줘."
        "그리고 한 사람이 여럿 주문하는 경우가 있단 말이야? 그런 사람들의 주문 건은 모아줘야해"
        "응답은 여러 줄의 주문 건일텐데, 각 줄의 구성은 이렇게 해줘"
        "공란(""), 인스타아이디 카톡아이디, 주문아이템, 색상, 공란(""), 공란("")"
    )

    raw = await asyncio.to_thread(call_llm, system_prompt, message)
    
    print(raw)
    
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    return data

async def sheet_compose_service(req: ChatRequest) -> ChatResponse:
    # check user is in DB for this feature only
    result = await asyncio.to_thread(_ensure_user, req.session_id)
    
    if result is False:
        return ChatResponse(
            session_id=req.session_id,
            reply="해당 사용자는 사용할 수 없는 기능입니다!",
            usage=[],
        )
    
    await call_sheet_compose_llm(req.message)
    
    return ChatResponse(
        session_id=req.session_id,
        reply="동작 완료! Google Sheet 확인을 부탁드립니다.",
        usage=[],
    )
