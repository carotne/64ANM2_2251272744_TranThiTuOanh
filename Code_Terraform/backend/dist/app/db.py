from functools import lru_cache

import boto3

from app.settings import get_settings


@lru_cache
def get_table():
    settings = get_settings()
    return boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.dynamodb_table)
