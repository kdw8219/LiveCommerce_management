import os
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-default-api-key")
MODEL = os.getenv("MODEL", "gpt-4")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="jooneyshop_chatbot", version="0.0.1")