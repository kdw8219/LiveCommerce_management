import asyncio
import base64
import hmac
import hashlib
import os
import uuid

from fastapi import APIRouter, Header, HTTPException, Request
from redis import Redis

from ..utils import append_message, flush_buffer, should_flush
from ..utils.buffer import FLUSH_SILENCE_SEC
from .common import call_commerce_management, logger

router = APIRouter()
BUFFER_ENABLED = os.getenv("KAKAO_BUFFER_ENABLED", "") == "1"
redis_client = Redis(host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", "6379")), decode_responses=True) if BUFFER_ENABLED else None


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    mac = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    return hmac.compare_digest(expected, signature.strip())


def kakao_response(text: str) -> dict:
    return {
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": text}}]},
    }

def has_end_signal(text: str) -> bool:
    return any(token in text for token in ["완료", "이상입니다", "끝", "요청드립니다", "해주시겠어요", "부탁드려요"])


async def send_followup(user_id: str, text: str) -> None:
    # TODO: 카카오 채널 발신 API 호출로 교체
    logger.info("followup to user=%s text=%s", user_id, text)


async def flush_after_silence(user_id: str) -> None:
    await asyncio.sleep(FLUSH_SILENCE_SEC)
    if redis_client is None:
        return
    if not should_flush(redis_client, user_id):
        return
    merged = flush_buffer(redis_client, user_id)
    if not merged:
        return
    reply = await call_commerce_management(user_id, merged)
    await send_followup(user_id, reply)


async def handle_long_running(task: asyncio.Task, user_id: str, request_id: str) -> None:
    try:
        reply = await task
        await send_followup(user_id, reply)
    except Exception:
        logger.exception("failed followup request_id=%s user=%s", request_id, user_id)


@router.post("/webhook/kakao")
async def kakao_webhook(
    request: Request,
    x_kakao_signature: str = Header(default=""),
):
    body = await request.body()

    kakao_secret = os.getenv("KAKAO_SECRET", "")
    if not kakao_secret or not verify_signature(body, x_kakao_signature, kakao_secret):
        raise HTTPException(status_code=401, detail="invalid signature")

    payload = await request.json()

    user_request = payload.get("userRequest")
    if not isinstance(user_request, dict):
        user_request = {}
        payload["userRequest"] = user_request

    user = user_request.get("user")
    if not isinstance(user, dict):
        user = {}
        user_request["user"] = user

    user_message = user_request.get("utterance") or ""
    user_id = user.get("id") or "unknown"

    if not user_message:
        action = payload.get("action")
        if isinstance(action, dict):
            detail_params = action.get("detailParams")
            if isinstance(detail_params, dict) and detail_params:
                for param in detail_params.values():
                    if not isinstance(param, dict):
                        continue
                    origin = param.get("origin")
                    if origin:
                        user_message = origin
                        break
                    value = param.get("value")
                    if value:
                        user_message = value
                        break

            if not user_message:
                params = action.get("params")
                if isinstance(params, dict) and params:
                    for value in params.values():
                        if value:
                            user_message = str(value)
                            break

            if not user_message:
                name = action.get("name")
                if name:
                    user_message = str(name)

    if user_message:
        user_request["utterance"] = user_message
    request_id = str(uuid.uuid4())

    if BUFFER_ENABLED and user_message and redis_client is not None:
        append_message(redis_client, user_id, user_message)
        if not (has_end_signal(user_message) or should_flush(redis_client, user_id)):
            asyncio.create_task(flush_after_silence(user_id))
            return kakao_response("")
        merged = flush_buffer(redis_client, user_id)
        if not merged:
            return kakao_response("요청을 처리 중입니다.")
        user_message = merged
        user_request["utterance"] = merged

    task = asyncio.create_task(call_commerce_management(user_id, user_message))
    try:
        # 5초 제한을 고려해 내부 처리에 타임아웃 적용
        bot_reply = await asyncio.wait_for(
            asyncio.shield(task),
            timeout=4.5,
        )
        return kakao_response(bot_reply)
    except asyncio.TimeoutError:
        asyncio.create_task(handle_long_running(task, user_id, request_id))
        return kakao_response("처리 중입니다. 잠시 후 안내드릴게요.")
