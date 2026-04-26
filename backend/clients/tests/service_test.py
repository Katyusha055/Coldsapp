from pathlib import Path
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
import os

tests_dir = Path(__file__).resolve().parent
test_env_file = tests_dir / '.env.tests'

@pytest.fixture(scope='session', autouse=True)
def load_test_env():
    load_dotenv(dotenv_path=test_env_file, override=True)
    if not test_env_file.exists():
        raise FileNotFoundError(f"Test environment file not found: {test_env_file}")
    if 'test' not in test_env_file.read_text():
        raise ValueError(f"Test environment file does not contain 'test' keyword in the database name: {os.getenv('DB_NAME')}")
    
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
def create_user():
    from backend.database.connect import connect
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (name, phone, password_hash)
                VALUES ('Test User', '1234567890', 'hashed_password')
                RETURNING id;
            """)
            user_id = cur.fetchone()[0]
    return user_id


def test_post_clients_endpoint_creates_client_validates_db_and_rejects_invalid_payload(
    api_client, create_user
):
    from backend.database.connect import connect

    user_id = create_user
    assert user_id == 1

    valid_payload = {
        "name": "Client Test",
        "phone": "5551234567",
        "description": "Created from service_test",
    }
    response = api_client.post("/clients/", json=valid_payload)

    assert response.status_code in (200, 201)
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == valid_payload["name"]
    assert body["phone"] == valid_payload["phone"]
    assert body["description"] == valid_payload["description"]
    assert "created_at" in body

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, name, phone, description
                FROM clients
                WHERE id = %s
                """,
                (body["id"],),
            )
            row = cur.fetchone()

    assert row is not None
    assert row[0] == body["id"]
    assert row[1] == user_id
    assert row[2] == valid_payload["name"]
    assert row[3] == valid_payload["phone"]
    assert row[4] == valid_payload["description"]

    invalid_payload = {
        "name": "Client Without Phone",
        "description": "Missing required phone",
    }
    invalid_response = api_client.post("/clients/", json=invalid_payload)

    assert invalid_response.status_code == 422
    invalid_body = invalid_response.json()
    assert "detail" in invalid_body
    assert any(
        error.get("loc", [])[-1] == "phone" and error.get("type")
        for error in invalid_body["detail"]
    )


def test_get_clients_endpoints_list_by_id_by_phone_and_invalid_missing_id(
    api_client, create_user
):
    from backend.database.connect import connect

    user_id = create_user
    assert user_id == 1

    payload_one = {
        "name": "Client One",
        "phone": "5551000001",
        "description": "First client for GET tests",
    }
    payload_two = {
        "name": "Client Two",
        "phone": "5551000002",
        "description": "Second client for GET tests",
    }

    create_response_one = api_client.post("/clients/", json=payload_one)
    create_response_two = api_client.post("/clients/", json=payload_two)

    assert create_response_one.status_code in (200, 201)
    assert create_response_two.status_code in (200, 201)

    created_one = create_response_one.json()
    created_two = create_response_two.json()

    assert created_one["id"] > 0
    assert created_two["id"] > created_one["id"]

    # GET /clients/
    get_clients_response = api_client.get("/clients/")
    assert get_clients_response.status_code == 200

    clients_body = get_clients_response.json()
    assert isinstance(clients_body, list)
    assert len(clients_body) >= 2
    assert any(client["id"] == created_one["id"] for client in clients_body)
    assert any(client["id"] == created_two["id"] for client in clients_body)

    # GET /clients/client_by_name/{id} (current endpoint used as "by id")
    get_by_id_response = api_client.get(f"/clients/client_by_name/{created_one['id']}")
    assert get_by_id_response.status_code == 200
    by_id_body = get_by_id_response.json()
    assert by_id_body["id"] == created_one["id"]
    assert by_id_body["name"] == payload_one["name"]
    assert by_id_body["phone"] == payload_one["phone"]
    assert by_id_body["description"] == payload_one["description"]

    # GET /clients/client_by_phone/{phone}
    get_by_phone_response = api_client.get(f"/clients/client_by_phone/{payload_two['phone']}")
    assert get_by_phone_response.status_code == 200
    by_phone_body = get_by_phone_response.json()
    assert by_phone_body["id"] == created_two["id"]
    assert by_phone_body["name"] == payload_two["name"]
    assert by_phone_body["phone"] == payload_two["phone"]
    assert by_phone_body["description"] == payload_two["description"]

    # DB validation for created records
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, name, phone, description
                FROM clients
                WHERE id IN (%s, %s)
                ORDER BY id
                """,
                (created_one["id"], created_two["id"]),
            )
            rows = cur.fetchall()

    assert len(rows) == 2
    assert rows[0] == (
        created_one["id"],
        user_id,
        payload_one["name"],
        payload_one["phone"],
        payload_one["description"],
    )
    assert rows[1] == (
        created_two["id"],
        user_id,
        payload_two["name"],
        payload_two["phone"],
        payload_two["description"],
    )

    # Invalid GET without required path param (missing id)
    invalid_get_response = api_client.get("/clients/client_by_name/")
    assert invalid_get_response.status_code == 422
    invalid_get_body = invalid_get_response.json()
    assert "detail" in invalid_get_body
