from unittest.mock import AsyncMock, patch

from backend.database.connect import connect


def _create_instance(user_id, instance_name="1_whatsapp", status="open"):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO whatsapp_instances (user_id, instance_name, status)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (user_id, instance_name, status),
            )
            return cur.fetchone()[0]


def _create_contact(instance_id, remote_jid="111@s.whatsapp.net", name="Jane", opted_out=False):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO contacts (instance_id, remote_jid, name, opted_out)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (instance_id, remote_jid, name, opted_out),
            )
            return cur.fetchone()[0]


def _contact_row(contact_id):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, opted_out FROM contacts WHERE id = %s", (contact_id,))
            return cur.fetchone()


def _mock_evolution(contacts_response, chats_response):
    """
    Mocks only the Evolution HTTP boundary (rep.find_contacts/find_chats), same
    "mock the external call, keep everything else real" style as whatsapp/tests.
    """
    return (
        patch("backend.contacts.service.rep.find_contacts", new=AsyncMock(return_value=contacts_response)),
        patch("backend.contacts.service.rep.find_chats", new=AsyncMock(return_value=chats_response)),
    )


# --- POST /contacts/import ---

def test_import_contacts_endpoint_reconciles_and_upserts_contacts(create_user, auth_headers, api_client):
    user = create_user("0999999999")
    headers = auth_headers("0999999999")
    _create_instance(user["id"], status="open")

    contacts_response = [
        {"remoteJid": "111@s.whatsapp.net", "pushName": "Alice", "type": "contact"},
        {"remoteJid": "not-a-contact@g.us", "pushName": "Group", "type": "group"},
    ]
    chats_response = [
        {
            "remoteJid": "222@lid",
            "pushName": "Bob",
            "lastMessage": {"key": {"remoteJidAlt": "222@s.whatsapp.net"}},
        },
    ]

    mock_contacts, mock_chats = _mock_evolution(contacts_response, chats_response)
    with mock_contacts, mock_chats:
        response = api_client.post("/contacts/import", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"imported": 2}

    list_response = api_client.get("/contacts/", headers=headers)
    names = {c["remote_jid"]: c["name"] for c in list_response.json()}
    assert names == {"111@s.whatsapp.net": "Alice", "222@s.whatsapp.net": "Bob"}


def test_import_contacts_endpoint_rejects_missing_or_disconnected_instance(create_user, auth_headers, api_client):
    user = create_user("0999999999")
    headers = auth_headers("0999999999")

    no_instance_response = api_client.post("/contacts/import", headers=headers)
    assert no_instance_response.status_code == 404
    assert no_instance_response.json()["detail"] == "WhatsApp instance not found"

    _create_instance(user["id"], status="connecting")

    not_connected_response = api_client.post("/contacts/import", headers=headers)
    assert not_connected_response.status_code == 409
    assert not_connected_response.json()["detail"] == "WhatsApp instance not connected"


def test_import_contacts_endpoint_reimport_does_not_blank_an_existing_name(create_user, auth_headers, api_client):
    """
    Edge case: the pushName bug can return an empty name for a contact that
    already has a real one. A second import must not let that blank clobber
    the existing name (the upsert's WHERE EXCLUDED.name != '' guard).
    """
    user = create_user("0999999999")
    headers = auth_headers("0999999999")
    _create_instance(user["id"], status="open")

    mock_contacts, mock_chats = _mock_evolution(
        [{"remoteJid": "111@s.whatsapp.net", "pushName": "Alice", "type": "contact"}], []
    )
    with mock_contacts, mock_chats:
        api_client.post("/contacts/import", headers=headers)

    mock_contacts, mock_chats = _mock_evolution(
        [{"remoteJid": "111@s.whatsapp.net", "pushName": "", "type": "contact"}], []
    )
    with mock_contacts, mock_chats:
        api_client.post("/contacts/import", headers=headers)

    list_response = api_client.get("/contacts/", headers=headers)
    assert list_response.json()[0]["name"] == "Alice"


# --- GET /contacts/ ---

