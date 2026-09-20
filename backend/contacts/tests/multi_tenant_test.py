import pytest

from backend.shared.connect import connect


@pytest.fixture()
def create_user_two_contact(create_user):
    user_one = create_user("1111111111", name="Tenant One")
    user_two = create_user("2222222222", name="Tenant Two")

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO whatsapp_instances (user_id, instance_name, status)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (user_two["id"], "2_whatsapp", "open"),
            )
            instance_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO contacts (instance_id, remote_jid, name)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (instance_id, "999@s.whatsapp.net", "Tenant2 Contact"),
            )
            contact_id = cur.fetchone()[0]

    return {
        "user_ids": (user_one["id"], user_two["id"]),
        "instance_id": instance_id,
        "contact_id": contact_id,
    }


def test_tenant_one_cannot_access_or_modify_tenant_two_contacts(api_client, create_user_two_contact, auth_headers):
    seeded = create_user_two_contact
    contact_id = seeded["contact_id"]

    headers = auth_headers("1111111111", name="Tenant One")

    # GET /contacts/ should not see tenant two's contact (tenant one has no instance at all).
    list_response = api_client.get("/contacts/", headers=headers)
    assert list_response.status_code == 404

    # PATCH .../name should not rename tenant two's contact.
    name_response = api_client.patch(f"/contacts/{contact_id}/name", json={"name": "Hacked"}, headers=headers)
    assert name_response.status_code == 404

    # PATCH .../opted_out should not blacklist tenant two's contact.
    opted_out_response = api_client.patch(f"/contacts/{contact_id}/opted_out", json={"opted_out": True}, headers=headers)
    assert opted_out_response.status_code == 404

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, opted_out FROM contacts WHERE id = %s", (contact_id,))
            assert cur.fetchone() == ("Tenant2 Contact", False)
