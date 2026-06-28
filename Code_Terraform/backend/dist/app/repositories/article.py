import datetime
import uuid
from typing import Any

from boto3.dynamodb.conditions import Key
from slugify import slugify

from app.db import get_table
from app.repositories import keys


def _now_iso() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()


class ArticleRepository:
    def __init__(self) -> None:
        self.table = get_table()

    def create(
        self,
        *,
        author_id: str,
        title: str,
        description: str,
        body: str,
        tags: list[str],
    ) -> dict[str, Any]:
        article_id = str(uuid.uuid4())
        slug = f"{slugify(title)}-{article_id[:8]}"
        now = _now_iso()
        item = {
            "PK": keys.ARTICLE_PK.format(article_id=article_id),
            "SK": keys.ARTICLE_SK,
            "GSI1PK": keys.SLUG_GSI1PK.format(slug=slug),
            "GSI1SK": "SLUG",
            "GSI2PK": keys.AUTHOR_GSI2PK.format(author_id=author_id),
            "GSI2SK": keys.AUTHOR_GSI2SK.format(created_at=now, article_id=article_id),
            "GSI3PK": keys.FEED_GSI3PK,
            "GSI3SK": now,
            "entity": "ARTICLE",
            "id": article_id,
            "slug": slug,
            "title": title,
            "description": description,
            "body": body,
            "tags": tags,
            "author_id": author_id,
            "favorites_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        self.table.put_item(Item=item)

        for tag in tags:
            self.table.put_item(
                Item={
                    "PK": keys.TAG_PK.format(tag=tag.lower()),
                    "SK": keys.TAG_ARTICLE_SK.format(article_id=article_id),
                    "GSI1PK": keys.TAG_LIST_GSI1PK,
                    "GSI1SK": tag.lower(),
                    "entity": "TAG_INDEX",
                    "tag": tag,
                    "article_id": article_id,
                }
            )
        return item

    def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        resp = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(keys.SLUG_GSI1PK.format(slug=slug)),
            Limit=1,
        )
        items = resp.get("Items") or []
        return items[0] if items else None

    def get_by_id(self, article_id: str) -> dict[str, Any] | None:
        resp = self.table.get_item(
            Key={"PK": keys.ARTICLE_PK.format(article_id=article_id), "SK": keys.ARTICLE_SK}
        )
        return resp.get("Item")

    def update(self, article: dict[str, Any], fields: dict[str, Any]) -> dict[str, Any]:
        updates = {k: v for k, v in fields.items() if v is not None}
        updates["updated_at"] = _now_iso()

        if "title" in updates:
            new_slug = f"{slugify(updates['title'])}-{article['id'][:8]}"
            updates["slug"] = new_slug

        expr_names = {f"#{k}": k for k in updates}
        expr_values = {f":{k}": v for k, v in updates.items()}
        set_expr = ", ".join(f"#{k} = :{k}" for k in updates)

        if "slug" in updates:
            expr_names["#GSI1PK"] = "GSI1PK"
            expr_values[":GSI1PK"] = keys.SLUG_GSI1PK.format(slug=updates["slug"])
            set_expr += ", #GSI1PK = :GSI1PK"

        resp = self.table.update_item(
            Key={"PK": article["PK"], "SK": article["SK"]},
            UpdateExpression=f"SET {set_expr}",
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
        return resp["Attributes"]

    def delete(self, article: dict[str, Any]) -> None:
        self.table.delete_item(Key={"PK": article["PK"], "SK": article["SK"]})
        for tag in article.get("tags") or []:
            self.table.delete_item(
                Key={
                    "PK": keys.TAG_PK.format(tag=tag.lower()),
                    "SK": keys.TAG_ARTICLE_SK.format(article_id=article["id"]),
                }
            )

    def list_by_author(self, author_id: str, *, limit: int, offset: int) -> list[dict[str, Any]]:
        resp = self.table.query(
            IndexName="GSI2",
            KeyConditionExpression=Key("GSI2PK").eq(keys.AUTHOR_GSI2PK.format(author_id=author_id)),
            ScanIndexForward=False,
            Limit=limit + offset,
        )
        items = resp.get("Items") or []
        return items[offset : offset + limit]

    def list_by_tag(self, tag: str, *, limit: int, offset: int) -> list[dict[str, Any]]:
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(keys.TAG_PK.format(tag=tag.lower()))
            & Key("SK").begins_with("ARTICLE#"),
        )
        article_ids = [item["article_id"] for item in resp.get("Items") or []]
        articles = [self.get_by_id(aid) for aid in article_ids]
        articles = [a for a in articles if a]
        articles.sort(key=lambda a: a["created_at"], reverse=True)
        return articles[offset : offset + limit]

    def list_recent(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        # Global recent feed: every article carries GSI3PK=ARTICLE_FEED, so we Query that
        # constant partition (newest first) instead of scanning the whole table.
        resp = self.table.query(
            IndexName="GSI3",
            KeyConditionExpression=Key("GSI3PK").eq(keys.FEED_GSI3PK),
            ScanIndexForward=False,
            Limit=limit + offset,
        )
        items = resp.get("Items") or []
        return items[offset : offset + limit]


class FavoriteRepository:
    def __init__(self) -> None:
        self.table = get_table()

    def favorite(self, user_id: str, article_id: str) -> None:
        self.table.put_item(
            Item={
                "PK": keys.USER_PK.format(user_id=user_id),
                "SK": keys.FAV_SK.format(article_id=article_id),
                "GSI2PK": keys.FAV_ARTICLE_GSI2PK.format(article_id=article_id),
                "GSI2SK": keys.FAV_USER_GSI2SK.format(user_id=user_id),
                "entity": "FAVORITE",
                "user_id": user_id,
                "article_id": article_id,
                "created_at": _now_iso(),
            }
        )
        self.table.update_item(
            Key={"PK": keys.ARTICLE_PK.format(article_id=article_id), "SK": keys.ARTICLE_SK},
            UpdateExpression="ADD favorites_count :one",
            ExpressionAttributeValues={":one": 1},
        )

    def unfavorite(self, user_id: str, article_id: str) -> None:
        self.table.delete_item(
            Key={
                "PK": keys.USER_PK.format(user_id=user_id),
                "SK": keys.FAV_SK.format(article_id=article_id),
            }
        )
        self.table.update_item(
            Key={"PK": keys.ARTICLE_PK.format(article_id=article_id), "SK": keys.ARTICLE_SK},
            UpdateExpression="ADD favorites_count :neg",
            ExpressionAttributeValues={":neg": -1},
        )

    def is_favorited(self, user_id: str | None, article_id: str) -> bool:
        if not user_id:
            return False
        resp = self.table.get_item(
            Key={
                "PK": keys.USER_PK.format(user_id=user_id),
                "SK": keys.FAV_SK.format(article_id=article_id),
            }
        )
        return "Item" in resp


class TagRepository:
    def __init__(self) -> None:
        self.table = get_table()

    def list_all(self) -> list[str]:
        resp = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(keys.TAG_LIST_GSI1PK),
        )
        return sorted({item["tag"] for item in resp.get("Items") or []})


