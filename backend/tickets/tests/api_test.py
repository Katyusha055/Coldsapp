import pytest


def test_post_tickets_endpoint_creates_ticket_validates_db_and_rejects_invalid_payload(
    api_client, create_user
):
    from backend.database.connect import connect

    user_id = create_user
    assert user_id == 1

    create_client_response = api_client.post(
        "/clients/",
        json={"name": "Test Client", "phone": "5550000001", "description": "For ticket tests"},
    )
    assert create_client_response.status_code in (200, 201)
    client_id = create_client_response.json()["id"]

    valid_payload = {
        "client_id": client_id,
        "title": "Screen is broken",
        "description": "The display goes black after 10 seconds",
    }
    response = api_client.post("/tickets/", json=valid_payload)

    assert response.status_code in (200, 201)
    body = response.json()
    assert body["id"] > 0
    assert body["client_id"] == client_id
    assert body["title"] == valid_payload["title"]
    assert body["description"] == valid_payload["description"]
    assert body["status"] == "pending"
    assert "received_at" in body
    assert "created_at" in body
    assert "updated_at" in body
    assert "user_id" not in body

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, client_id, title, description, status FROM tickets WHERE id = %s",
                (body["id"],),
            )
            row = cur.fetchone()

    assert row is not None
    assert row[1] == user_id
    assert row[2] == client_id
    assert row[3] == valid_payload["title"]
    assert row[4] == valid_payload["description"]
    assert row[5] == "pending"

    not_found_payload = {"client_id": 999, "title": "Orphan ticket", "description": None}
    not_found_response = api_client.post("/tickets/", json=not_found_payload)
    assert not_found_response.status_code == 404
    assert not_found_response.json()["detail"] == "Client not found"

    invalid_payload = {"description": "Missing required client_id and title"}
    invalid_response = api_client.post("/tickets/", json=invalid_payload)
    assert invalid_response.status_code == 422
    assert "detail" in invalid_response.json()


def test_get_tickets_endpoint_returns_list(api_client, create_user):
    user_id = create_user
    assert user_id == 1

    create_client_response = api_client.post(
        "/clients/",
        json={"name": "List Test Client", "phone": "5550000002", "description": None},
    )
    assert create_client_response.status_code in (200, 201)
    client_id = create_client_response.json()["id"]

    ticket_one = api_client.post("/tickets/", json={"client_id": client_id, "title": "Ticket One"})
    ticket_two = api_client.post("/tickets/", json={"client_id": client_id, "title": "Ticket Two"})

    assert ticket_one.status_code in (200, 201)
    assert ticket_two.status_code in (200, 201)

    response = api_client.get("/tickets/")
    assert response.status_code == 200

    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 2

    ids = [t["id"] for t in body]
    assert ticket_one.json()["id"] in ids
    assert ticket_two.json()["id"] in ids


def test_get_ticket_by_id_endpoint_retrieves_ticket_and_rejects_invalid(api_client, create_user):
    user_id = create_user
    assert user_id == 1

    create_client_response = api_client.post(
        "/clients/",
        json={"name": "By-ID Client", "phone": "5550000003", "description": None},
    )
    assert create_client_response.status_code in (200, 201)
    client_id = create_client_response.json()["id"]

    create_ticket_response = api_client.post(
        "/tickets/",
        json={"client_id": client_id, "title": "Get by ID ticket", "description": "Some details"},
    )
    assert create_ticket_response.status_code in (200, 201)
    ticket_id = create_ticket_response.json()["id"]

    response = api_client.get(f"/tickets/{ticket_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == ticket_id
    assert body["client_id"] == client_id
    assert body["title"] == "Get by ID ticket"
    assert body["description"] == "Some details"
    assert body["status"] == "pending"

    not_found_response = api_client.get("/tickets/999999")
    assert not_found_response.status_code == 404
    assert not_found_response.json()["detail"] == "Ticket not found"

    invalid_response = api_client.get("/tickets/not-an-int")
    assert invalid_response.status_code == 422
    assert "detail" in invalid_response.json()


def test_delete_ticket_endpoint_deletes_ticket_and_returns_404_when_missing(api_client, create_user):
    from backend.database.connect import connect

    user_id = create_user
    assert user_id == 1

    create_client_response = api_client.post(
        "/clients/",
        json={"name": "Delete Client", "phone": "5550000004", "description": None},
    )
    assert create_client_response.status_code in (200, 201)
    client_id = create_client_response.json()["id"]

    create_ticket_response = api_client.post(
        "/tickets/",
        json={"client_id": client_id, "title": "Ticket to delete", "description": None},
    )
    assert create_ticket_response.status_code in (200, 201)
    ticket_id = create_ticket_response.json()["id"]

    delete_response = api_client.delete(f"/tickets/{ticket_id}")
    assert delete_response.status_code == 204

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM tickets WHERE id = %s AND deleted_at IS NULL",
                (ticket_id,),
            )
            row = cur.fetchone()
    assert row is None

    second_delete_response = api_client.delete(f"/tickets/{ticket_id}")
    assert second_delete_response.status_code == 404
    assert second_delete_response.json()["detail"] == "Ticket not found"

    invalid_delete_response = api_client.delete("/tickets/not-an-int")
    assert invalid_delete_response.status_code == 422
    assert "detail" in invalid_delete_response.json()


