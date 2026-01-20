
from dotenv import load_dotenv
from fastapi import FastAPI
from app.api.v1.route import api_router as MainRouter

load_dotenv()

app = FastAPI(title="jooneyshop_chatbot", version="0.0.1")
app.include_router(router=MainRouter, prefix="/api/v1")