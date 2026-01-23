from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.session import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    # Parent conversation row
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    # user | assistant | system
    role = Column(String, nullable=False)
    # Raw message content
    content = Column(String, nullable=False)
    # Optional intent tag for analytics/routing
    intent = Column(String, nullable=True)
    # Model metadata (tokens, model name, channel, etc.)
    meta = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
