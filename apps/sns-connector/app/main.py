# apps/sns-connector/app/main.py
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .services.common import close_clients
from .services.instagram import router as instagram_router
from .services.kakao import router as kakao_router

app = FastAPI()
app.include_router(kakao_router)
app.include_router(instagram_router)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await close_clients()
