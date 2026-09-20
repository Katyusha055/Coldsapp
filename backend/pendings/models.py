from typing import Literal
from pydantic import BaseModel

class PendingStatusUpdate(BaseModel):
    status: Literal["converted", "discarded"]
