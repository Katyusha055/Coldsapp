from pydantic import BaseModel


class CreateClient(BaseModel):
    name: str
    phone: str
    description: str | None = None


class ResponseClient(BaseModel):
    name: str
    phone: str
    created_at: str
    description: str | None = None

class UpdateClient(BaseModel):
    name: str | None = None
    phone: str | None = None 
    description: str | None = None