import pytest


@pytest.fixture()
def create_user_two_pending_contact(create_user):
    user_one = create_user("1111111111", name="Tenant One")
    user_two = create_user("2222222222", name="Tenant Two")
    user_one_id = user_one["id"]
    user_two_id = user_two["id"]

    from backend.database.connect import connect

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO whatsapp_instances (user_id, instance_name)
                VALUES (%s, %s)
                RETURNING id;
                """,
                (user_two_id, "2_whatsapp"),
            )
            instance_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO wa_pending_contacts (instance_id, remote_jid, name, last_message, last_message_at)
                VALUES (%s, %s, %s, %s, NOW())
                RETURNING id;
                """,
                (instance_id, "999@s.whatsapp.net", "Tenant2 Contact", "Only for tenant 2"),
            )
            pending_id = cur.fetchone()[0]

    return {
        "user_ids": (user_one_id, user_two_id),
        "instance_id": instance_id,
        "pending_id": pending_id,
    }


def test_tenant_one_cannot_access_or_modify_tenant_two_pending_contacts(api_client, create_user_two_pending_contact, auth_headers):
    seeded = create_user_two_pending_contact
    user_one_id, user_two_id = seeded["user_ids"]
    pending_id = seeded["pending_id"]

    assert user_one_id == 1
    assert user_two_id == 2

    headers = auth_headers("1111111111", name="Tenant One")

    # GET /whatsapp/pending should not list tenant 2's pending contact (tenant 1 has no instance at all).
    list_response = api_client.get("/whatsapp/pending", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json() == []

    # PATCH /whatsapp/pending/{id}/status should not update tenant 2's pending contact.
    status_response = api_client.patch(
        f"/whatsapp/pending/{pending_id}/status",
        json={"status": "converted"},
        headers=headers,
    )
    assert status_response.status_code == 404

    # DELETE /whatsapp/pending/{id} should not delete tenant 2's pending contact.
    delete_response = api_client.delete(f"/whatsapp/pending/{pending_id}", headers=headers)
    assert delete_response.status_code == 404

    # PATCH /whatsapp/notifications should not be able to toggle tenant 2's instance
    # (tenant 1 has no instance of their own, so this must 404, not touch tenant 2's row).
    notifications_response = api_client.patch(
        "/whatsapp/notifications",
        json={"enabled": False},
        headers=headers,
    )
    assert notifications_response.status_code == 404

    from backend.database.connect import connect
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM wa_pending_contacts WHERE id = %s", (pending_id,))
            assert cur.fetchone()[0] == "pending"

            cur.execute("SELECT notifications_enabled FROM whatsapp_instances WHERE id = %s", (seeded["instance_id"],))
            assert cur.fetchone()[0] is True
