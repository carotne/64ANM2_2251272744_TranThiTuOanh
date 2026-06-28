from fastapi import APIRouter, Depends

from app.routes.dependencies import current_user
from app.schemas.user import (
    UserLoginRequest,
    UserRegistrationRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.user import UserService, user_to_response

router = APIRouter()


@router.post("/users", response_model=UserResponse)
def register(payload: UserRegistrationRequest) -> UserResponse:
    item = UserService().register(
        email=payload.user.email,
        username=payload.user.username,
        password=payload.user.password,
    )
    return UserResponse(user=user_to_response(item))


@router.post("/users/login", response_model=UserResponse)
def login(payload: UserLoginRequest) -> UserResponse:
    item = UserService().login(email=payload.user.email, password=payload.user.password)
    return UserResponse(user=user_to_response(item))


@router.get("/user", response_model=UserResponse)
def me(user=Depends(current_user)) -> UserResponse:
    return UserResponse(user=user_to_response(user))


@router.put("/user", response_model=UserResponse)
def update_me(payload: UserUpdateRequest, user=Depends(current_user)) -> UserResponse:
    updated = UserService().update(user["id"], fields=payload.user.model_dump(exclude_none=True))
    return UserResponse(user=user_to_response(updated))
