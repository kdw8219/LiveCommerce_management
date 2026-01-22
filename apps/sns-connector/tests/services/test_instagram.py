import app.services.instagram as instagram_module


def test_extract_instagram_messages():
    payload = {
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": "user-1"},
                        "message": {"text": "hi"},
                    }
                ]
            }
        ]
    }

    messages = instagram_module.extract_instagram_messages(payload)

    assert messages == [("user-1", "hi")]


def test_instagram_verify_success(client, monkeypatch):
    monkeypatch.setenv("INSTAGRAM_VERIFY_TOKEN", "token-123")

    response = client.get(
        "/webhook/instagram",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "token-123",
            "hub.challenge": "challenge",
        },
    )

    assert response.status_code == 200
    assert response.text == "challenge"
