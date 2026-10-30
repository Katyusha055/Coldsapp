from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import HTTPException

import backend.inventory.service as service

ITEM_ID = 7
VALID_CODE = "4006381333931"


def _item(**overrides):
    """
    A service return value shaped exactly like the repository's item dict, so
    the API layer is exercised against the real response shape.
    """
    item = {
        "id": ITEM_ID,
        "name": "Disco",
        "low_stock_threshold": None,
        "created_at": datetime(2026, 10, 30, tzinfo=UTC),
        "stock": 5,
        "codes": [VALID_CODE],
    }
    return {**item, **overrides}


def _movement(**overrides):
    movement = {
        "id": 1,
        "quantity": 5,
        "type": "initial_adjustment",
        "note": None,
        "created_at": datetime(2026, 10, 30, tzinfo=UTC),
    }
    return {**movement, **overrides}


@pytest.fixture()
def user(create_user, api_client):
    """
    A real registered user and bearer headers: CurrentUser loads the user
    from the DB, so auth stays real while the service is mocked.
    """
    created = create_user("3333333333", name="API User")
    token_response = api_client.post("/auth/token", data={"username": "3333333333", "password": "testpassword"})
    return {"id": created["id"], "headers": {"Authorization": f"Bearer {token_response.json()['access_token']}"}}


def _mock(function_name, **kwargs):
    return patch.object(service, function_name, **kwargs)


# --- GET /items/ ---


def test_list_items_endpoint_serializes_items_for_the_caller(api_client, user):
    with _mock("list_items", return_value=[_item()]) as mocked:
        response = api_client.get("/items/", headers=user["headers"])

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": ITEM_ID,
            "name": "Disco",
            "low_stock_threshold": None,
            "stock": 5,
            "codes": [VALID_CODE],
            "created_at": "2026-10-30T00:00:00Z",
        }
    ]
    mocked.assert_called_once_with(user["id"])


def test_list_items_endpoint_rejects_a_request_without_a_token(api_client):
    with _mock("list_items") as mocked:
        response = api_client.get("/items/")

    assert response.status_code == 401
    mocked.assert_not_called()


def test_list_items_endpoint_returns_an_empty_list_not_a_404(api_client, user):
    with _mock("list_items", return_value=[]):
        response = api_client.get("/items/", headers=user["headers"])

    assert response.status_code == 200
    assert response.json() == []


# --- GET /items/{id} ---


def test_get_item_endpoint_passes_the_id_to_the_service(api_client, user):
    with _mock("get_item", return_value=_item()) as mocked:
        response = api_client.get(f"/items/{ITEM_ID}", headers=user["headers"])

    assert response.status_code == 200
    assert response.json()["id"] == ITEM_ID
    mocked.assert_called_once_with(user["id"], ITEM_ID)


def test_get_item_endpoint_rejects_a_non_integer_id_and_passes_a_404_through(api_client, user):
    with _mock("get_item") as mocked:
        assert api_client.get("/items/abc", headers=user["headers"]).status_code == 422
        mocked.assert_not_called()

    with _mock("get_item", side_effect=HTTPException(status_code=404, detail="Item not found")):
        response = api_client.get(f"/items/{ITEM_ID}", headers=user["headers"])
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


# --- POST /items/ ---


def test_create_item_endpoint_passes_the_body_to_the_service(api_client, user):
    with _mock("create_item", return_value=_item()) as mocked:
        response = api_client.post("/items/", json={"name": "  Disco  ", "quantity": 3}, headers=user["headers"])

    assert response.status_code == 200
    mocked.assert_called_once_with(
        user["id"], {"name": "Disco", "quantity": 3, "low_stock_threshold": None, "code": None}
    )


@pytest.mark.parametrize(
    "body",
    [
        {"name": "Disco", "quantity": -1},
        {"name": "Disco", "quantity": 5001},
        {"name": "Disco", "quantity": 2.5},
        {"name": "Disco", "quantity": "3"},
        {"name": "Disco", "quantity": True},
        {"name": "   ", "quantity": 1},
        {"quantity": 1},
        {"name": "Disco", "quantity": 1, "code": "1" * 65},
    ],
)
def test_create_item_endpoint_rejects_invalid_bodies(api_client, user, body):
    with _mock("create_item") as mocked:
        response = api_client.post("/items/", json=body, headers=user["headers"])

    assert response.status_code == 422
    mocked.assert_not_called()


def test_create_item_endpoint_passes_a_conflict_through(api_client, user):
    conflict = HTTPException(status_code=409, detail="Code already linked to another item")
    with _mock("create_item", side_effect=conflict):
        response = api_client.post(
            "/items/", json={"name": "Disco", "quantity": 1, "code": VALID_CODE}, headers=user["headers"]
        )

    assert response.status_code == 409


