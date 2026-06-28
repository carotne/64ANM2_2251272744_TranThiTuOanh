"""Backfill the global-feed index (GSI3) onto existing ARTICLE items.

Articles created before GSI3 was introduced lack GSI3PK/GSI3SK, so they do not
appear in the recent-articles feed (which now Queries GSI3 instead of Scanning).
This one-off migration:

  1. ensures the GSI3 index exists (adds it via UpdateTable if missing — handy for
     a local DynamoDB created before the change; on AWS the index is created by
     `terraform apply`, so this step is a no-op there);
  2. sets GSI3PK=ARTICLE_FEED and GSI3SK=<created_at> on every existing ARTICLE.

Run with developer/admin credentials (NOT the Lambda role — it intentionally has
no dynamodb:Scan). Examples:

  # Local DynamoDB
  AWS_ENDPOINT_URL_DYNAMODB=http://localhost:8001 python scripts/backfill_feed_gsi3.py

  # AWS (after `terraform apply` has added GSI3)
  DYNAMODB_TABLE=conduit-prod-conduit AWS_REGION_APP=ap-southeast-1 python scripts/backfill_feed_gsi3.py
"""
import os
import time

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

TABLE = os.getenv("DYNAMODB_TABLE", "conduit")
ENDPOINT = os.getenv("AWS_ENDPOINT_URL_DYNAMODB")  # set for local; unset on AWS
REGION = os.getenv("AWS_REGION_APP", "ap-southeast-1")

FEED_GSI3PK = "ARTICLE_FEED"  # mirrors app.repositories.keys.FEED_GSI3PK


def _client_kwargs() -> dict:
    kwargs = {"region_name": REGION}
    if ENDPOINT:
        kwargs.update(
            endpoint_url=ENDPOINT,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "local"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "local"),
        )
    return kwargs


def ensure_gsi3(ddb) -> None:
    """Add GSI3 if the table doesn't have it yet, then wait until it is ACTIVE."""
    desc = ddb.describe_table(TableName=TABLE)["Table"]
    existing = {g["IndexName"] for g in desc.get("GlobalSecondaryIndexes", [])}
    if "GSI3" in existing:
        print("GSI3 already exists — skipping index creation.")
        return

    print("GSI3 missing — creating via UpdateTable ...")
    ddb.update_table(
        TableName=TABLE,
        AttributeDefinitions=[
            {"AttributeName": "GSI3PK", "AttributeType": "S"},
            {"AttributeName": "GSI3SK", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexUpdates=[
            {
                "Create": {
                    "IndexName": "GSI3",
                    "KeySchema": [
                        {"AttributeName": "GSI3PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI3SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            }
        ],
    )
    for _ in range(60):
        gsis = ddb.describe_table(TableName=TABLE)["Table"].get("GlobalSecondaryIndexes", [])
        status = next((g["IndexStatus"] for g in gsis if g["IndexName"] == "GSI3"), None)
        if status == "ACTIVE":
            print("GSI3 is ACTIVE.")
            return
        time.sleep(2)
    print("WARNING: GSI3 not ACTIVE yet; backfill will still write attributes.")


def backfill(table) -> None:
    """Stamp GSI3PK/GSI3SK onto every ARTICLE item that lacks them."""
    scanned = updated = 0
    kwargs = {"FilterExpression": Attr("entity").eq("ARTICLE")}
    while True:
        resp = table.scan(**kwargs)
        for item in resp.get("Items", []):
            scanned += 1
            if item.get("GSI3PK") == FEED_GSI3PK:
                continue
            created_at = item.get("created_at")
            if not created_at:
                print(f"  skip {item.get('PK')} (no created_at)")
                continue
            table.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET GSI3PK = :pk, GSI3SK = :sk",
                ExpressionAttributeValues={":pk": FEED_GSI3PK, ":sk": created_at},
            )
            updated += 1
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    print(f"Done: {scanned} ARTICLE item(s) scanned, {updated} backfilled.")


def main() -> None:
    ddb = boto3.client("dynamodb", **_client_kwargs())
    table = boto3.resource("dynamodb", **_client_kwargs()).Table(TABLE)
    try:
        ensure_gsi3(ddb)
    except ClientError as exc:
        # ResourceInUseException = index already creating/active; safe to continue.
        if exc.response["Error"]["Code"] != "ResourceInUseException":
            raise
        print("GSI3 creation already in progress — continuing.")
    backfill(table)


if __name__ == "__main__":
    main()
