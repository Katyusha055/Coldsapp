from datetime import datetime

from pydantic import BaseModel


class ImportResult(BaseModel):
    imported: int


class ContactResponse(BaseModel):
    id: int
    remote_jid: str
    name: str | None = None
    opted_out: bool
    last_incoming_at: datetime | None = None
    last_broadcast_at: datetime | None = None
    created_at: datetime


class ContactNameUpdate(BaseModel):
    name: str


class ContactOptedOutUpdate(BaseModel):
    opted_out: bool
