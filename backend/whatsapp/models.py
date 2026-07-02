from pydantic import BaseModel

class QrResponse(BaseModel):
    qr: str


class StatusResponse(BaseModel):
    status: str
