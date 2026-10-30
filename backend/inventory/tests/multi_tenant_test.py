import pytest

import backend.inventory.service as service


@pytest.fixture()
def tenant_b_state(tenants):
    """
    Reads tenant B's item and history straight from the service, so each test
    can assert that A's request left B exactly as it was.
    """

    def _read():
        b = tenants["b"]
        return service.get_item(b["user_id"], b["item_id"]), service.list_movements(b["user_id"], b["item_id"])

    return _read


def test_tenant_a_never_sees_tenant_b_items_in_the_list(api_client, tenants, tenant_headers):
    response = api_client.get("/items/", headers=tenant_headers["a"])

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [tenants["a"]["item_id"]]


def test_tenant_a_cannot_read_tenant_b_item(api_client, tenants, tenant_headers):
    response = api_client.get(f"/items/{tenants['b']['item_id']}", headers=tenant_headers["a"])

    assert response.status_code == 404


def test_tenant_a_cannot_edit_tenant_b_item(api_client, tenants, tenant_headers, tenant_b_state):
    before = tenant_b_state()

    response = api_client.patch(
        f"/items/{tenants['b']['item_id']}", json={"name": "Hacked"}, headers=tenant_headers["a"]
    )

    assert response.status_code == 404
    assert tenant_b_state() == before


def test_tenant_a_cannot_deactivate_tenant_b_item(api_client, tenants, tenant_headers, tenant_b_state):
    before = tenant_b_state()

    response = api_client.delete(f"/items/{tenants['b']['item_id']}", headers=tenant_headers["a"])

    assert response.status_code == 404
    assert tenant_b_state() == before


def test_tenant_a_cannot_record_movements_on_tenant_b_item(api_client, tenants, tenant_headers, tenant_b_state):
    before = tenant_b_state()

    response = api_client.post(
        f"/items/{tenants['b']['item_id']}/movements",
        json={"type": "exit", "quantity": 1},
        headers=tenant_headers["a"],
    )

    assert response.status_code == 404
    assert tenant_b_state() == before


def test_tenant_a_cannot_count_tenant_b_item(api_client, tenants, tenant_headers, tenant_b_state):
    before = tenant_b_state()

    response = api_client.post(
        f"/items/{tenants['b']['item_id']}/count", json={"counted": 0}, headers=tenant_headers["a"]
    )

    assert response.status_code == 404
    assert tenant_b_state() == before


def test_tenant_a_cannot_read_tenant_b_history(api_client, tenants, tenant_headers):
    response = api_client.get(f"/items/{tenants['b']['item_id']}/movements", headers=tenant_headers["a"])

    assert response.status_code == 404


def test_tenant_a_cannot_look_up_a_code_only_tenant_b_has(api_client, tenants, tenant_headers):
    response = api_client.get(f"/items/by-code/{tenants['b']['code']}", headers=tenant_headers["a"])

    assert response.status_code == 404


def test_tenant_a_cannot_link_a_code_to_tenant_b_item(api_client, tenants, tenant_headers, tenant_b_state):
    before = tenant_b_state()

    response = api_client.post(
        f"/items/{tenants['b']['item_id']}/codes", json={"code": "9780201379624"}, headers=tenant_headers["a"]
    )

    assert response.status_code == 404
    assert tenant_b_state() == before


def test_tenant_a_cannot_unlink_tenant_b_code(api_client, tenants, tenant_headers, tenant_b_state):
    before = tenant_b_state()

    response = api_client.delete(
        f"/items/{tenants['b']['item_id']}/codes/{tenants['b']['code']}", headers=tenant_headers["a"]
    )

    assert response.status_code == 404
    assert tenant_b_state() == before


def test_tenant_a_can_link_a_code_text_tenant_b_already_holds(api_client, tenants, tenant_headers, tenant_b_state):
    before = tenant_b_state()

    response = api_client.post(
        f"/items/{tenants['a']['item_id']}/codes", json={"code": tenants["b"]["code"]}, headers=tenant_headers["a"]
    )

    assert response.status_code == 200
    assert tenants["b"]["code"] in response.json()["codes"]
    assert tenant_b_state() == before
