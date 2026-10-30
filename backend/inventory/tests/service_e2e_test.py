import pytest
from fastapi import HTTPException

import backend.inventory.service as service
from backend.shared.connect import connect

UNKNOWN_ITEM_ID = 999999
UNLINKED_CODE = "9780201379624"
OTHER_UNLINKED_CODE = "8410076472816"
UPC_A_CODE = "012345678905"
UPC_A_AS_EAN_13 = "0012345678905"
BAD_CHECK_DIGIT_CODE = "4006381333932"


def _quick_add(user_id, name, quantity=0, code=None, low_stock_threshold=None):
    return service.create_item(
        user_id,
        {"name": name, "quantity": quantity, "low_stock_threshold": low_stock_threshold, "code": code},
    )


def _movement_rows(item_id):
    with connect() as conn:
        return conn.execute(
            "SELECT type, quantity FROM stock_movements WHERE item_id = %s ORDER BY id",
            (item_id,),
        ).fetchall()


def _item_count_named(user_id, name):
    with connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM items WHERE user_id = %s AND name = %s",
            (user_id, name),
        ).fetchone()[0]


def _status_of(call):
    with pytest.raises(HTTPException) as raised:
        call()
    return raised.value.status_code


# --- GET /items/ ---


def test_list_items_returns_active_items_with_stock_and_codes_ordered_by_name(tenants):
    user_id = tenants["a"]["user_id"]
    _quick_add(user_id, "Zeta", quantity=2)
    _quick_add(user_id, "Alfa", quantity=1)

    items = service.list_items(user_id)

    assert [item["name"] for item in items] == ["Alfa", "Disco A", "Zeta"]
    fixture_item = next(item for item in items if item["name"] == "Disco A")
    assert fixture_item["stock"] == 5
    assert fixture_item["codes"] == [tenants["a"]["code"]]


def test_list_items_counts_stock_once_for_an_item_with_several_codes(tenants):
    user_id = tenants["a"]["user_id"]
    item_id = tenants["a"]["item_id"]
    service.link_code(user_id, item_id, UNLINKED_CODE)
    service.add_movement(user_id, item_id, "entry", 3)
    service.add_movement(user_id, item_id, "exit", 1)

    listed = next(item for item in service.list_items(user_id) if item["id"] == item_id)

    assert len(listed["codes"]) == 2
    assert listed["stock"] == 5 + 3 - 1


# --- GET /items/{id} ---


def test_get_item_returns_the_item_with_stock_and_codes(tenants):
    item = service.get_item(tenants["a"]["user_id"], tenants["a"]["item_id"])

    assert item["name"] == "Disco A"
    assert item["stock"] == 5
    assert item["codes"] == [tenants["a"]["code"]]


def test_get_item_rejects_an_unknown_item(tenants):
    assert _status_of(lambda: service.get_item(tenants["a"]["user_id"], UNKNOWN_ITEM_ID)) == 404


def test_get_item_reports_zero_stock_and_no_codes_for_an_untouched_item(tenants):
    created = _quick_add(tenants["a"]["user_id"], "Vacío")

    item = service.get_item(tenants["a"]["user_id"], created["id"])

    assert item["stock"] == 0
    assert item["codes"] == []


# --- POST /items/ ---


def test_create_item_records_the_initial_quantity_and_stores_the_code_canonically(tenants):
    created = _quick_add(tenants["a"]["user_id"], "Memoria", quantity=3, code=UPC_A_CODE)

    assert created["stock"] == 3
    assert created["codes"] == [UPC_A_AS_EAN_13]
    assert _movement_rows(created["id"]) == [("initial_adjustment", 3)]


def test_create_item_with_zero_quantity_records_no_movement(tenants):
    created = _quick_add(tenants["a"]["user_id"], "Cable", quantity=0)

    assert created["stock"] == 0
    assert _movement_rows(created["id"]) == []


def test_create_item_rejects_a_code_already_linked_or_an_invalid_code(tenants):
    user_id = tenants["a"]["user_id"]

    assert _status_of(lambda: _quick_add(user_id, "Duplicado", quantity=1, code=tenants["a"]["code"])) == 409
    assert _status_of(lambda: _quick_add(user_id, "Mal dígito", quantity=1, code=BAD_CHECK_DIGIT_CODE)) == 422
    assert _status_of(lambda: _quick_add(user_id, "Letras", quantity=1, code="ABC123456789X")) == 422


