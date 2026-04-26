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
