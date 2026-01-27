import asyncio
import json
import re
from collections.abc import Callable
from datetime import date
from typing import Any

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from app.model.chat.chat_request import ChatRequest
from app.model.chat.chat_response import ChatResponse
from sqlalchemy import select

from app.client.llm.chatgpt import call_llm
from app.client.db.psql import session_scope
from app.db.models.user import User

import app.config.config as configs

SPREADSHEET_NAME = "준이샵 라방 시작 24.10/8"
COMPLETED_TAB_INDEX = 2  # "3번 탭" (0-based index)
DATE_TITLE_RE = re.compile(r"^\s*(\d{1,2})\s*/\s*(\d{1,2})\s*$")

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


def _today_title() -> str:
    today = date.today()
    return f"{today.month}/{today.day}"


def _parse_date_title(title: str) -> date | None:
    """
    Parse worksheet titles like "1/22" into a date in the current year.
    Returns None if the title is not a simple month/day sheet.
    """
    m = DATE_TITLE_RE.match(title or "")
    if not m:
        return None
    month = int(m.group(1))
    day = int(m.group(2))
    try:
        return date(date.today().year, month, day)
    except ValueError:
        return None


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    # Extract the first numeric token and remove commas.
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _normalize_user_key(value: Any) -> str:
    return str(value or "").strip().lower()


def _find_user_group(rows: list[list[Any]], user_id: str) -> tuple[int, int] | None:
    """
    Find the last contiguous block (group) of rows where column B matches the user_id.
    Returns (start_index, end_index) inclusive, or None if not found.
    """
    target = _normalize_user_key(user_id)
    if not target:
        return None

    matches: list[int] = []
    for idx, row in enumerate(rows):
        col_b = row[1] if len(row) > 1 else ""
        if _normalize_user_key(col_b) == target:
            matches.append(idx)

    if not matches:
        return None

    pivot = matches[-1]

    start = pivot
    while start - 1 >= 0:
        prev_row = rows[start - 1]
        prev_b = prev_row[1] if len(prev_row) > 1 else ""
        if _normalize_user_key(prev_b) != target:
            break
        start -= 1

    end = pivot
    last_index = len(rows) - 1
    while end + 1 <= last_index:
        next_row = rows[end + 1]
        next_b = next_row[1] if len(next_row) > 1 else ""
        if _normalize_user_key(next_b) != target:
            break
        end += 1

    return (start, end)


def _group_contains_keep(rows: list[list[Any]], start: int, end: int) -> bool:
    for idx in range(start, end + 1):
        row = rows[idx]
        for cell in row:
            if "킵" in str(cell):
                return True
    return False


def _is_payment_confirmed(rows: list[list[Any]], start: int, end: int) -> bool:
    """
    Payment is considered confirmed if:
    - The last row's column A value exists, and
    - It is strictly greater than the sum of prior column A values in the group.
    """
    if start < 0 or end < start or end >= len(rows):
        return False

    last_row = rows[end]
    last_amount = _coerce_float(last_row[0] if len(last_row) > 0 else None)
    if last_amount is None:
        return False

    grouped_sum = 0.0
    for idx in range(start, end):
        row = rows[idx]
        amount = _coerce_float(row[0] if len(row) > 0 else None)
        if amount is not None:
            grouped_sum += amount

    return last_amount > grouped_sum


def _select_reference_worksheet(spreadsheet: gspread.Spreadsheet) -> gspread.Worksheet | None:
    """
    The business rule says the "3rd tab" represents completed processing.
    Prefer that tab when it exists; otherwise fall back to the last tab.
    """
    worksheets = spreadsheet.worksheets()
    if not worksheets:
        return None
    if len(worksheets) > COMPLETED_TAB_INDEX:
        return worksheets[COMPLETED_TAB_INDEX]
    return worksheets[-1]


