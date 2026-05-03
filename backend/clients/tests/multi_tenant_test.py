from pathlib import Path
import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient


tests_dir = Path(__file__).resolve().parent
test_env_file = tests_dir / '.env.tests'


@pytest.fixture(scope='session', autouse=True)
def load_test_env():
    load_dotenv(dotenv_path=test_env_file, override=True)
    if not test_env_file.exists():
        raise FileNotFoundError(f"Test environment file not found: {test_env_file}")
    if 'test' not in test_env_file.read_text():
        raise ValueError(
            f"Test environment file does not contain 'test' keyword in the database name: {os.getenv('DB_NAME')}"
        )


@pytest.fixture()
def api_client():
    from backend.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def clean_db():
    yield
    from backend.database.connect import connect

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE clients, users RESTART IDENTITY CASCADE;")


@pytest.fixture()
def create_users():
    from backend.database.connect import connect

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (name, phone, password_hash)
                VALUES
                    ('Tenant One', '1111111111', 'hashed_password_1'),
                    ('Tenant Two', '2222222222', 'hashed_password_2')
                RETURNING id;
                """
            )
            rows = cur.fetchall()

    user_ids = [row[0] for row in rows]
    return user_ids


@pytest.fixture()
def create_user_two_clients(create_users):
    from backend.database.connect import connect

    user_one_id, user_two_id = create_users

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


def test_tenant_one_cannot_access_or_modify_tenant_two_clients(api_client, create_user_two_clients):
    seeded = create_user_two_clients
    user_one_id, user_two_id = seeded['user_ids']
    client_one, client_two = seeded['clients']

    assert user_one_id == 1
    assert user_two_id == 2

    tenant_two_client_one_id = client_one[0]
    tenant_two_client_one_phone = client_one[3]
    tenant_two_client_two_id = client_two[0]

    # GET /clients/ should not include tenant 2 clients when auth is hardcoded to user_id = 1.
    list_response = api_client.get('/clients/')
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert isinstance(list_body, list)
    assert all(client['id'] not in (tenant_two_client_one_id, tenant_two_client_two_id) for client in list_body)

    # GET /clients/{id} should not retrieve tenant 2 client.
    get_by_id_response = api_client.get(f'/clients/{tenant_two_client_one_id}')
    assert get_by_id_response.status_code == 404 or get_by_id_response.json() == {}

    # GET /clients/by-phone/{phone} should not retrieve tenant 2 client.
    get_by_phone_response = api_client.get(f'/clients/by-phone/{tenant_two_client_one_phone}')
    assert get_by_phone_response.status_code == 404 or get_by_phone_response.json() == {}

    # PATCH /clients/{id} should not update tenant 2 client.
    patch_payload = {
        'name': 'Illegal Update Attempt',
        'phone': '9999999999',
        'description': 'Should not be applied by tenant 1',
    }
    patch_response = api_client.patch(f'/clients/{tenant_two_client_one_id}', json=patch_payload)
    assert patch_response.status_code == 404 or patch_response.json() == {}

    # DELETE /clients/{id} should not delete tenant 2 client.
    delete_response = api_client.delete(f'/clients/{tenant_two_client_two_id}')
    assert delete_response.json()['deleted'] == False

    # Note for future coverage:
    # Add a multi-tenant POST-focused test once authentication/authorization is implemented.
