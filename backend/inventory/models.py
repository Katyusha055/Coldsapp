from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictInt, StringConstraints, field_validator

# Upper bound for any single quantity, count or threshold in one request. A
# small repair shop never moves thousands of one part at once, and the cap
# keeps a typo from landing (or overflowing the INTEGER column as a 500).
MAX_QUANTITY = 5000

ItemName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class ItemCreate(BaseModel):
    name: ItemName
    quantity: StrictInt = Field(ge=0, le=MAX_QUANTITY)
    low_stock_threshold: StrictInt | None = Field(default=None, ge=0, le=MAX_QUANTITY)
    code: str | None = None


class ItemUpdate(BaseModel):
    name: ItemName | None = None
    low_stock_threshold: StrictInt | None = Field(default=None, ge=0, le=MAX_QUANTITY)

    @field_validator("name")
    @classmethod
    def name_not_null(cls, value):
        # Only runs when the client sends "name"; null would violate NOT NULL.
        if value is None:
            raise ValueError("name cannot be null")
        return value


class MovementCreate(BaseModel):
    type: Literal["entry", "exit"]
    quantity: StrictInt = Field(gt=0, le=MAX_QUANTITY)
    note: str | None = None


class ItemCount(BaseModel):
    counted: StrictInt = Field(ge=0, le=MAX_QUANTITY)


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
