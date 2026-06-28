from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegistrationData(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    username: str = Field(..., min_length=3)


class UserLoginData(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserUpdateData(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8)
    username: str | None = Field(None, min_length=3)
    bio: str | None = None
    image: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def empty_as_none(cls, v: Any) -> Any:
        return v or None if isinstance(v, str) else v


class UserRegistrationRequest(BaseModel):
    user: UserRegistrationData


class UserLoginRequest(BaseModel):
    user: UserLoginData


class UserUpdateRequest(BaseModel):
    user: UserUpdateData


class UserResponseData(BaseModel):
    email: str
    username: str
    bio: str = ""
    image: str = ""
    token: str


class UserResponse(BaseModel):
    user: UserResponseData


class ProfileData(BaseModel):
    username: str
    bio: str = ""
    image: str = ""
    following: bool = False


class ProfileResponse(BaseModel):
    profile: ProfileData