def test_update_ticket_status_endpoint_transitions_status_and_rejects_invalid(api_client, create_user):
    user_id = create_user
    assert user_id == 1

    create_client_response = api_client.post(
        "/clients/",
        json={"name": "Status Client", "phone": "5550000005", "description": None},
    )
    assert create_client_response.status_code in (200, 201)
    client_id = create_client_response.json()["id"]

    create_ticket_response = api_client.post(
        "/tickets/",
        json={"client_id": client_id, "title": "Status transition ticket"},
    )
    assert create_ticket_response.status_code in (200, 201)
    ticket_id = create_ticket_response.json()["id"]
    assert create_ticket_response.json()["status"] == "pending"

    valid_transition_response = api_client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "in_progress"},
    )
    assert valid_transition_response.status_code == 200
    assert valid_transition_response.json()["status"] == "in_progress"

    invalid_transition_response = api_client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "pending"},
    )
    assert invalid_transition_response.status_code == 400
    assert "Cannot transition" in invalid_transition_response.json()["detail"]

    not_found_response = api_client.patch(
        "/tickets/999999/status",
        json={"status": "in_progress"},
    )
    assert not_found_response.status_code == 404
    assert not_found_response.json()["detail"] == "Ticket not found"

    invalid_status_response = api_client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "flying"},
    )
    assert invalid_status_response.status_code == 422
    assert "detail" in invalid_status_response.json()


def test_update_ticket_endpoint_updates_fields_and_rejects_invalid(api_client, create_user):
    user_id = create_user
    assert user_id == 1

    create_client_response = api_client.post(
        "/clients/",
        json={"name": "Update Client", "phone": "5550000006", "description": None},
    )
    assert create_client_response.status_code in (200, 201)
    client_id = create_client_response.json()["id"]

    create_ticket_response = api_client.post(
        "/tickets/",
        json={"client_id": client_id, "title": "Original title", "description": "Original description"},
    )
    assert create_ticket_response.status_code in (200, 201)
    ticket_id = create_ticket_response.json()["id"]

    patch_response = api_client.patch(
        f"/tickets/{ticket_id}",
        json={"title": "Updated title", "description": "Updated description"},
    )
    assert patch_response.status_code == 200
    patched_body = patch_response.json()
    assert patched_body["id"] == ticket_id
    assert patched_body["title"] == "Updated title"
    assert patched_body["description"] == "Updated description"

    no_fields_response = api_client.patch(f"/tickets/{ticket_id}", json={})
    assert no_fields_response.status_code == 400
    assert no_fields_response.json()["detail"] == "No fields to update"

    not_found_response = api_client.patch(
        "/tickets/999999",
        json={"title": "Wont work"},
    )
    assert not_found_response.status_code == 404
    assert not_found_response.json()["detail"] == "Ticket not found"

    invalid_type_response = api_client.patch(
        f"/tickets/{ticket_id}",
        json={"title": ["not", "a", "string"]},
    )
    assert invalid_type_response.status_code == 422
    assert "detail" in invalid_type_response.json()