def test_create_item_leaves_nothing_behind_when_the_code_conflicts(tenants):
    user_id = tenants["a"]["user_id"]

    assert _status_of(lambda: _quick_add(user_id, "Fantasma", quantity=7, code=tenants["a"]["code"])) == 409

    assert _item_count_named(user_id, "Fantasma") == 0
    assert [item["name"] for item in service.list_items(user_id)] == ["Disco A"]


# --- PATCH /items/{id} ---


def test_update_item_changes_sent_fields_and_leaves_omitted_ones(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]
    service.update_item(user_id, item_id, {"low_stock_threshold": 2})

    updated = service.update_item(user_id, item_id, {"name": "Disco 2TB"})

    assert updated["name"] == "Disco 2TB"
    assert updated["low_stock_threshold"] == 2


def test_update_item_rejects_an_empty_update_or_a_missing_item(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]
    deactivated = _quick_add(user_id, "Viejo")
    service.deactivate_item(user_id, deactivated["id"])

    assert _status_of(lambda: service.update_item(user_id, item_id, {})) == 400
    assert _status_of(lambda: service.update_item(user_id, UNKNOWN_ITEM_ID, {"name": "x"})) == 404
    assert _status_of(lambda: service.update_item(user_id, deactivated["id"], {"name": "x"})) == 404


def test_update_item_with_a_null_threshold_clears_the_alert(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]
    service.update_item(user_id, item_id, {"low_stock_threshold": 2})

    updated = service.update_item(user_id, item_id, {"low_stock_threshold": None})

    assert updated["low_stock_threshold"] is None


# --- DELETE /items/{id} ---


def test_deactivate_item_hides_it_but_keeps_its_movements(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]

    service.deactivate_item(user_id, item_id)

    assert service.list_items(user_id) == []
    assert _status_of(lambda: service.get_item(user_id, item_id)) == 404
    assert _movement_rows(item_id) == [("initial_adjustment", 5)]


def test_deactivate_item_rejects_an_unknown_or_already_deactivated_item(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]
    service.deactivate_item(user_id, item_id)

    assert _status_of(lambda: service.deactivate_item(user_id, UNKNOWN_ITEM_ID)) == 404
    assert _status_of(lambda: service.deactivate_item(user_id, item_id)) == 404


def test_deactivate_item_frees_its_code_for_another_item(tenants):
    user_id, item_id, code = tenants["a"]["user_id"], tenants["a"]["item_id"], tenants["a"]["code"]
    service.deactivate_item(user_id, item_id)

    replacement = _quick_add(user_id, "Reemplazo", code=code)

    assert replacement["codes"] == [code]


# --- POST /items/{id}/movements ---


def test_add_movement_applies_the_sign_from_the_type(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]

    after_entry = service.add_movement(user_id, item_id, "entry", 4)
    after_exit = service.add_movement(user_id, item_id, "exit", 4)

    assert after_entry["stock"] == 9
    assert after_exit["stock"] == 5
    assert _movement_rows(item_id)[1:] == [("entry", 4), ("exit", -4)]


def test_add_movement_rejects_an_unknown_or_deactivated_item(tenants):
    user_id = tenants["a"]["user_id"]
    deactivated = _quick_add(user_id, "Viejo")
    service.deactivate_item(user_id, deactivated["id"])

    assert _status_of(lambda: service.add_movement(user_id, UNKNOWN_ITEM_ID, "entry", 1)) == 404
    assert _status_of(lambda: service.add_movement(user_id, deactivated["id"], "entry", 1)) == 404


def test_add_movement_allows_stock_to_go_negative(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]

    after_exit = service.add_movement(user_id, item_id, "exit", 7)

    assert after_exit["stock"] == -2


# --- POST /items/{id}/count ---


def test_count_item_inserts_the_difference_as_a_manual_adjustment(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]
    service.add_movement(user_id, item_id, "entry", 1)

    counted = service.count_item(user_id, item_id, 4)

    assert counted["stock"] == 4
    assert _movement_rows(item_id)[-1] == ("manual_adjustment", -2)


def test_count_item_rejects_an_unknown_or_deactivated_item(tenants):
    user_id = tenants["a"]["user_id"]
    deactivated = _quick_add(user_id, "Viejo")
    service.deactivate_item(user_id, deactivated["id"])

    assert _status_of(lambda: service.count_item(user_id, UNKNOWN_ITEM_ID, 1)) == 404
    assert _status_of(lambda: service.count_item(user_id, deactivated["id"], 1)) == 404


def test_count_item_matching_the_stock_inserts_no_movement(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]

    counted = service.count_item(user_id, item_id, 5)

    assert counted["stock"] == 5
    assert _movement_rows(item_id) == [("initial_adjustment", 5)]


# --- GET /items/{id}/movements ---


