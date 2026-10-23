from fastapi import HTTPException

import backend.inventory.repository as rep
from backend.shared.connect import connect


def _normalize_code(raw: str) -> str:
    """
    Normalizes a barcode to its canonical 13-digit EAN-13 form. Only EAN-13
    and UPC-A are supported: a 12-digit UPC-A is the same code as the EAN-13
    with a leading 0, so it gets one. The check digit is validated.

    Raises HTTPException(422) for anything that isn't a valid EAN-13/UPC-A.
    """
    code = raw.strip()
    if not code.isdigit() or len(code) not in (12, 13):
        raise HTTPException(status_code=422, detail="Code must be a 12-digit UPC-A or 13-digit EAN-13")
    if len(code) == 12:
        code = "0" + code

    weighted_sum = sum(int(digit) * (3 if index % 2 else 1) for index, digit in enumerate(code[:12]))
    if (10 - weighted_sum % 10) % 10 != int(code[12]):
        raise HTTPException(status_code=422, detail="Invalid barcode check digit")
    return code


def _get_item_or_404(conn, user_id, item_id) -> dict:
    item = rep.get_item(conn, user_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


def _link_code_or_409(conn, user_id, item_id, code) -> None:
    """
    Links a normalized code to an item. Re-linking a code to the item it's
    already on is a no-op; a code on any other item of the user is a 409.
    """
    linked_item_id = rep.get_item_id_by_code(conn, user_id, code)
    if linked_item_id == item_id:
        return
    if linked_item_id is not None or not rep.link_code(conn, user_id, item_id, code):
        raise HTTPException(status_code=409, detail="Code already linked to another item")


def list_items(user_id) -> list[dict]:
    with connect() as conn:
        return rep.list_items(conn, user_id)


def get_item(user_id, item_id) -> dict:
    with connect() as conn:
        return _get_item_or_404(conn, user_id, item_id)


def create_item(user_id, data: dict) -> dict:
    """
    Quick add, in one transaction: the item, an 'initial' movement when the
    quantity is above 0, and the code when one is given.
    """
    code = _normalize_code(data["code"]) if data.get("code") is not None else None
    with connect() as conn:
        item_id = rep.create_item(conn, user_id, data["name"], data.get("low_stock_threshold"))
        if data["quantity"] > 0:
            rep.insert_movement(conn, user_id, item_id, data["quantity"], "initial")
        if code is not None:
            _link_code_or_409(conn, user_id, item_id, code)
        created_item = _get_item_or_404(conn, user_id, item_id)
    return created_item


def update_item(user_id, item_id, data: dict) -> dict:
    """
    Input dict: only the fields the client actually sent, so an explicit
    low_stock_threshold of None clears the alert.
    """
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    with connect() as conn:
        if not rep.update_item(conn, user_id, item_id, data):
            raise HTTPException(status_code=404, detail="Item not found")
        updated_item = _get_item_or_404(conn, user_id, item_id)
    return updated_item


def deactivate_item(user_id, item_id) -> None:
    """
    Soft-deletes the item and frees its codes for reuse, in one transaction.
    """
    with connect() as conn:
        if not rep.deactivate_item(conn, user_id, item_id):
            raise HTTPException(status_code=404, detail="Item not found")
        rep.delete_item_codes(conn, user_id, item_id)


def add_movement(user_id, item_id, movement_type, quantity, note=None) -> dict:
    """
    Records an 'in' or 'out' of a positive quantity; 'out' is stored
    negative. Stock is allowed to go negative.
    """
    signed_quantity = -quantity if movement_type == "out" else quantity
    with connect() as conn:
        item_before = _get_item_or_404(conn, user_id, item_id)
        rep.insert_movement(conn, user_id, item_before["id"], signed_quantity, movement_type, note)
        item_after = _get_item_or_404(conn, user_id, item_id)
    return item_after


def count_item(user_id, item_id, counted) -> dict:
    """
    Quick count: the client sends the quantity it physically counted. The
    item row is locked so two counts can't both read the same stock, and an
    'adjustment' for the difference is inserted only when there is one.
    """
    with connect() as conn:
        current = rep.lock_item_stock(conn, user_id, item_id)
        if current is None:
            raise HTTPException(status_code=404, detail="Item not found")
        if counted != current:
            rep.insert_movement(conn, user_id, item_id, counted - current, "adjustment")
        counted_item = _get_item_or_404(conn, user_id, item_id)
    return counted_item


def list_movements(user_id, item_id) -> list[dict]:
    with connect() as conn:
        _get_item_or_404(conn, user_id, item_id)
        return rep.list_movements(conn, user_id, item_id)


def get_item_by_code(user_id, raw_code) -> dict:
    code = _normalize_code(raw_code)
    with connect() as conn:
        item_id = rep.get_item_id_by_code(conn, user_id, code)
        if item_id is None:
            raise HTTPException(status_code=404, detail="Code not linked to any item")
        return _get_item_or_404(conn, user_id, item_id)


def link_code(user_id, item_id, raw_code) -> dict:
    code = _normalize_code(raw_code)
    with connect() as conn:
        item_before = _get_item_or_404(conn, user_id, item_id)
        _link_code_or_409(conn, user_id, item_before["id"], code)
        item_after = _get_item_or_404(conn, user_id, item_id)
    return item_after


def unlink_code(user_id, item_id, raw_code) -> None:
    code = _normalize_code(raw_code)
    with connect() as conn:
        _get_item_or_404(conn, user_id, item_id)
        if not rep.unlink_code(conn, user_id, item_id, code):
            raise HTTPException(status_code=404, detail="Code not linked to this item")
