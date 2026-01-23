import json

from app.client.db.redis import redis_client


def get_context(session_id: str) -> list[str]:
    key = f"chat:session:{session_id}"
    data = redis_client.get(key)
    if data is None:
        return []
    try:
        decoded = json.loads(data)
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []


def set_context(session_id: str, context: list[str], ttl_seconds: int = 1800) -> None:
    key = f"chat:session:{session_id}"
    redis_client.setex(key, ttl_seconds, json.dumps(context))
