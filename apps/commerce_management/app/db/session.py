import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)


def _build_database_url() -> str:
    if os.getenv("DB_HOST") or os.getenv("DB_USER") or os.getenv("DB_PWD") or os.getenv("DB_NAME") or os.getenv("DB_ADMIN_TABLE"):
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        user = os.getenv("DB_USER", "user")
        password = os.getenv("DB_PWD", "pass")
        name = os.getenv("DB_NAME")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    return "postgresql+psycopg2://user:pass@localhost:5432/db"


DATABASE_URL = _build_database_url()

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()
