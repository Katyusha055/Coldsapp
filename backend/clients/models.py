from pydantic import BaseModel


class CreateClient(BaseModel):
    user_id: int
    name: str
    phone: str
    description: str | None = None


class ResponseClient(BaseModel):
    id: int
    user_id: int
    name: str
    phone: str
    created_at: str
    description: str | None = None

class UpdateClient(BaseModel):
    user_id: int
    name: str | None = None
    phone: str | None = None 
    description: str | None = None