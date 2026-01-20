from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func

from app.db.session import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    # Parent conversation row; complaint is derived from a session
    conversation_id = Column(Integer, nullable=False)
    # Evidence message IDs that triggered the complaint summary
    evidence_message_ids = Column(ARRAY(Integer), nullable=True)
    # open | closed
    status = Column(String, default="open", nullable=False)
    # AI-generated summary of the complaint
    summary = Column(String, nullable=False)
    assigned_to = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
