# apps/sns-connector/app/main.py
from fastapi import FastAPI

from .services.common import close_clients
from .services.instagram import router as instagram_router
from .services.kakao import router as kakao_router

app = FastAPI()
app.include_router(kakao_router)
app.include_router(instagram_router)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await close_clients()
