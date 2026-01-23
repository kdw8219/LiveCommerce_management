
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from app.api.v1.route import api_router as MainRouter
from app.db.session import Base, engine
from app.db import models  # noqa: F401

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(title="jooneyshop_chatbot", version="0.0.1")
app.include_router(router=MainRouter, prefix="/api/v1")


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
