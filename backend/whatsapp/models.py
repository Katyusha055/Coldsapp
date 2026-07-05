from typing import Literal
from pydantic import BaseModel

class QrResponse(BaseModel):
    qr: str


class StatusResponse(BaseModel):
    status: str


class PendingStatusUpdate(BaseModel):
    status: Literal["converted", "discarded"]