def test_list_contacts_endpoint_returns_all_contacts_regardless_of_opted_out(create_user, auth_headers, api_client):
    """
    The active/blacklist split is a frontend-only concern (the Pinia store's
    activeContacts/blacklistedContacts getters over one fetched list) — this
    endpoint itself returns every contact for the instance, opted out or not.
    """
    user = create_user("0999999999")
    headers = auth_headers("0999999999")
    instance_id = _create_instance(user["id"])

    _create_contact(instance_id, remote_jid="111@s.whatsapp.net", name="Alice", opted_out=False)
    _create_contact(instance_id, remote_jid="333@s.whatsapp.net", name="Blacklisted", opted_out=True)

    response = api_client.get("/contacts/", headers=headers)
    assert response.status_code == 200
    jids = {c["remote_jid"] for c in response.json()}
    assert jids == {"111@s.whatsapp.net", "333@s.whatsapp.net"}


def test_list_contacts_endpoint_rejects_missing_instance(create_user, auth_headers, api_client):
    create_user("0999999999")
    headers = auth_headers("0999999999")

    response = api_client.get("/contacts/", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "WhatsApp instance not found"


def test_list_contacts_endpoint_preserves_null_name(create_user, auth_headers, api_client):
    """
    Edge case: a contact with no name comes back as null, never a placeholder
    string. "Sin Nombre" is a frontend-only, read-layer concern.
    """
    user = create_user("0999999999")
    headers = auth_headers("0999999999")
    instance_id = _create_instance(user["id"])
    _create_contact(instance_id, remote_jid="111@s.whatsapp.net", name=None)

    response = api_client.get("/contacts/", headers=headers)
    assert response.json()[0]["name"] is None


# --- PATCH /contacts/{id}/name ---

def test_update_contact_name_endpoint_renames_and_rejects_missing(create_user, auth_headers, api_client):
    user = create_user("0999999999")
    headers = auth_headers("0999999999")
    instance_id = _create_instance(user["id"])
    contact_id = _create_contact(instance_id, name="Old Name")

    response = api_client.patch(f"/contacts/{contact_id}/name", json={"name": "New Name"}, headers=headers)
    assert response.status_code == 200
    assert _contact_row(contact_id)[0] == "New Name"

    not_found_response = api_client.patch("/contacts/999999/name", json={"name": "X"}, headers=headers)
    assert not_found_response.status_code == 404
    assert not_found_response.json()["detail"] == "Contact not found"

    invalid_response = api_client.patch(f"/contacts/{contact_id}/name", json={}, headers=headers)
    assert invalid_response.status_code == 422


def test_update_contact_name_endpoint_allows_empty_string(create_user, auth_headers, api_client):
    """
    Edge case, pinning down current behavior rather than changing it: the
    manual rename endpoint has no non-empty guard (that guard only exists in
    the reconciliation upsert's ON CONFLICT clause), so an empty string is
    accepted and persisted as-is.
    """
    user = create_user("0999999999")
    headers = auth_headers("0999999999")
    instance_id = _create_instance(user["id"])
    contact_id = _create_contact(instance_id, name="Old Name")

    response = api_client.patch(f"/contacts/{contact_id}/name", json={"name": ""}, headers=headers)
    assert response.status_code == 200
    assert _contact_row(contact_id)[0] == ""


# --- PATCH /contacts/{id}/opted_out ---

def test_update_contact_opted_out_endpoint_toggles_and_rejects_missing(create_user, auth_headers, api_client):
    user = create_user("0999999999")
    headers = auth_headers("0999999999")
    instance_id = _create_instance(user["id"])
    contact_id = _create_contact(instance_id, opted_out=False)

    response = api_client.patch(f"/contacts/{contact_id}/opted_out", json={"opted_out": True}, headers=headers)
    assert response.status_code == 200
    assert _contact_row(contact_id)[1] is True

    not_found_response = api_client.patch("/contacts/999999/opted_out", json={"opted_out": True}, headers=headers)
    assert not_found_response.status_code == 404
    assert not_found_response.json()["detail"] == "Contact not found"

    invalid_response = api_client.patch(f"/contacts/{contact_id}/opted_out", json={}, headers=headers)
    assert invalid_response.status_code == 422


def test_update_contact_opted_out_endpoint_does_not_touch_name(create_user, auth_headers, api_client):
    user = create_user("0999999999")
    headers = auth_headers("0999999999")
    instance_id = _create_instance(user["id"])
    contact_id = _create_contact(instance_id, name="Alice", opted_out=False)

    api_client.patch(f"/contacts/{contact_id}/opted_out", json={"opted_out": True}, headers=headers)

    assert _contact_row(contact_id) == ("Alice", True)