def _resolve_reference_date(
    spreadsheet: gspread.Spreadsheet, reference_ws: gspread.Worksheet
) -> date:
    """
    Resolve the effective order date:
    - Use the reference worksheet's date title if available.
    - Otherwise fall back to the previous date sheet by tab order.
    - If still unavailable, use today's date.
    """
    ws_date = _parse_date_title(reference_ws.title)
    if ws_date:
        return ws_date

    worksheets = spreadsheet.worksheets()
    try:
        ref_index = worksheets.index(reference_ws)
    except ValueError:
        ref_index = -1

    if ref_index > 0:
        prev_ws = worksheets[ref_index - 1]
        prev_date = _parse_date_title(prev_ws.title)
        if prev_date:
            return prev_date

    # Fall back to the latest date-like sheet if any exist.
    dated_sheets: list[tuple[date, gspread.Worksheet]] = []
    for ws in worksheets:
        parsed = _parse_date_title(ws.title)
        if parsed:
            dated_sheets.append((parsed, ws))
    if dated_sheets:
        dated_sheets.sort(key=lambda item: item[0])
        return dated_sheets[-1][0]

    return date.today()


def _get_spreadsheet() -> gspread.Spreadsheet:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME)


def _sheet_status_for_user(user_id: str) -> dict[str, Any]:
    """
    Compute delivery/order status signals from the reference worksheet.
    Returns a dict with keys:
    - found: bool
    - payment_confirmed: bool
    - keep: bool
    - order_date: date
    - age_days: int
    """
    spreadsheet = _get_spreadsheet()
    reference_ws = _select_reference_worksheet(spreadsheet)
    if reference_ws is None:
        return {
            "found": False,
            "payment_confirmed": False,
            "keep": False,
            "order_date": date.today(),
            "age_days": 0,
        }

    order_date = _resolve_reference_date(spreadsheet, reference_ws)
    age_days = (date.today() - order_date).days

    rows = reference_ws.get_all_values()
    group = _find_user_group(rows, user_id)
    if group is None:
        return {
            "found": False,
            "payment_confirmed": False,
            "keep": False,
            "order_date": order_date,
            "age_days": age_days,
        }

    start, end = group
    keep = _group_contains_keep(rows, start, end)
    payment_confirmed = _is_payment_confirmed(rows, start, end)

    return {
        "found": True,
        "payment_confirmed": payment_confirmed,
        "keep": keep,
        "order_date": order_date,
        "age_days": age_days,
    }

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
    try:
        status = await asyncio.to_thread(_sheet_status_for_user, req.user_id)
    except FileNotFoundError:
        return ChatResponse(
            session_id=req.session_id,
            reply="배송 상태 확인에 문제가 발생했어요. 잠시 후 다시 시도해주세요.",
            usage=[],
        )
    except Exception:
        return ChatResponse(
            session_id=req.session_id,
            reply="배송 상태를 확인하는 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.",
            usage=[],
        )

    if status["keep"]:
        reply = "입금은 확인되었고, 요청하신 상품은 이번 출고에서 킵으로 처리되어 있어요."
    elif status["payment_confirmed"] and status["age_days"] >= 2:
        reply = "입금이 확인되었고 주문일 기준 2~3일 경과 건이라 배송된 것으로 보여요."
    elif status["payment_confirmed"]:
        reply = "입금이 확인되었어요. 출고/배송 진행 상태를 확인 중이에요."
    else:
        reply = "아직 입금 확인이 되지 않았을 수 있어요. 한번 더 확인 부탁드릴게요."

    return ChatResponse(
        session_id=req.session_id,
        reply=reply,
        usage=[],
    )


async def order_status_service(req: ChatRequest) -> ChatResponse:
    try:
        status = await asyncio.to_thread(_sheet_status_for_user, req.user_id)
    except FileNotFoundError:
        return ChatResponse(
            session_id=req.session_id,
            reply="주문 상태 확인에 문제가 발생했어요. 잠시 후 다시 시도해주세요.",
            usage=[],
        )
    except Exception:
        return ChatResponse(
            session_id=req.session_id,
            reply="주문 상태를 확인하는 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.",
            usage=[],
        )

    if status["keep"]:
        reply = "입금은 확인되었고, 해당 상품은 이번 출고에서 킵 처리되어 있어요."
    elif status["payment_confirmed"] and status["age_days"] >= 2:
        reply = "입금이 확인되었고 주문일 기준 2~3일 경과 건이라 배송 완료로 보여요."
    elif status["payment_confirmed"]:
        reply = "입금이 확인되었어요. 주문 처리는 완료 단계로 보고 있어요."
    else:
        reply = "입금이 아직 반영되지 않았을 수 있어요. 한번 더 확인 부탁드릴게요."

    return ChatResponse(
        session_id=req.session_id,
        reply=reply,
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
    fallbacks = ai_result.get("fallbacks", [])

    spreadsheet = _get_spreadsheet()
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
