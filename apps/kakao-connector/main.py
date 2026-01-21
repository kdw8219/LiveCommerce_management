import os

import httpx
from fastapi import FastAPI, Request
from redis import Redis

from buffer import append_message, should_flush, flush_buffer

app = FastAPI()
redis_client = Redis(host="localhost", port=6379, decode_responses=True)
commerce_base_url = os.getenv("COMMERCE_MANAGEMENT_URL", "http://commerce_management:8000")
commerce_client = httpx.AsyncClient(timeout=5.0)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await commerce_client.aclose()


def has_end_signal(text: str) -> bool:
    return any(token in text for token in ["완료", "이상입니다", "끝", "요청드립니다", "해주시겠어요", "부탁드려요"])


@app.post("/webhook/kakao")
async def kakao_webhook(request: Request):
    payload = await request.json()
    session_id = payload.get("userRequest", {}).get("user", {}).get("id", "anon")
    text = payload.get("userRequest", {}).get("utterance", "")

    append_message(redis_client, session_id, text)

    if has_end_signal(text) or should_flush(redis_client, session_id):
        merged = flush_buffer(redis_client, session_id)
        if merged:
            try:
                response = await commerce_client.post(
                    f"{commerce_base_url}/api/v1/chat",
                    json={"session_id": session_id, "message": merged},
                )
                if response.status_code == 200:
                    reply = response.json().get("reply", "요청을 처리 중입니다.")
                else:
                    reply = "요청을 처리 중입니다."
            except httpx.RequestError:
                reply = "요청을 처리 중입니다."
        else:
            reply = "요청을 처리 중입니다."
    else:
        # NOTE: Kakao webhook requires a response payload; adjust to channel spec.
        reply = ""

    return {
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": reply}}]},
    }
