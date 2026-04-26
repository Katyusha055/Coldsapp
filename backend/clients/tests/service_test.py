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

