from datetime import datetime
from pydantic import BaseModel


class WhatsAppInstance(BaseModel):
    id: int
    user_id: int
    instance_name: str
    status: str
    created_at: datetime
    connected_at: datetime | None = None


class QrResponse(BaseModel):
    qr: str


class StatusResponse(BaseModel):
    status: str
