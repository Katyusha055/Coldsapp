from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: int


class UserCreate(BaseModel):
    name: str
    phone: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    phone: str
