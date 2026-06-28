from typing import Any

from fastapi import HTTPException, status

from app.repositories.article import (
    ArticleRepository,
    CommentRepository,
    FavoriteRepository,
    TagRepository,
)
from app.repositories.user import FollowRepository, UserRepository
from app.schemas.article import ArticleData, AuthorData, CommentData
from app.services.user import profile_from_user


class ArticleService:
    def __init__(self) -> None:
        self.articles = ArticleRepository()
        self.users = UserRepository()
        self.follows = FollowRepository()
        self.favorites = FavoriteRepository()
        self.tags = TagRepository()

    def _author_data(self, author_id: str, current_user_id: str | None) -> AuthorData:
        author = self.users.get_by_id(author_id)
        if author is None:
            return AuthorData(username="(unknown)")
        following = self.follows.is_following(current_user_id, author_id)
        profile = profile_from_user(author, following)
        return AuthorData(**profile.model_dump())

    def to_article_data(self, item: dict[str, Any], current_user_id: str | None) -> ArticleData:
        return ArticleData(
            slug=item["slug"],
            title=item["title"],
            description=item["description"],
            body=item["body"],
            tagList=item.get("tags") or [],
            createdAt=item["created_at"],
            updatedAt=item["updated_at"],
            favorited=self.favorites.is_favorited(current_user_id, item["id"]),
            favoritesCount=int(item.get("favorites_count") or 0),
            author=self._author_data(item["author_id"], current_user_id),
        )

    def create(self, *, author_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.articles.create(
            author_id=author_id,
            title=payload["title"],
            description=payload["description"],
            body=payload["body"],
            tags=payload.get("tags") or [],
        )

    def get_or_404(self, slug: str) -> dict[str, Any]:
        article = self.articles.get_by_slug(slug)
        if article is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Article not found")
        return article

    def update(self, slug: str, *, current_user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        article = self.get_or_404(slug)
        if article["author_id"] != current_user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the author")
        return self.articles.update(article, fields)

    def delete(self, slug: str, current_user_id: str) -> None:
        article = self.get_or_404(slug)
        if article["author_id"] != current_user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the author")
        self.articles.delete(article)

    def favorite(self, slug: str, current_user_id: str) -> dict[str, Any]:
        article = self.get_or_404(slug)
        self.favorites.favorite(current_user_id, article["id"])
        return self.articles.get_by_id(article["id"]) or article

    def unfavorite(self, slug: str, current_user_id: str) -> dict[str, Any]:
        article = self.get_or_404(slug)
        self.favorites.unfavorite(current_user_id, article["id"])
        return self.articles.get_by_id(article["id"]) or article

    def list_global(self, *, limit: int, offset: int, tag: str | None, author: str | None) -> list[dict[str, Any]]:
        if tag:
            return self.articles.list_by_tag(tag, limit=limit, offset=offset)
        if author:
            user = self.users.get_by_username(author)
            if user is None:
                return []
            return self.articles.list_by_author(user["id"], limit=limit, offset=offset)
        return self.articles.list_recent(limit=limit, offset=offset)

    def feed(self, *, current_user_id: str, limit: int, offset: int) -> list[dict[str, Any]]:
        followed = self.follows.list_followed(current_user_id)
        articles: list[dict[str, Any]] = []
        for author_id in followed:
            articles.extend(self.articles.list_by_author(author_id, limit=limit + offset, offset=0))
        articles.sort(key=lambda a: a["created_at"], reverse=True)
        return articles[offset : offset + limit]

    def list_tags(self) -> list[str]:
        return self.tags.list_all()


class CommentService:
    def __init__(self) -> None:
        self.comments = CommentRepository()
        self.articles = ArticleRepository()
        self.users = UserRepository()
        self.follows = FollowRepository()

    def to_comment_data(self, item: dict[str, Any], current_user_id: str | None) -> CommentData:
        author = self.users.get_by_id(item["author_id"]) or {"username": "(unknown)"}
        following = self.follows.is_following(current_user_id, item["author_id"])
        return CommentData(
            id=item["id"],
            body=item["body"],
            createdAt=item["created_at"],
            updatedAt=item["updated_at"],
            author=AuthorData(
                username=author.get("username", "(unknown)"),
                bio=author.get("bio") or "",
                image=author.get("image") or "",
                following=following,
            ),
        )

    def create(self, *, slug: str, author_id: str, body: str) -> dict[str, Any]:
        article = self.articles.get_by_slug(slug)
        if article is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Article not found")
        return self.comments.create(article_id=article["id"], author_id=author_id, body=body)

    def list_for_slug(self, slug: str) -> list[dict[str, Any]]:
        article = self.articles.get_by_slug(slug)
        if article is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Article not found")
        return self.comments.list_for_article(article["id"])

    def delete(self, slug: str, comment_id: str, current_user_id: str) -> None:
        article = self.articles.get_by_slug(slug)
        if article is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Article not found")
        comment = self.comments.get(article["id"], comment_id)
        if comment is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")
        if comment["author_id"] != current_user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the author")
        self.comments.delete(article["id"], comment_id)
