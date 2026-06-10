import pytest

from backend.conftest import load_test_env, api_client, clean_db


@pytest.fixture()
def create_user_two_clients(create_user):
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
                VALUES
                    (%s, %s, %s, %s),
                    (%s, %s, %s, %s)
                RETURNING id, user_id, name, phone, description;
                """,
                (
                    user_two_id,
                    'Tenant2 Client One',
                    '7777000001',
                    'Belongs only to tenant 2',
                    user_two_id,
                    'Tenant2 Client Two',
                    '7777000002',
                    'Also belongs only to tenant 2',
                ),
            )
            clients = cur.fetchall()

    return {
        'user_ids': (user_one_id, user_two_id),
        'clients': clients,
    }


def test_tenant_one_cannot_access_or_modify_tenant_two_clients(api_client, create_user_two_clients, auth_headers):
    seeded = create_user_two_clients
    user_one_id, user_two_id = seeded['user_ids']
    client_one, client_two = seeded['clients']

    assert user_one_id == 1
    assert user_two_id == 2

    headers = auth_headers("1111111111", name="Tenant One")

    tenant_two_client_one_id = client_one[0]
    tenant_two_client_one_phone = client_one[3]
    tenant_two_client_two_id = client_two[0]

    # GET /clients/ should not include tenant 2 clients when authenticated as tenant 1.
    list_response = api_client.get('/clients/', headers=headers)
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert isinstance(list_body, list)
    assert all(client['id'] not in (tenant_two_client_one_id, tenant_two_client_two_id) for client in list_body)

    # GET /clients/{id} should not retrieve tenant 2 client.
    get_by_id_response = api_client.get(f'/clients/{tenant_two_client_one_id}', headers=headers)
    assert get_by_id_response.status_code == 404 or get_by_id_response.json() == {}

    # GET /clients/by-phone/{phone} should not retrieve tenant 2 client.
    get_by_phone_response = api_client.get(f'/clients/by-phone/{tenant_two_client_one_phone}', headers=headers)
    assert get_by_phone_response.status_code == 404 or get_by_phone_response.json() == {}

    # PATCH /clients/{id} should not update tenant 2 client.
    patch_payload = {
        'name': 'Illegal Update Attempt',
        'phone': '9999999999',
        'description': 'Should not be applied by tenant 1',
    }
    patch_response = api_client.patch(f'/clients/{tenant_two_client_one_id}', json=patch_payload, headers=headers)
    assert patch_response.status_code == 404 or patch_response.json() == {}

    # DELETE /clients/{id} should not delete tenant 2 client.
    delete_response = api_client.delete(f'/clients/{tenant_two_client_two_id}', headers=headers)
    assert delete_response.json()['deleted'] == False

    # Note for future coverage:
    # Add a multi-tenant POST-focused test once authentication/authorization is implemented.
