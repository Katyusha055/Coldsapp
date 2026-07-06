from pydantic import BaseModel, field_validator


class CreateClient(BaseModel):
    name: str
    phone: str
    description: str | None = None
    whatsapp_id: str | None = None

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if not v.isdigit() or len(v) != 10:
            raise ValueError('Phone must be exactly 10 digits')
        return v


class ResponseClient(BaseModel):
    id: int
    name: str
    phone: str
    created_at: str
    description: str | None = None
    whatsapp_id: str | None = None

class UpdateClient(BaseModel):
    name: str | None = None
    phone: str | None = None
    description: str | None = None
    whatsapp_id: str | None = None

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return v
        if not v.isdigit() or len(v) != 10:
            raise ValueError('Phone must be exactly 10 digits')
        return v