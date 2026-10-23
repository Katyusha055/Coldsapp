from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

ItemName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class ItemCreate(BaseModel):
    name: ItemName
    quantity: int = Field(ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    code: str | None = None


class ItemUpdate(BaseModel):
    name: ItemName | None = None
    low_stock_threshold: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def name_not_null(cls, value):
        # Only runs when the client sends "name"; null would violate NOT NULL.
        if value is None:
            raise ValueError("name cannot be null")
        return value


class MovementCreate(BaseModel):
    type: Literal["in", "out"]
    quantity: int = Field(gt=0)
    note: str | None = None


class ItemCount(BaseModel):
    counted: int = Field(ge=0)


class CodeLink(BaseModel):
    code: str


class ItemResponse(BaseModel):
    id: int
    name: str
    low_stock_threshold: int | None
    stock: int
    codes: list[str]
    created_at: datetime


class MovementResponse(BaseModel):
    id: int
    quantity: int
    type: str
    note: str | None
    created_at: datetime
