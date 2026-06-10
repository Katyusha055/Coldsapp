import pytest
from fastapi import HTTPException

from backend.auth.service import login, register_user


def test_register_user_valid_data_returns_user_response():
    result = register_user({"name": "Test User", "phone": "0999999999", "password": "testpassword"})

    assert result.id > 0
    assert result.name == "Test User"
    assert result.phone == "0999999999"


def test_login_valid_credentials_returns_access_token():
    register_user({"name": "Test User", "phone": "0999999999", "password": "testpassword"})

    result = login("0999999999", "testpassword")

    assert result.access_token
    assert result.token_type == "bearer"


def test_login_wrong_password_raises_401():
    register_user({"name": "Test User", "phone": "0999999999", "password": "testpassword"})

    with pytest.raises(HTTPException) as exc_info:
        login("0999999999", "wrongpassword")

    assert exc_info.value.status_code == 401


def test_login_unregistered_phone_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        login("0000000000", "testpassword")

    assert exc_info.value.status_code == 401
