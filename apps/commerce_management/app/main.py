
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from app.api.v1.route import api_router as MainRouter

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(title="jooneyshop_chatbot", version="0.0.1")
app.include_router(router=MainRouter, prefix="/api/v1")
