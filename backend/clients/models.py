from pydantic import BaseModel

class CreateClient(BaseModel):
    name = str
    phone = str 
    description = str | None = None

class ResponseClient(BaseModel):
    name = str
    phone = str 
    created_at = str
    id = int
    description = str | None = None

