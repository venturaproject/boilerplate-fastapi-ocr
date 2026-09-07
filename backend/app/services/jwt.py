import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings


class JwtService:
    def __init__(self) -> None:
        self._secret = settings.secret_key
        self._algorithm = settings.jwt_algorithm
        self._issuer = settings.jwt_issuer
        self._audience = settings.jwt_audience

    def generate_access_token(
        self,
        user_id: uuid.UUID,
        name: str,
        roles: list[str],
        permissions: list[str],
    ) -> str:
        now = datetime.now(tz=UTC)
        payload = {
            "sub": str(user_id),
            "name": name,
            "roles": roles,
            "permissions": permissions,
            "token_type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=settings.jwt_access_ttl_seconds),
            "iss": self._issuer,
            "aud": self._audience,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def generate_refresh_token(self, user_id: uuid.UUID) -> tuple[str, str]:
        jti = str(uuid.uuid4())
        now = datetime.now(tz=UTC)
        payload = {
            "sub": str(user_id),
            "jti": jti,
            "token_type": "refresh",
            "iat": now,
            "exp": now + timedelta(seconds=settings.jwt_refresh_ttl_seconds),
            "iss": self._issuer,
            "aud": self._audience,
        }
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        return token, jti

    def validate_access_token(self, token: str) -> dict | None:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                audience=self._audience,
            )
            if payload.get("token_type") != "access":
                return None
            return payload
        except jwt.PyJWTError:
            return None

    def validate_refresh_token(self, token: str) -> dict | None:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                audience=self._audience,
            )
            if payload.get("token_type") != "refresh":
                return None
            return payload
        except jwt.PyJWTError:
            return None


jwt_service = JwtService()