def test_create_item_endpoint_accepts_the_limits_and_passes_the_code_raw(api_client, user):
    raw_code = " " * 51 + VALID_CODE
    with _mock("create_item", return_value=_item()) as mocked:
        response = api_client.post(
            "/items/", json={"name": "Disco", "quantity": 5000, "code": raw_code}, headers=user["headers"]
        )

    assert response.status_code == 200
    assert len(raw_code) == 64
    assert mocked.call_args.args[1]["quantity"] == 5000
    assert mocked.call_args.args[1]["code"] == raw_code


# --- PATCH /items/{id} ---


def test_update_item_endpoint_sends_only_the_fields_in_the_body(api_client, user):
    with _mock("update_item", return_value=_item(name="Disco 2TB")) as mocked:
        response = api_client.patch(f"/items/{ITEM_ID}", json={"name": "Disco 2TB"}, headers=user["headers"])

    assert response.status_code == 200
    mocked.assert_called_once_with(user["id"], ITEM_ID, {"name": "Disco 2TB"})


@pytest.mark.parametrize(
    "body",
    [
        {"name": None},
        {"low_stock_threshold": 5001},
        {"low_stock_threshold": "2"},
    ],
)
def test_update_item_endpoint_rejects_invalid_bodies(api_client, user, body):
    with _mock("update_item") as mocked:
        response = api_client.patch(f"/items/{ITEM_ID}", json=body, headers=user["headers"])

    assert response.status_code == 422
    mocked.assert_not_called()


def test_update_item_endpoint_sends_an_explicit_null_but_not_an_omitted_threshold(api_client, user):
    with _mock("update_item", return_value=_item()) as mocked:
        api_client.patch(f"/items/{ITEM_ID}", json={"low_stock_threshold": None}, headers=user["headers"])
        api_client.patch(f"/items/{ITEM_ID}", json={"name": "Disco"}, headers=user["headers"])

    explicit_null_call, omitted_call = mocked.call_args_list
    assert explicit_null_call.args[2] == {"low_stock_threshold": None}
    assert "low_stock_threshold" not in omitted_call.args[2]


# --- DELETE /items/{id} ---


def test_deactivate_item_endpoint_returns_204_with_an_empty_body(api_client, user):
    with _mock("deactivate_item", return_value=None) as mocked:
        response = api_client.delete(f"/items/{ITEM_ID}", headers=user["headers"])

    assert response.status_code == 204
    assert response.content == b""
    mocked.assert_called_once_with(user["id"], ITEM_ID)


def test_deactivate_item_endpoint_passes_a_404_through(api_client, user):
    with _mock("deactivate_item", side_effect=HTTPException(status_code=404, detail="Item not found")):
        response = api_client.delete(f"/items/{ITEM_ID}", headers=user["headers"])

    assert response.status_code == 404


# --- POST /items/{id}/movements ---


def test_add_movement_endpoint_passes_type_quantity_and_note(api_client, user):
    with _mock("add_movement", return_value=_item(stock=9)) as mocked:
        response = api_client.post(
            f"/items/{ITEM_ID}/movements", json={"type": "entry", "quantity": 4}, headers=user["headers"]
        )

    assert response.status_code == 200
    assert response.json()["stock"] == 9
    mocked.assert_called_once_with(user["id"], ITEM_ID, "entry", 4, None)


@pytest.mark.parametrize(
    "body",
    [
        {"type": "in", "quantity": 1},
        {"quantity": 1},
        {"type": "exit", "quantity": 0},
        {"type": "exit", "quantity": 5001},
        {"type": "exit", "quantity": 2.5},
        {"type": "exit", "quantity": "4"},
        {"type": "exit", "quantity": True},
    ],
)
def test_add_movement_endpoint_rejects_invalid_bodies(api_client, user, body):
    with _mock("add_movement") as mocked:
        response = api_client.post(f"/items/{ITEM_ID}/movements", json=body, headers=user["headers"])

    assert response.status_code == 422
    mocked.assert_not_called()


def test_add_movement_endpoint_accepts_the_quantity_limit(api_client, user):
    with _mock("add_movement", return_value=_item()) as mocked:
        response = api_client.post(
            f"/items/{ITEM_ID}/movements", json={"type": "entry", "quantity": 5000}, headers=user["headers"]
        )

    assert response.status_code == 200
    assert mocked.call_args.args[3] == 5000


# --- POST /items/{id}/count ---


def test_count_item_endpoint_passes_the_counted_quantity(api_client, user):
    with _mock("count_item", return_value=_item(stock=4)) as mocked:
        response = api_client.post(f"/items/{ITEM_ID}/count", json={"counted": 4}, headers=user["headers"])

    assert response.status_code == 200
    mocked.assert_called_once_with(user["id"], ITEM_ID, 4)


@pytest.mark.parametrize("counted", [-1, 5001, "3"])
def test_count_item_endpoint_rejects_invalid_counts(api_client, user, counted):
    with _mock("count_item") as mocked:
        response = api_client.post(f"/items/{ITEM_ID}/count", json={"counted": counted}, headers=user["headers"])

    assert response.status_code == 422
    mocked.assert_not_called()


