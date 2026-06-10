import pytest


def test_register_endpoint_creates_user_returns_id_name_phone_without_password_hash(api_client):
    response = api_client.post(
        "/auth/register",
        json={"name": "Test User", "phone": "0999999999", "password": "testpassword"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == "Test User"
    assert body["phone"] == "0999999999"
    assert "password_hash" not in body
    assert "password" not in body


def test_register_endpoint_rejects_duplicate_phone_with_400(api_client, create_user):
    create_user("0999999999")

    response = api_client.post(
        "/auth/register",
        json={"name": "Another User", "phone": "0999999999", "password": "testpassword"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Phone already registered"


def test_register_endpoint_rejects_missing_name_with_422(api_client):
    response = api_client.post(
        "/auth/register",
        json={"phone": "0999999999", "password": "testpassword"},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_register_endpoint_rejects_missing_phone_with_422(api_client):
    response = api_client.post(
        "/auth/register",
        json={"name": "Test User", "password": "testpassword"},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_register_endpoint_rejects_missing_password_with_422(api_client):
    response = api_client.post(
        "/auth/register",
        json={"name": "Test User", "phone": "0999999999"},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_login_endpoint_valid_credentials_returns_token(api_client, create_user):
    create_user("0999999999")

    response = api_client.post(
        "/auth/token",
        data={"username": "0999999999", "password": "testpassword"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_endpoint_wrong_phone_returns_401(api_client):
    response = api_client.post(
        "/auth/token",
        data={"username": "0000000000", "password": "testpassword"},
    )

    assert response.status_code == 401


def test_login_endpoint_wrong_password_returns_401(api_client, create_user):
    create_user("0999999999")

    response = api_client.post(
        "/auth/token",
        data={"username": "0999999999", "password": "wrongpassword"},
    )

    assert response.status_code == 401


def test_login_endpoint_unregistered_phone_returns_401(api_client):
    response = api_client.post(
        "/auth/token",
        data={"username": "0888888888", "password": "testpassword"},
    )

    assert response.status_code == 401


def test_register_login_and_access_protected_endpoint_end_to_end(api_client):
    register_response = api_client.post(
        "/auth/register",
        json={"name": "E2E User", "phone": "0777777777", "password": "e2epassword"},
    )
    assert register_response.status_code == 201

    login_response = api_client.post(
        "/auth/token",
        data={"username": "0777777777", "password": "e2epassword"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    protected_response = api_client.get("/tickets/", headers=headers)
    assert protected_response.status_code == 200
