import jwt
from datetime import datetime, timezone, timedelta

from backend.auth.utils import SECRET_KEY, ALGORITHM


def test_request_without_token_returns_401(api_client):
    response = api_client.get("/tickets/")

    assert response.status_code == 401


def test_request_with_invalid_token_returns_401(api_client):
    response = api_client.get(
        "/tickets/",
        headers={"Authorization": "Bearer invalid_token_string"},
    )

    assert response.status_code == 401


def test_request_with_expired_token_returns_401(api_client):
    payload = {"sub": "999", "exp": datetime.now(timezone.utc) - timedelta(hours=1)}
    expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    response = api_client.get(
        "/tickets/",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


def test_token_contains_correct_user_id_as_string(api_client, create_user):
    user = create_user("0999999999")
    user_id = user["id"]

    token_response = api_client.post(
        "/auth/token",
        data={"username": "0999999999", "password": "testpassword"},
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == str(user_id)
