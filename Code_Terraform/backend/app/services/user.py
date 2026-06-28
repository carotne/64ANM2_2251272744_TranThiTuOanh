from typing import Any

from fastapi import HTTPException, status

from app.repositories.user import FollowRepository, UserRepository
from app.schemas.user import ProfileData, UserResponseData
from app.security import create_jwt, hash_password, verify_password


def user_to_response(item: dict[str, Any]) -> UserResponseData:
    return UserResponseData(
        email=item["email"],
        username=item["username"],
        bio=item.get("bio") or "",
        image=item.get("image") or "",
        token=create_jwt(user_id=item["id"], username=item["username"]),
    )


def profile_from_user(user: dict[str, Any], following: bool) -> ProfileData:
    return ProfileData(
        username=user["username"],
        bio=user.get("bio") or "",
        image=user.get("image") or "",
        following=following,
    )


class UserService:
    def __init__(self) -> None:
        self.users = UserRepository()

    def register(self, *, email: str, username: str, password: str) -> dict[str, Any]:
        if self.users.get_by_email(email):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")
        if self.users.get_by_username(username):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Username already taken")
        return self.users.create(email=email, username=username, password_hash=hash_password(password))

    def login(self, *, email: str, password: str) -> dict[str, Any]:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user["password_hash"]):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return user

    def update(self, user_id: str, *, fields: dict[str, Any]) -> dict[str, Any]:
        if "password" in fields and fields["password"]:
            fields["password_hash"] = hash_password(fields.pop("password"))
        else:
            fields.pop("password", None)
        return self.users.update(user_id, fields)


class ProfileService:
    def __init__(self) -> None:
        self.users = UserRepository()
        self.follows = FollowRepository()

    def get_by_username(self, username: str, current_user_id: str | None) -> ProfileData:
        user = self.users.get_by_username(username)
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profile not found")
        following = self.follows.is_following(current_user_id, user["id"])
        return profile_from_user(user, following)

    def follow(self, username: str, current_user_id: str) -> ProfileData:
        user = self.users.get_by_username(username)
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profile not found")
        self.follows.follow(current_user_id, user["id"])
        return profile_from_user(user, True)

    def unfollow(self, username: str, current_user_id: str) -> ProfileData:
        user = self.users.get_by_username(username)
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profile not found")
        self.follows.unfollow(current_user_id, user["id"])
        return profile_from_user(user, False)
