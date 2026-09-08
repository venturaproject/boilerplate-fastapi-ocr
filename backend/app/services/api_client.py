import hashlib
import secrets
from datetime import UTC, datetime, timedelta

ACCESS_TOKEN_TTL = timedelta(hours=1)
REFRESH_TOKEN_TTL = timedelta(days=30)


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(40)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def access_expires_at() -> datetime:
    return datetime.now(tz=UTC) + ACCESS_TOKEN_TTL


def refresh_expires_at() -> datetime:
    return datetime.now(tz=UTC) + REFRESH_TOKEN_TTL


def access_ttl_seconds() -> int:
    return int(ACCESS_TOKEN_TTL.total_seconds())
