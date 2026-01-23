import app.api.v1.route as v1_router_module

def test_chat_endpoint_success_check(client, monkeypatch):
    async def fake_ai_service(req):
        return {
            "session_id": req.session_id,
            "reply": f"return: {req.message}",
            "usage": ["mock"],
        }

    monkeypatch.setattr(v1_router_module, "ai_service", fake_ai_service)

    payload = {
        "session_id": "session-123",
        "user_id": "tempuser",
        "message": "hello",
        "context": ["previous"],
    }

    response = client.post("/api/v1/chat", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "session-123",
        "reply": "return: hello",
        "usage": ["mock"],
    }


def test_chat_endpoint_error_check(client):
    response = client.post("/api/v1/chat", json={"session_id": "session-123"})

    assert response.status_code == 422
