import logging
import os

import httpx

logger = logging.getLogger(__name__)
commerce_base_url = os.getenv("COMMERCE_MANAGEMENT_URL", "http://commerce_management:8000")
commerce_client = httpx.AsyncClient(timeout=5.0)

DEFAULT_REPLY = "말씀하신 내용 확인중입니다. 곧 회신 드릴게요."


async def call_commerce_management(session_id: str, message: str) -> str:
    try:
        response = await commerce_client.post(
            f"{commerce_base_url}/api/v1/chat",
            json={"session_id": session_id, "message": message},
        )
        if response.status_code == 200:
            return response.json().get("reply", DEFAULT_REPLY)
    except httpx.RequestError:
        logger.exception("commerce_management request failed")
    return DEFAULT_REPLY


async def close_clients() -> None:
    await commerce_client.aclose()