def test_list_movements_returns_history_newest_first(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]
    service.add_movement(user_id, item_id, "entry", 2)
    service.add_movement(user_id, item_id, "exit", 1, note="usado en reparación")

    history = service.list_movements(user_id, item_id)

    assert [(movement["type"], movement["quantity"]) for movement in history] == [
        ("exit", -1),
        ("entry", 2),
        ("initial_adjustment", 5),
    ]
    assert history[0]["note"] == "usado en reparación"


def test_list_movements_rejects_an_unknown_or_deactivated_item(tenants):
    user_id = tenants["a"]["user_id"]
    deactivated = _quick_add(user_id, "Viejo")
    service.deactivate_item(user_id, deactivated["id"])

    assert _status_of(lambda: service.list_movements(user_id, UNKNOWN_ITEM_ID)) == 404
    assert _status_of(lambda: service.list_movements(user_id, deactivated["id"])) == 404


def test_list_movements_is_empty_for_an_item_created_without_quantity(tenants):
    created = _quick_add(tenants["a"]["user_id"], "Vacío")

    assert service.list_movements(tenants["a"]["user_id"], created["id"]) == []


# --- GET /items/by-code/{code} ---


def test_get_item_by_code_finds_the_linked_item(tenants):
    found = service.get_item_by_code(tenants["a"]["user_id"], tenants["a"]["code"])

    assert found["id"] == tenants["a"]["item_id"]


def test_get_item_by_code_rejects_unknown_and_invalid_codes(tenants):
    user_id = tenants["a"]["user_id"]

    assert _status_of(lambda: service.get_item_by_code(user_id, UNLINKED_CODE)) == 404
    assert _status_of(lambda: service.get_item_by_code(user_id, BAD_CHECK_DIGIT_CODE)) == 422
    assert _status_of(lambda: service.get_item_by_code(user_id, "12345")) == 422


def test_get_item_by_code_finds_an_ean_13_link_from_its_upc_a_form(tenants):
    user_id = tenants["a"]["user_id"]
    created = _quick_add(user_id, "Memoria", code=UPC_A_AS_EAN_13)

    found = service.get_item_by_code(user_id, f"  {UPC_A_CODE} ")

    assert found["id"] == created["id"]


# --- POST /items/{id}/codes ---


def test_link_code_adds_the_code_in_canonical_form(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]

    linked = service.link_code(user_id, item_id, UPC_A_CODE)

    assert sorted(linked["codes"]) == sorted([tenants["a"]["code"], UPC_A_AS_EAN_13])


def test_link_code_rejects_a_conflict_an_invalid_code_or_a_missing_item(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]
    other = _quick_add(user_id, "Otro")

    assert _status_of(lambda: service.link_code(user_id, other["id"], tenants["a"]["code"])) == 409
    assert _status_of(lambda: service.link_code(user_id, item_id, BAD_CHECK_DIGIT_CODE)) == 422
    assert _status_of(lambda: service.link_code(user_id, UNKNOWN_ITEM_ID, UNLINKED_CODE)) == 404


def test_link_code_to_the_item_it_is_already_on_changes_nothing(tenants):
    user_id, item_id, code = tenants["a"]["user_id"], tenants["a"]["item_id"], tenants["a"]["code"]

    relinked = service.link_code(user_id, item_id, code)

    assert relinked["codes"] == [code]


# --- DELETE /items/{id}/codes/{code} ---


def test_unlink_code_removes_it_so_lookup_no_longer_finds_it(tenants):
    user_id, item_id, code = tenants["a"]["user_id"], tenants["a"]["item_id"], tenants["a"]["code"]

    service.unlink_code(user_id, item_id, code)

    assert service.get_item(user_id, item_id)["codes"] == []
    assert _status_of(lambda: service.get_item_by_code(user_id, code)) == 404


def test_unlink_code_rejects_a_code_not_on_this_item_or_an_invalid_code(tenants):
    user_id, item_id = tenants["a"]["user_id"], tenants["a"]["item_id"]

    assert _status_of(lambda: service.unlink_code(user_id, item_id, OTHER_UNLINKED_CODE)) == 404
    assert _status_of(lambda: service.unlink_code(user_id, item_id, BAD_CHECK_DIGIT_CODE)) == 422


def test_unlink_code_frees_it_for_a_different_item(tenants):
    user_id, item_id, code = tenants["a"]["user_id"], tenants["a"]["item_id"], tenants["a"]["code"]
    other = _quick_add(user_id, "Otro")
    service.unlink_code(user_id, item_id, code)

    relinked = service.link_code(user_id, other["id"], code)

    assert relinked["codes"] == [code]
