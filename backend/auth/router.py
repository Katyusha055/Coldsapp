from typing import Annotated
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from backend.auth import service
from backend.auth.models import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate):
    return service.register_user(user_data.model_dump())


@router.post("/token", response_model=Token)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    return service.login(form_data.username, form_data.password)