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
