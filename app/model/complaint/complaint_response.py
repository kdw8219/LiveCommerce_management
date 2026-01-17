from pydantic import BaseModel
from typing import List, Optional


class ComplaintResponse(BaseModel):
    id: int
    session_id: str
    status: str
    summary: str
    evidence_message_ids: Optional[List[int]] = None
