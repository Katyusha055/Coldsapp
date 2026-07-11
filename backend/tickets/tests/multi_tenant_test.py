import pytest


@pytest.fixture()
def create_user_two_ticket(create_user):
    user_one = create_user("1111111111", name="Tenant One")
    user_two = create_user("2222222222", name="Tenant Two")
    user_one_id = user_one['id']
    user_two_id = user_two['id']

    from backend.database.connect import connect

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO clients (user_id, name, phone, description)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (user_two_id, 'Tenant2 Client', '7777000001', 'Belongs to tenant 2'),
            )
            client_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO tickets (user_id, client_id, title, description)
                VALUES (%s, %s, %s, %s)
                RETURNING id, user_id, client_id, title, status;
                """,
                (user_two_id, client_id, 'Tenant 2 Ticket', 'Only for tenant 2'),
            )
            ticket = cur.fetchone()

    return {
        'user_ids': (user_one_id, user_two_id),
        'ticket': ticket,
    }


def test_tenant_one_cannot_access_or_modify_tenant_two_tickets(api_client, create_user_two_ticket, auth_headers):
    seeded = create_user_two_ticket
    user_one_id, user_two_id = seeded['user_ids']
    ticket = seeded['ticket']

    assert user_one_id == 1
    assert user_two_id == 2

    headers = auth_headers("1111111111", name="Tenant One")

    ticket_id = ticket[0]

    # GET /tickets/ should not include tenant 2 tickets when authenticated as tenant 1.
    list_response = api_client.get('/tickets/', headers=headers)
    assert list_response.status_code == 200
    assert list_response.json() == []

    # GET /tickets/{id} should not retrieve tenant 2 ticket.
    get_response = api_client.get(f'/tickets/{ticket_id}', headers=headers)
    assert get_response.status_code == 404

    # DELETE /tickets/{id} should not delete tenant 2 ticket.
    delete_response = api_client.delete(f'/tickets/{ticket_id}', headers=headers)
    assert delete_response.status_code == 404

    # PATCH /tickets/{id} should not update tenant 2 ticket.
    patch_response = api_client.patch(f'/tickets/{ticket_id}', json={'title': 'Illegal Update'}, headers=headers)
    assert patch_response.status_code == 404

    # PATCH /tickets/{id}/status should not update tenant 2 ticket status.
    status_response = api_client.patch(
        f'/tickets/{ticket_id}/status',
        json={'status': 'in_progress'},
        headers=headers,
    )
    assert status_response.status_code == 404

    # POST /tickets/ should not let tenant 1 create a ticket against tenant 2's client.
    tenant_two_client_id = ticket[2]
    create_response = api_client.post(
        '/tickets/',
        json={'client_id': tenant_two_client_id, 'title': 'Illegal cross-tenant ticket'},
        headers=headers,
    )
    assert create_response.status_code == 404
    assert create_response.json()['detail'] == 'Client not found'
