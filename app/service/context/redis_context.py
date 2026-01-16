from app.client.db.redis import redis_client


def get_context(session_id: str) -> list[str]:
    key = f"chat:session:{session_id}"
    data = redis_client.get(key)
    return [] if data is None else []


def set_context(session_id: str, context: list[str], ttl_seconds: int = 1800) -> None:
    key = f"chat:session:{session_id}"
    redis_client.setex(key, ttl_seconds, "")
