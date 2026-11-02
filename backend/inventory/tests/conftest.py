import pytest

import backend.inventory.service as service

TENANT_A_PHONE = "1111111111"
TENANT_B_PHONE = "2222222222"
TENANT_A_CODE = "4006381333931"
TENANT_B_CODE = "5901234123457"


@pytest.fixture()
def tenants(create_user):
    """
    Users A and B, each with one item that has a code and a movement (the
    quick add's initial_adjustment of 5).

    Output: {"a": {...}, "b": {...}}, each {"user_id", "item_id", "code", "phone"}
    """
    seeded = {}
    for key, phone, name, code in (
        ("a", TENANT_A_PHONE, "Tenant A", TENANT_A_CODE),
        ("b", TENANT_B_PHONE, "Tenant B", TENANT_B_CODE),
    ):
        user = create_user(phone, name=name)
        item = service.create_item(
            user["id"],
            {"name": f"Disco {key.upper()}", "quantity": 5, "low_stock_threshold": None, "code": code},
        )
        seeded[key] = {"user_id": user["id"], "item_id": item["id"], "code": code, "phone": phone}
    return seeded


@pytest.fixture()
def tenant_headers(tenants, api_client):
    """
    Bearer headers for the already-registered users A and B.

    Output: {"a": headers, "b": headers}
    """
    headers = {}
    for key in ("a", "b"):
        token_response = api_client.post(
            "/auth/token",
            data={"username": tenants[key]["phone"], "password": "testpassword"},
        )
        headers[key] = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
    return headers