def test_count_item_endpoint_accepts_a_count_of_zero(api_client, user):
    with _mock("count_item", return_value=_item(stock=0)) as mocked:
        response = api_client.post(f"/items/{ITEM_ID}/count", json={"counted": 0}, headers=user["headers"])

    assert response.status_code == 200
    mocked.assert_called_once_with(user["id"], ITEM_ID, 0)


# --- GET /items/{id}/movements ---


def test_list_movements_endpoint_serializes_the_history(api_client, user):
    history = [_movement(id=2, type="exit", quantity=-1, note="usado"), _movement()]
    with _mock("list_movements", return_value=history) as mocked:
        response = api_client.get(f"/items/{ITEM_ID}/movements", headers=user["headers"])

    assert response.status_code == 200
    assert [entry["type"] for entry in response.json()] == ["exit", "initial_adjustment"]
    mocked.assert_called_once_with(user["id"], ITEM_ID)


def test_list_movements_endpoint_rejects_a_non_integer_id(api_client, user):
    with _mock("list_movements") as mocked:
        response = api_client.get("/items/abc/movements", headers=user["headers"])

    assert response.status_code == 422
    mocked.assert_not_called()


def test_list_movements_endpoint_keeps_a_missing_note_as_an_explicit_null(api_client, user):
    with _mock("list_movements", return_value=[_movement(note=None)]):
        response = api_client.get(f"/items/{ITEM_ID}/movements", headers=user["headers"])

    entry = response.json()[0]
    assert "note" in entry
    assert entry["note"] is None


# --- GET /items/by-code/{code} ---


def test_get_item_by_code_endpoint_passes_the_raw_code(api_client, user):
    with _mock("get_item_by_code", return_value=_item()) as mocked:
        response = api_client.get("/items/by-code/012345678905", headers=user["headers"])

    assert response.status_code == 200
    mocked.assert_called_once_with(user["id"], "012345678905")


def test_get_item_by_code_endpoint_rejects_a_code_over_the_length_limit(api_client, user):
    with _mock("get_item_by_code") as mocked:
        response = api_client.get(f"/items/by-code/{'1' * 65}", headers=user["headers"])

    assert response.status_code == 422
    mocked.assert_not_called()


def test_get_item_by_code_endpoint_accepts_a_code_at_the_length_limit(api_client, user):
    raw_code = " " * 51 + VALID_CODE
    with _mock("get_item_by_code", return_value=_item()) as mocked:
        response = api_client.get(f"/items/by-code/{raw_code}", headers=user["headers"])

    assert response.status_code == 200
    assert len(raw_code) == 64
    mocked.assert_called_once_with(user["id"], raw_code)


# --- POST /items/{id}/codes ---


def test_link_code_endpoint_passes_the_raw_code(api_client, user):
    with _mock("link_code", return_value=_item()) as mocked:
        response = api_client.post(f"/items/{ITEM_ID}/codes", json={"code": VALID_CODE}, headers=user["headers"])

    assert response.status_code == 200
    mocked.assert_called_once_with(user["id"], ITEM_ID, VALID_CODE)


@pytest.mark.parametrize("body", [{}, {"code": "1" * 65}])
def test_link_code_endpoint_rejects_invalid_bodies(api_client, user, body):
    with _mock("link_code") as mocked:
        response = api_client.post(f"/items/{ITEM_ID}/codes", json=body, headers=user["headers"])

    assert response.status_code == 422
    mocked.assert_not_called()


def test_link_code_endpoint_passes_a_conflict_through(api_client, user):
    conflict = HTTPException(status_code=409, detail="Code already linked to another item")
    with _mock("link_code", side_effect=conflict):
        response = api_client.post(f"/items/{ITEM_ID}/codes", json={"code": VALID_CODE}, headers=user["headers"])

    assert response.status_code == 409


def test_link_code_endpoint_accepts_a_code_at_the_length_limit(api_client, user):
    raw_code = " " * 51 + VALID_CODE
    with _mock("link_code", return_value=_item()) as mocked:
        response = api_client.post(f"/items/{ITEM_ID}/codes", json={"code": raw_code}, headers=user["headers"])

    assert response.status_code == 200
    assert mocked.call_args.args[2] == raw_code


# --- DELETE /items/{id}/codes/{code} ---


def test_unlink_code_endpoint_returns_204_with_an_empty_body(api_client, user):
    with _mock("unlink_code", return_value=None) as mocked:
        response = api_client.delete(f"/items/{ITEM_ID}/codes/{VALID_CODE}", headers=user["headers"])

    assert response.status_code == 204
    assert response.content == b""
    mocked.assert_called_once_with(user["id"], ITEM_ID, VALID_CODE)


def test_unlink_code_endpoint_rejects_a_code_over_the_length_limit(api_client, user):
    with _mock("unlink_code") as mocked:
        response = api_client.delete(f"/items/{ITEM_ID}/codes/{'1' * 65}", headers=user["headers"])

    assert response.status_code == 422
    mocked.assert_not_called()
