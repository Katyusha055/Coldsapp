from pydantic import BaseModel

class QrResponse(BaseModel):
    qr: str


class StatusResponse(BaseModel):
    status: str
    notifications_enabled: bool = True


class NotificationsToggle(BaseModel):
    enabled: bool
