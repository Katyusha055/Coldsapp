from backend.database.connect import connect
from backend.auth import repository
from backend.auth.models import Token, UserResponse
from backend.auth.utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    DUMMY_HASH
)
from fastapi import HTTPException, status


def register_user(user_data: dict) -> dict:
    with connect() as conn:
        existing = repository.get_user_by_phone(conn, user_data["phone"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone already registered"
            )
        user_data["password_hash"] = get_password_hash(user_data["password"])
        del user_data["password"]
        return UserResponse(**repository.create_user(conn, user_data))


def login(phone: str, password: str) -> dict:
    with connect() as conn:
        user = repository.get_user_credentials(conn, phone)
        if not user:
            verify_password(password, DUMMY_HASH)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        if not verify_password(password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        access_token = create_access_token(data={"sub": str(user["id"])})
        return Token(**{"access_token": access_token, "token_type": "bearer"})


