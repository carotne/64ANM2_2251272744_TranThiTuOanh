from fastapi import HTTPException, Request, status

from app.repositories.user import UserRepository
from app.security import decode_jwt, extract_token


def _user_from_token(token: str) -> dict:
    payload = decode_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    user = UserRepository().get_by_id(user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def current_user(request: Request) -> dict:
    token = extract_token(request, required=True)
    return _user_from_token(token)


def current_user_optional(request: Request) -> dict | None:
    token = extract_token(request, required=False)
    if token is None:
        return None
    return _user_from_token(token)
