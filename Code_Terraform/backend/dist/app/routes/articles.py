from fastapi import APIRouter, Depends, Query
from starlette import status

from app.routes.dependencies import current_user, current_user_optional
from app.schemas.article import (
    ArticleResponse,
    ArticlesFeedResponse,
    CreateArticleRequest,
    TagsResponse,
    UpdateArticleRequest,
)
from app.services.article import ArticleService

router = APIRouter(prefix="/articles")
tags_router = APIRouter(prefix="/tags")


@router.get("/feed", response_model=ArticlesFeedResponse)
def feed(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(current_user),
) -> ArticlesFeedResponse:
    svc = ArticleService()
    items = svc.feed(current_user_id=user["id"], limit=limit, offset=offset)
    return ArticlesFeedResponse(
        articles=[svc.to_article_data(i, user["id"]) for i in items],
        articlesCount=len(items),
    )


@router.get("", response_model=ArticlesFeedResponse)
def list_articles(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tag: str | None = None,
    author: str | None = None,
    favorited: str | None = None,  # noqa: ARG001 (TODO: implement favorited-by filter)
    viewer=Depends(current_user_optional),
) -> ArticlesFeedResponse:
    svc = ArticleService()
    items = svc.list_global(limit=limit, offset=offset, tag=tag, author=author)
    viewer_id = viewer["id"] if viewer else None
    return ArticlesFeedResponse(
        articles=[svc.to_article_data(i, viewer_id) for i in items],
        articlesCount=len(items),
    )


@router.post("", response_model=ArticleResponse)
def create_article(payload: CreateArticleRequest, user=Depends(current_user)) -> ArticleResponse:
    svc = ArticleService()
    item = svc.create(author_id=user["id"], payload=payload.article.model_dump())
    return ArticleResponse(article=svc.to_article_data(item, user["id"]))


@router.get("/{slug}", response_model=ArticleResponse)
def get_article(slug: str, viewer=Depends(current_user_optional)) -> ArticleResponse:
    svc = ArticleService()
    item = svc.get_or_404(slug)
    viewer_id = viewer["id"] if viewer else None
    return ArticleResponse(article=svc.to_article_data(item, viewer_id))


@router.put("/{slug}", response_model=ArticleResponse)
def update_article(
    slug: str, payload: UpdateArticleRequest, user=Depends(current_user)
) -> ArticleResponse:
    svc = ArticleService()
    item = svc.update(
        slug,
        current_user_id=user["id"],
        fields=payload.article.model_dump(exclude_none=True),
    )
    return ArticleResponse(article=svc.to_article_data(item, user["id"]))


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(slug: str, user=Depends(current_user)) -> None:
    ArticleService().delete(slug, user["id"])


@router.post("/{slug}/favorite", response_model=ArticleResponse)
def favorite_article(slug: str, user=Depends(current_user)) -> ArticleResponse:
    svc = ArticleService()
    item = svc.favorite(slug, user["id"])
    return ArticleResponse(article=svc.to_article_data(item, user["id"]))


@router.delete("/{slug}/favorite", response_model=ArticleResponse)
def unfavorite_article(slug: str, user=Depends(current_user)) -> ArticleResponse:
    svc = ArticleService()
    item = svc.unfavorite(slug, user["id"])
    return ArticleResponse(article=svc.to_article_data(item, user["id"]))


@tags_router.get("", response_model=TagsResponse)
def list_tags() -> TagsResponse:
    return TagsResponse(tags=ArticleService().list_tags())
