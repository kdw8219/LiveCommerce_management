from fastapi import FastAPI, Request
from redis import Redis

from buffer import append_message, should_flush, flush_buffer

app = FastAPI()
redis_client = Redis(host="localhost", port=6379, decode_responses=True)


def has_end_signal(text: str) -> bool:
    return any(token in text for token in ["완료", "이상입니다", "끝", "요청드립니다"])


@app.post("/webhook/kakao")
async def kakao_webhook(request: Request):
    payload = await request.json()
    session_id = payload.get("userRequest", {}).get("user", {}).get("id", "anon")
    text = payload.get("userRequest", {}).get("utterance", "")

    append_message(redis_client, session_id, text)

    if has_end_signal(text) or should_flush(redis_client, session_id):
        merged = flush_buffer(redis_client, session_id)
        if merged:
            # TODO: call commerce_management chat API
            reply = f"received: {merged}"
        else:
            reply = "요청을 처리 중입니다."
    else:
        # NOTE: Kakao webhook requires a response payload; adjust to channel spec.
        reply = ""

    return {
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": reply}}]},
    }
