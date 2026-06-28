import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuthorData(BaseModel):
    username: str
    bio: str = ""
    image: str = ""
    following: bool = False


class ArticleData(BaseModel):
    slug: str
    title: str
    description: str
    body: str
    tags: list[str] = Field(alias="tagList")
    created_at: datetime.datetime = Field(alias="createdAt")
    updated_at: datetime.datetime = Field(alias="updatedAt")
    favorited: bool = False
    favorites_count: int = Field(default=0, alias="favoritesCount")
    author: AuthorData

    model_config = ConfigDict(populate_by_name=True)


class ArticleResponse(BaseModel):
    article: ArticleData


class ArticlesFeedResponse(BaseModel):
    articles: list[ArticleData]
    articles_count: int = Field(alias="articlesCount")

    model_config = ConfigDict(populate_by_name=True)


class CreateArticleData(BaseModel):
    title: str = Field(..., min_length=5)
    description: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list, alias="tagList")

    model_config = ConfigDict(populate_by_name=True)


class CreateArticleRequest(BaseModel):
    article: CreateArticleData


class UpdateArticleData(BaseModel):
    title: str | None = None
    description: str | None = None
    body: str | None = None


class UpdateArticleRequest(BaseModel):
    article: UpdateArticleData


class CommentData(BaseModel):
    id: str
    body: str
    author: AuthorData
    created_at: datetime.datetime = Field(alias="createdAt")
    updated_at: datetime.datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class CreateCommentData(BaseModel):
    body: str = Field(..., min_length=1)


class CreateCommentRequest(BaseModel):
    comment: CreateCommentData


class CommentResponse(BaseModel):
    comment: CommentData


class CommentsListResponse(BaseModel):
    comments: list[CommentData]
    comments_count: int = Field(alias="commentsCount")

    model_config = ConfigDict(populate_by_name=True)


class TagsResponse(BaseModel):
    tags: list[str]
