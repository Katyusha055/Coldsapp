from typing import Literal
from pydantic import BaseModel

class QrResponse(BaseModel):
    qr: str


class StatusResponse(BaseModel):
    status: str
    notifications_enabled: bool = True


class PendingStatusUpdate(BaseModel):
    status: Literal["converted", "discarded"]


class NotificationsToggle(BaseModel):
    enabled: bool
