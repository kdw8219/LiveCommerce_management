import asyncio
import json
from collections.abc import Callable

from app.model.chat.chat_request import ChatRequest
from app.model.chat.chat_response import ChatResponse

from app.client.llm.chatgpt import call_llm

import app.config.config as configs

async def ai_service(req: ChatRequest) -> ChatResponse:
    intent = await _detect_intent_llm(req.message)
    handler = _get_intent_handler(intent)
    return await handler(req)

async def _detect_intent_llm(message: str) -> str:
    system_prompt = (
        "You are an intent classifier for a live commerce chatbot. "
        "Choose exactly one intent from: delivery_status, order_status, "
        "smalltalk, fallback. "
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
    if intent == "compose_sheet":
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
    return ChatResponse(
        session_id=req.session_id,
        reply="요청을 이해하기 어려워요. 주문/배송 관련 질문인지 알려줄 수 있을까요?",
        usage=[],
    )