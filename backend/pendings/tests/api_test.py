import pytest


def _create_instance(user_id, instance_name="1_whatsapp", notifications_enabled=True):
    from backend.database.connect import connect

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO whatsapp_instances (user_id, instance_name, notifications_enabled)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (user_id, instance_name, notifications_enabled),
            )
            return cur.fetchone()[0]


def _create_pending(instance_id, remote_jid="123@s.whatsapp.net", name="Jane", last_message="Hola", status="pending"):
    from backend.database.connect import connect

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO wa_pending_contacts (instance_id, remote_jid, name, last_message, last_message_at, status)
                VALUES (%s, %s, %s, %s, NOW(), %s)
                RETURNING id;
                """,
                (instance_id, remote_jid, name, last_message, status),
            )
            return cur.fetchone()[0]


# --- PATCH /whatsapp/notifications ---

def test_update_notifications_endpoint_toggles_flag_and_rejects_missing_instance(create_user, auth_headers, api_client):
    user = create_user("0999999999")
    headers = auth_headers("0999999999")

    not_found_response = api_client.patch("/whatsapp/notifications", json={"enabled": False}, headers=headers)
    assert not_found_response.status_code == 404
    assert not_found_response.json()["detail"] == "WhatsApp instance not found"

    _create_instance(user["id"], notifications_enabled=True)

    disable_response = api_client.patch("/whatsapp/notifications", json={"enabled": False}, headers=headers)
    assert disable_response.status_code == 200
    assert disable_response.json()["notifications_enabled"] is False

    enable_response = api_client.patch("/whatsapp/notifications", json={"enabled": True}, headers=headers)
    assert enable_response.status_code == 200
    assert enable_response.json()["notifications_enabled"] is True

    invalid_response = api_client.patch("/whatsapp/notifications", json={"enabled": "not-a-bool"}, headers=headers)
    assert invalid_response.status_code == 422


# --- GET /whatsapp/pending ---

def test_get_pending_contacts_endpoint_returns_empty_then_populated_list(create_user, auth_headers, api_client):
    user = create_user("0999999999")
    headers = auth_headers("0999999999")

    empty_response = api_client.get("/whatsapp/pending", headers=headers)
    assert empty_response.status_code == 200
    assert empty_response.json() == []

    instance_id = _create_instance(user["id"])
    _create_pending(instance_id, remote_jid="111@s.whatsapp.net", name="Contact One")
    _create_pending(instance_id, remote_jid="222@s.whatsapp.net", name="Contact Two")
    _create_pending(instance_id, remote_jid="333@s.whatsapp.net", name="Already Converted", status="converted")

    response = api_client.get("/whatsapp/pending", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert len(body) == 2
    names = {c["name"] for c in body}
    assert names == {"Contact One", "Contact Two"}


# --- PATCH /whatsapp/pending/{id}/status ---

def test_update_pending_status_endpoint_updates_status_and_rejects_invalid(create_user, auth_headers, api_client):
    user = create_user("0999999999")
    headers = auth_headers("0999999999")

    instance_id = _create_instance(user["id"])
    pending_id = _create_pending(instance_id)

    response = api_client.patch(
        f"/whatsapp/pending/{pending_id}/status",
        json={"status": "converted"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "converted"

    not_found_response = api_client.patch(
        "/whatsapp/pending/999999/status",
        json={"status": "converted"},
        headers=headers,
    )
    assert not_found_response.status_code == 404
    assert not_found_response.json()["detail"] == "Pending contact not found"

    invalid_status_response = api_client.patch(
        f"/whatsapp/pending/{pending_id}/status",
        json={"status": "does anyone read this?"},
        headers=headers,
    )
    assert invalid_status_response.status_code == 422


# --- DELETE /whatsapp/pending/{id} ---

def test_delete_pending_endpoint_deletes_and_returns_404_when_missing(create_user, auth_headers, api_client):
    user = create_user("0999999999")
    headers = auth_headers("0999999999")

    instance_id = _create_instance(user["id"])
    pending_id = _create_pending(instance_id)

    delete_response = api_client.delete(f"/whatsapp/pending/{pending_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True, "id": pending_id}

    second_delete_response = api_client.delete(f"/whatsapp/pending/{pending_id}", headers=headers)
    assert second_delete_response.status_code == 404
    assert second_delete_response.json()["detail"] == "Pending contact not found"
