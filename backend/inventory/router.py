from typing import Annotated

from fastapi import APIRouter, Path, Response

import backend.inventory.models as mdl
import backend.inventory.service as ser
from backend.auth.utils import CurrentUser

CodePath = Annotated[str, Path(max_length=mdl.MAX_CODE_INPUT_LENGTH)]

router = APIRouter(
    prefix="/items",
    tags=["inventory"],
)


@router.get("/", response_model=list[mdl.ItemResponse])
def list_items_endpoint(user: CurrentUser):
    return ser.list_items(user["id"])


@router.post("/", response_model=mdl.ItemResponse)
def create_item_endpoint(payload: mdl.ItemCreate, user: CurrentUser):
    return ser.create_item(user["id"], payload.model_dump())


@router.get("/by-code/{code}", response_model=mdl.ItemResponse)
def get_item_by_code_endpoint(code: CodePath, user: CurrentUser):
    return ser.get_item_by_code(user["id"], code)


@router.get("/{item_id}", response_model=mdl.ItemResponse)
def get_item_endpoint(item_id: int, user: CurrentUser):
    return ser.get_item(user["id"], item_id)


@router.patch("/{item_id}", response_model=mdl.ItemResponse)
def update_item_endpoint(item_id: int, payload: mdl.ItemUpdate, user: CurrentUser):
    # exclude_unset: an omitted field is left alone, an explicit null clears it.
    return ser.update_item(user["id"], item_id, payload.model_dump(exclude_unset=True))


@router.delete("/{item_id}", status_code=204)
def deactivate_item_endpoint(item_id: int, user: CurrentUser):
    ser.deactivate_item(user["id"], item_id)
    return Response(status_code=204)


@router.post("/{item_id}/movements", response_model=mdl.ItemResponse)
def add_movement_endpoint(item_id: int, payload: mdl.MovementCreate, user: CurrentUser):
    return ser.add_movement(user["id"], item_id, payload.type, payload.quantity, payload.note)


@router.get("/{item_id}/movements", response_model=list[mdl.MovementResponse])
def list_movements_endpoint(item_id: int, user: CurrentUser):
    return ser.list_movements(user["id"], item_id)


@router.post("/{item_id}/count", response_model=mdl.ItemResponse)
def count_item_endpoint(item_id: int, payload: mdl.ItemCount, user: CurrentUser):
    return ser.count_item(user["id"], item_id, payload.counted)


@router.post("/{item_id}/codes", response_model=mdl.ItemResponse)
def link_code_endpoint(item_id: int, payload: mdl.CodeLink, user: CurrentUser):
    return ser.link_code(user["id"], item_id, payload.code)


@router.delete("/{item_id}/codes/{code}", status_code=204)
def unlink_code_endpoint(item_id: int, code: CodePath, user: CurrentUser):
    ser.unlink_code(user["id"], item_id, code)
    return Response(status_code=204)
