"""Create the Conduit single-table schema in a local DynamoDB.

Schema mirrors the Terraform `modules/dynamodb` definition:
  hash=PK, range=SK, plus GSI1/GSI2/GSI3 (GSIxPK/GSIxSK), all PAY_PER_REQUEST.
  GSI3 (GSI3PK=ARTICLE_FEED, GSI3SK=created_at) backs the global recent-articles feed.

Usage (with the backend venv active):
  AWS_ENDPOINT_URL_DYNAMODB=http://localhost:8001 python scripts/create_local_table.py
"""
import os

import boto3
from botocore.exceptions import ClientError

TABLE = os.getenv("DYNAMODB_TABLE", "conduit")
ENDPOINT = os.getenv("AWS_ENDPOINT_URL_DYNAMODB", "http://localhost:8001")
REGION = os.getenv("AWS_REGION_APP", "ap-southeast-1")


def main() -> None:
    ddb = boto3.client(
        "dynamodb",
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "local"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "local"),
    )

    attrs = [
        {"AttributeName": n, "AttributeType": "S"}
        for n in ("PK", "SK", "GSI1PK", "GSI1SK", "GSI2PK", "GSI2SK", "GSI3PK", "GSI3SK")
    ]
    gsis = [
        {
            "IndexName": "GSI1",
            "KeySchema": [
                {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        },
        {
            "IndexName": "GSI2",
            "KeySchema": [
                {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        },
        {
            "IndexName": "GSI3",
            "KeySchema": [
                {"AttributeName": "GSI3PK", "KeyType": "HASH"},
                {"AttributeName": "GSI3SK", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        },
    ]

    try:
        ddb.create_table(
            TableName=TABLE,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=attrs,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=gsis,
        )
        print(f"OK: created table '{TABLE}' at {ENDPOINT}")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceInUseException":
            print(f"Table '{TABLE}' already exists — nothing to do.")
        else:
            raise


if __name__ == "__main__":
    main()
