import datetime
import uuid
from typing import Any

from boto3.dynamodb.conditions import Key

from app.db import get_table
from app.repositories import keys


def _now_iso() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()


class UserRepository:
    def __init__(self) -> None:
        self.table = get_table()

    def create(self, *, email: str, username: str, password_hash: str) -> dict[str, Any]:
        user_id = str(uuid.uuid4())
        now = _now_iso()
        item = {
            "PK": keys.USER_PK.format(user_id=user_id),
            "SK": keys.USER_SK,
            "GSI1PK": keys.EMAIL_GSI1PK.format(email=email.lower()),
            "GSI1SK": "EMAIL",
            "GSI2PK": keys.USERNAME_GSI2PK.format(username=username.lower()),
            "GSI2SK": "USERNAME",
            "entity": "USER",
            "id": user_id,
            "email": email,
            "username": username,
            "password_hash": password_hash,
            "bio": "",
            "image": "",
            "created_at": now,
            "updated_at": now,
        }
        self.table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(PK)",
        )
        return item

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        resp = self.table.get_item(Key={"PK": keys.USER_PK.format(user_id=user_id), "SK": keys.USER_SK})
        return resp.get("Item")

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        resp = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(keys.EMAIL_GSI1PK.format(email=email.lower())),
            Limit=1,
        )
        items = resp.get("Items") or []
        return items[0] if items else None

    def get_by_username(self, username: str) -> dict[str, Any] | None:
        resp = self.table.query(
            IndexName="GSI2",
            KeyConditionExpression=Key("GSI2PK").eq(keys.USERNAME_GSI2PK.format(username=username.lower())),
            Limit=1,
        )
        items = resp.get("Items") or []
        return items[0] if items else None

    def update(self, user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        current = self.get_by_id(user_id)
        if current is None:
            raise KeyError(user_id)

        updates: dict[str, Any] = {k: v for k, v in fields.items() if v is not None}
        updates["updated_at"] = _now_iso()

        expr_names = {f"#{k}": k for k in updates}
        expr_values = {f":{k}": v for k, v in updates.items()}
        set_expr = ", ".join(f"#{k} = :{k}" for k in updates)

        if "email" in updates:
            expr_names["#GSI1PK"] = "GSI1PK"
            expr_values[":GSI1PK"] = keys.EMAIL_GSI1PK.format(email=updates["email"].lower())
            set_expr += ", #GSI1PK = :GSI1PK"
        if "username" in updates:
            expr_names["#GSI2PK"] = "GSI2PK"
            expr_values[":GSI2PK"] = keys.USERNAME_GSI2PK.format(username=updates["username"].lower())
            set_expr += ", #GSI2PK = :GSI2PK"

        resp = self.table.update_item(
            Key={"PK": keys.USER_PK.format(user_id=user_id), "SK": keys.USER_SK},
            UpdateExpression=f"SET {set_expr}",
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
        return resp["Attributes"]


class FollowRepository:
    def __init__(self) -> None:
        self.table = get_table()

    def follow(self, follower_id: str, followed_id: str) -> None:
        self.table.put_item(
            Item={
                "PK": keys.USER_PK.format(user_id=follower_id),
                "SK": keys.FOLLOW_SK.format(followed_id=followed_id),
                "GSI2PK": keys.FOLLOWER_GSI2PK.format(followed_id=followed_id),
                "GSI2SK": keys.FOLLOWER_GSI2SK.format(follower_id=follower_id),
                "entity": "FOLLOW",
                "follower_id": follower_id,
                "followed_id": followed_id,
                "created_at": _now_iso(),
            }
        )

    def unfollow(self, follower_id: str, followed_id: str) -> None:
        self.table.delete_item(
            Key={
                "PK": keys.USER_PK.format(user_id=follower_id),
                "SK": keys.FOLLOW_SK.format(followed_id=followed_id),
            }
        )

    def is_following(self, follower_id: str | None, followed_id: str) -> bool:
        if not follower_id:
            return False
        resp = self.table.get_item(
            Key={
                "PK": keys.USER_PK.format(user_id=follower_id),
                "SK": keys.FOLLOW_SK.format(followed_id=followed_id),
            }
        )
        return "Item" in resp

    def list_followed(self, follower_id: str) -> list[str]:
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(keys.USER_PK.format(user_id=follower_id))
            & Key("SK").begins_with("FOLLOWS#")
        )
        return [item["followed_id"] for item in resp.get("Items") or []]
