from fastapi import APIRouter, Depends
from starlette import status

from app.routes.dependencies import current_user, current_user_optional
from app.schemas.article import (
    CommentResponse,
    CommentsListResponse,
    CreateCommentRequest,
)
from app.services.article import CommentService

router = APIRouter(prefix="/articles")


@router.get("/{slug}/comments", response_model=CommentsListResponse)
def list_comments(slug: str, viewer=Depends(current_user_optional)) -> CommentsListResponse:
    svc = CommentService()
    items = svc.list_for_slug(slug)
    viewer_id = viewer["id"] if viewer else None
    return CommentsListResponse(
        comments=[svc.to_comment_data(i, viewer_id) for i in items],
        commentsCount=len(items),
    )


@router.post("/{slug}/comments", response_model=CommentResponse)
def create_comment(
    slug: str, payload: CreateCommentRequest, user=Depends(current_user)
) -> CommentResponse:
    svc = CommentService()
    item = svc.create(slug=slug, author_id=user["id"], body=payload.comment.body)
    return CommentResponse(comment=svc.to_comment_data(item, user["id"]))


@router.delete("/{slug}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(slug: str, comment_id: str, user=Depends(current_user)) -> None:
    CommentService().delete(slug, comment_id, user["id"])
