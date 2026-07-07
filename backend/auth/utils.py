from typing_extensions import Annotated
from dotenv import load_dotenv
import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from backend.auth.models import TokenData
from backend.database.connect import connect
from backend.auth import repository

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv('ACCESS_TOKEN_EXPIRE_HOURS'))

password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)

def get_password_hash(password):
    return password_hash.hash(password)

def create_access_token(data: dict) -> str: #here the user_id is passed in the data dict
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return TokenData(user_id=int(user_id))
    except InvalidTokenError:
        raise credentials_exception

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    token_data = decode_token(token)
    with connect() as conn:
        user = repository.get_user_by_id(conn, token_data.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return user

CurrentUser = Annotated[dict, Depends(get_current_user)]

def get_current_user_from_query(token: str = Query(...)) -> dict:
    """Resolve the current user from a `?token=` query param.

    Delegates to get_current_user; the only difference is that the token is read
    from the query string instead of the Authorization header. Needed for SSE,
    since the browser EventSource API cannot send custom headers.
    """
    return get_current_user(token)

CurrentUserFromQuery = Annotated[dict, Depends(get_current_user_from_query)]
