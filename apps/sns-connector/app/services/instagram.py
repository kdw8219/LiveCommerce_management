import asyncio
import hmac
import os
from typing import List, Tuple

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from .common import call_commerce_management, commerce_client, logger

router = APIRouter()


def extract_instagram_messages(payload: dict) -> List[Tuple[str, str]]:
    messages: List[Tuple[str, str]] = []
    entries = payload.get("entry")
    if not isinstance(entries, list):
        return messages
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        messaging = entry.get("messaging")
        if not isinstance(messaging, list):
            continue
        for event in messaging:
            if not isinstance(event, dict):
                continue
            message = event.get("message")
            if not isinstance(message, dict):
                continue
            text = message.get("text")
            if not text:
                continue
            sender = event.get("sender")
            if not isinstance(sender, dict):
                continue
            sender_id = sender.get("id")
            if not sender_id:
                continue
            messages.append((sender_id, text))
    return messages


async def send_instagram_message(recipient_id: str, text: str) -> None:
    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    if not access_token:
        logger.warning("instagram access token missing")
        return
    try:
        response = await commerce_client.post(
            "https://graph.facebook.com/v18.0/me/messages",
            params={"access_token": access_token},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": text},
                "messaging_type": "RESPONSE",
            },
        )
        if response.status_code >= 400:
            logger.warning("instagram send failed status=%s body=%s", response.status_code, response.text)
    except httpx.RequestError:
        logger.exception("instagram send failed")


async def handle_instagram_message(sender_id: str, text: str) -> None:
    reply = await call_commerce_management(sender_id, text)
    await send_instagram_message(sender_id, reply)


@router.get("/webhook/instagram")
async def instagram_verify(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
):
    verify_token = os.getenv("INSTAGRAM_VERIFY_TOKEN", "")
    if hub_mode == "subscribe" and verify_token and hmac.compare_digest(hub_verify_token, verify_token):
        return hub_challenge
    raise HTTPException(status_code=403, detail="invalid verify token")


@router.post("/webhook/instagram")
async def instagram_webhook(request: Request):
    payload = await request.json()
    if not isinstance(payload, dict):
        return {"status": "ignored"}

    messages = extract_instagram_messages(payload)
    if not messages:
        return {"status": "ignored"}

    for sender_id, text in messages:
        asyncio.create_task(handle_instagram_message(sender_id, text))

    return {"status": "ok"}
