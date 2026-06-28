from fastapi import APIRouter, Depends

from app.routes.dependencies import current_user, current_user_optional
from app.schemas.user import ProfileResponse
from app.services.user import ProfileService

router = APIRouter(prefix="/profiles")


@router.get("/{username}", response_model=ProfileResponse)
def get_profile(username: str, viewer=Depends(current_user_optional)) -> ProfileResponse:
    profile = ProfileService().get_by_username(username, viewer["id"] if viewer else None)
    return ProfileResponse(profile=profile)


@router.post("/{username}/follow", response_model=ProfileResponse)
def follow(username: str, viewer=Depends(current_user)) -> ProfileResponse:
    profile = ProfileService().follow(username, viewer["id"])
    return ProfileResponse(profile=profile)


@router.delete("/{username}/follow", response_model=ProfileResponse)
def unfollow(username: str, viewer=Depends(current_user)) -> ProfileResponse:
    profile = ProfileService().unfollow(username, viewer["id"])
    return ProfileResponse(profile=profile)
