import base64
import hmac
import hashlib
import json

import app.services.kakao as kakao_module


def _sign_body(body: bytes, secret: str) -> str:
    mac = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(mac).decode()


def test_kakao_webhook_success(client, monkeypatch):
    async def fake_call(_, __):
        return "ok"

    monkeypatch.setenv("KAKAO_SECRET", "secret")
    monkeypatch.setattr(kakao_module, "call_commerce_management", fake_call)

    payload = {
        "userRequest": {"utterance": "hello", "user": {"id": "user-1"}},
    }
    body = json.dumps(payload).encode()
    signature = _sign_body(body, "secret")

    response = client.post(
        "/webhook/kakao",
        data=body,
        headers={
            "x-kakao-signature": signature,
            "content-type": "application/json",
        },
    )

    assert response.status_code == 200
    assert response.json()["template"]["outputs"][0]["simpleText"]["text"] == "ok"
