import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    dynamodb_table: str = os.getenv("DYNAMODB_TABLE", "conduit")
    jwt_secret: str = os.getenv("JWT_SECRET", "insecure-dev-secret")
    jwt_algorithm: str = "HS256"
    jwt_ttl_seconds: int = 60 * 60 * 24 * 7
    aws_region: str = os.getenv("AWS_REGION_APP", os.getenv("AWS_REGION", "ap-southeast-1"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    allowed_origins: list[str] = ["*"]
    # Shared secret injected by CloudFront as the X-Origin-Verify header. When set,
    # requests missing the matching header are rejected (blocks direct API Gateway
    # access that bypasses CloudFront/WAF). Empty = disabled (e.g. local dev).
    origin_verify_secret: str = os.getenv("ORIGIN_VERIFY_SECRET", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
