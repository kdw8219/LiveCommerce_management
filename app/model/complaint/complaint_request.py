from pydantic import BaseModel


class ComplaintRequest(BaseModel):
    session_id: str
    summary: str
