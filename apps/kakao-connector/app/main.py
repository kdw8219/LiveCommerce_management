# apps/kakao-connector/main.py
import hmac
import hashlib
from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI()


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature)


@app.post("/webhook/kakao")
async def kakao_webhook(
    request: Request,
    x_kakao_signature: str = Header(default=""),
):
    body = await request.body()

    # TODO: 실제 카카오 시그니처 헤더/방식에 맞게 수정
    if not verify_signature(body, x_kakao_signature, "KAKAO_SECRET"):
        raise HTTPException(status_code=401, detail="invalid signature")

    payload = await request.json()

    # TODO: 카카오 메시지 구조에 맞게 파싱
    user_message = payload.get("userRequest", {}).get("utterance", "")

    # TODO: 내부 서비스 호출 (commerce_management)
    bot_reply = f"echo: {user_message}"

    # TODO: 카카오 응답 포맷에 맞게 구성
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {"simpleText": {"text": bot_reply}}
            ]
        }
    }
