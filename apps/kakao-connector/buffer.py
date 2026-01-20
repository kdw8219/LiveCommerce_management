import time
from typing import Optional
from redis import Redis

BUFFER_TTL = 120
FLUSH_SILENCE_SEC = 5
MAX_WAIT_SEC = 60
MAX_CHARS = 800


def _buffer_key(session_id: str) -> str:
    return f"chat:buffer:{session_id}"


def _meta_key(session_id: str) -> str:
    return f"chat:buffer:meta:{session_id}"


def _lock_key(session_id: str) -> str:
    return f"chat:buffer:lock:{session_id}"


def append_message(r: Redis, session_id: str, text: str) -> None:
    now = int(time.time())
    buf_key = _buffer_key(session_id)
    meta_key = _meta_key(session_id)

    r.rpush(buf_key, text)

    meta = r.hgetall(meta_key)
    if not meta:
        r.hset(meta_key, mapping={"first_ts": now, "last_ts": now})
    else:
        r.hset(meta_key, "last_ts", now)

    r.expire(buf_key, BUFFER_TTL)
    r.expire(meta_key, BUFFER_TTL)


def should_flush(r: Redis, session_id: str) -> bool:
    now = int(time.time())
    meta = r.hgetall(_meta_key(session_id))
    if not meta:
        return False

    first_ts = int(meta.get("first_ts", 0))
    last_ts = int(meta.get("last_ts", 0))

    if now - last_ts >= FLUSH_SILENCE_SEC:
        return True
    if now - first_ts >= MAX_WAIT_SEC:
        return True

    texts = r.lrange(_buffer_key(session_id), 0, -1)
    if sum(len(t) for t in texts) >= MAX_CHARS:
        return True

    return False


def flush_buffer(r: Redis, session_id: str) -> Optional[str]:
    lock_key = _lock_key(session_id)
    if not r.set(lock_key, "1", nx=True, ex=5):
        return None

    try:
        texts = r.lrange(_buffer_key(session_id), 0, -1)
        if not texts:
            return None
        r.delete(_buffer_key(session_id))
        r.delete(_meta_key(session_id))
        return "\n".join(texts)
    finally:
        r.delete(lock_key)
