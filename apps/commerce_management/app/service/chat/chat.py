import asyncio
import json
from collections.abc import Callable
from typing import list, dict, Any
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

async def call_sheet_compose_llm(message: str) -> dict[str, list]:
    system_prompt = (
        '채팅 메시지 전체를 전달할 것이다.'
        '그 중에서 문맥상 "주문"으로 명확히 판단되는 내용만 추려라.'

        '주문 정보는 일반적으로'
        '인스타아이디, 카카오톡아이디, 주문아이템, 색상'
'으로 구성되어 있다.'

'위 구성이 정확히 맞지 않더라도,'
'가격 제시, 아이템 언급, 주문 의사 표현이 있으면'
'주문 건으로 판단한다.'

'주문 정보가 일부만 존재하는 경우,'
'아래 포맷에 맞게 채우고 없는 필드는 공백으로 둔다.'

'인스타아이디와 카카오톡아이디는'
'항상 하나의 문자열로 결합해서 출력해야 하며,'
'형식은 다음과 같다.'

'"인스타아이디 카카오톡아이디"'

'(공백 하나로만 구분하고 절대 분리하지 말 것)'

'한 사람이 여러 개를 주문한 경우,'
'사람 기준으로 주문을 인식하되'
'출력은 주문 건 단위로 각각 한 줄씩 출력한다.'

'이때 동일 인물의 주문들은'
'출력 배열에서 반드시 연속된 인덱스로 배치한다.'

'출력은 JSON만 반환한다.'

'주문 목록은 orders 배열에 담고,'
'각 주문은 아래 순서를 가진 배열이어야 한다.'

'['
  '"",'
  '"인스타아이디 카카오톡아이디",'
  '"주문아이템",'
  '"색상",'
  '"",'
  '""'
']'

'주문으로 보기 애매하지만'
'아이템이나 가격이 언급된 문장은'
'fallbacks 배열에 문자열 그대로 담아 전달한다.'

'설명, 주석, 자연어 문장은'
'절대 포함하지 말 것.'

    )

    raw = await asyncio.to_thread(call_llm, system_prompt, message)
    
    print(raw)
    
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"orders": [], "fallbacks": []}

    orders = data.get("orders", [])
    fallbacks = data.get("fallbacks", [])

    if not isinstance(orders, list):
        orders = []
    if not isinstance(fallbacks, list):
        fallbacks = []

    return {"orders": orders, "fallbacks": fallbacks}

async def sheet_compose_service(req: ChatRequest) -> ChatResponse:
    # check user is in DB for this feature only
    result = await asyncio.to_thread(_ensure_user, req.session_id)
    
    if result is False:
        return ChatResponse(
            session_id=req.session_id,
            reply="해당 사용자는 사용할 수 없는 기능입니다!",
            usage=[],
        )
    
    ai_result = await call_sheet_compose_llm(req.message)
    orders = ai_result.get("orders", [])
    fallbacks= ai_result.get("fallbacks", [])
    
    scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name('creds.json', scope)
    client = gspread.authorize(creds)
    
    spreadsheet = client.open("준이샵 라방 시작 24.10/8")
    new_sheet = spreadsheet.add_worksheet(title="NewTab")
    
    for i in range(0, len(orders)):
        new_sheet.append(orders[i])
        
    if len(fallbacks) != 0:
        new_sheet.append([])
        new_sheet.append(["", "실패 사례"])
        
        for i in range(0, len(fallbacks)):
            new_sheet.append(["", fallbacks[i]])
    
    new_sheet.format("A", {
        "backgroundColor": {
            "red": 1.0,
            "green": 1.0,
            "blue": 0.0
        }
    })
    
    return ChatResponse(
        session_id=req.session_id,
        reply="동작 완료! Google Sheet 확인을 부탁드립니다.",
        usage=[],
    )
