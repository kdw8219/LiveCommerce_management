from pydantic import BaseModel
from typing import List, Optional


class ComplaintRequest(BaseModel):
    session_id: str
    summary: str
    evidence_message_ids: Optional[List[int]] = None
