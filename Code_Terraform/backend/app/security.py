import datetime
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, Request, status

from app.settings import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_jwt(user_id: str, username: str) -> str:
    settings = get_settings()
    now = datetime.datetime.now(tz=datetime.UTC)
    payload = {
        "sub": user_id,
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(seconds=settings.jwt_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_jwt(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc


def extract_token(request: Request, required: bool = True) -> str | None:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        if required:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
        return None

    # RealWorld uses "Token <jwt>"; also accept "Bearer <jwt>"
    parts = auth.split(maxsplit=1)
    if len(parts) != 2 or parts[0] not in {"Token", "Bearer"}:
        if required:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
        return None
    return parts[1]
