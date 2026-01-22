# apps/kakao-connector/main.py
import asyncio
import base64
import hmac
import hashlib
import logging
import os
import uuid

import httpx
from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI()
logger = logging.getLogger(__name__)
commerce_base_url = os.getenv("COMMERCE_MANAGEMENT_URL", "http://commerce_management:8000")
commerce_client = httpx.AsyncClient(timeout=5.0)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await commerce_client.aclose()


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    mac = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    return hmac.compare_digest(expected, signature.strip())

def kakao_response(text: str) -> dict:
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {"simpleText": {"text": text}}
            ]
        }
    }

async def call_commerce_management(payload: dict) -> str:
    user_message = payload.get("userRequest", {}).get("utterance", "")
    user_id = payload.get("userRequest", {}).get("user", {}).get("id", "unknown")
    try:
        response = await commerce_client.post(
            f"{commerce_base_url}/api/v1/chat",
            json={"session_id": user_id, "message": user_message},
        )
        if response.status_code == 200:
            return response.json().get("reply", "말씀하신 내용 확인중입니다. 곧 회신 드릴게요.")
    except httpx.RequestError:
        logger.exception("commerce_management request failed")
    return "말씀하신 내용 확인중입니다. 곧 회신 드릴게요."

async def send_followup(user_id: str, text: str) -> None:
    # TODO: 카카오 채널 발신 API 호출로 교체
    logger.info("followup to user=%s text=%s", user_id, text)

async def handle_long_running(task: asyncio.Task, user_id: str, request_id: str) -> None:
    try:
        reply = await task
        await send_followup(user_id, reply)
    except Exception:
        logger.exception("failed followup request_id=%s user=%s", request_id, user_id)


@app.post("/webhook/kakao")
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

    task = asyncio.create_task(call_commerce_management(payload))
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