class CommentRepository:
    def __init__(self) -> None:
        self.table = get_table()

    def create(self, *, article_id: str, author_id: str, body: str) -> dict[str, Any]:
        comment_id = str(uuid.uuid4())
        now = _now_iso()
        item = {
            "PK": keys.ARTICLE_PK.format(article_id=article_id),
            "SK": keys.COMMENT_SK.format(comment_id=comment_id),
            "GSI2PK": keys.COMMENT_GSI2PK.format(comment_id=comment_id),
            "GSI2SK": keys.COMMENT_GSI2SK,
            "entity": "COMMENT",
            "id": comment_id,
            "article_id": article_id,
            "author_id": author_id,
            "body": body,
            "created_at": now,
            "updated_at": now,
        }
        self.table.put_item(Item=item)
        return item

    def list_for_article(self, article_id: str) -> list[dict[str, Any]]:
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(keys.ARTICLE_PK.format(article_id=article_id))
            & Key("SK").begins_with("COMMENT#")
        )
        items = resp.get("Items") or []
        items.sort(key=lambda c: c["created_at"])
        return items

    def delete(self, article_id: str, comment_id: str) -> None:
        self.table.delete_item(
            Key={
                "PK": keys.ARTICLE_PK.format(article_id=article_id),
                "SK": keys.COMMENT_SK.format(comment_id=comment_id),
            }
        )

    def get(self, article_id: str, comment_id: str) -> dict[str, Any] | None:
        resp = self.table.get_item(
            Key={
                "PK": keys.ARTICLE_PK.format(article_id=article_id),
                "SK": keys.COMMENT_SK.format(comment_id=comment_id),
            }
        )
        return resp.get("Item")
