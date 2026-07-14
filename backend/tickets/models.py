from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class TicketCreate(BaseModel):
    client_id: int
    title: str
    description: str | None = None


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class TicketStatusUpdate(BaseModel):
    status: Literal["pending", "in_progress", "ready", "delivered", "cancelled"]


class TicketResponse(BaseModel):
    id: int
    client_id: int
    title: str
    description: str | None
    status: str
    received_at: datetime
    ready_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime
    whatsapp_notification_sent: bool | None = None
    whatsapp_notification_error: str | None = None

