from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    db_host: str = "localhost"
    db_name: str = "fastapi_ocr_db"
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_port: int = 5432

    # JWT
    secret_key: str = "change-this-to-a-secret-key-with-at-least-32-chars"
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_seconds: int = 604800
    jwt_issuer: str = "fastapi-ocr"
    jwt_audience: str = "fastapi-ocr-frontend"
    jwt_algorithm: str = "HS256"

    # Cookies
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # CORS
    cors_allowed_origins: str = "http://localhost:8081,http://localhost:5173"

    # Media
    media_dir: str = "/app/backend/media"

    # App
    app_name: str = "FastAPI OCR"
    app_url: str = "http://localhost"

    # Admin seed
    admin_email: str = "admin@example.com"
    admin_password: str = "password"
    admin_name: str = "Admin"

    # Dashboard
    dashboard_recent_devices_limit: int = 5

    # Eventos (CQRS · outbox · inbox)
    events_worker_interval_seconds: float = 5.0
    idempotency_key_ttl_hours: int = 24

    # Rate limiting  ("<limit>/<segundos>")
    throttle_login: str = "5/60"
    throttle_ext_auth: str = "10/60"
    throttle_ext_api: str = "600/60"
    throttle_webhook: str = "120/60"
    throttle_ocr: str = "30/60"

    # ── OCR ──────────────────────────────────────────────────────────────────
    ocr_engine: Literal["paddle", "fake"] = "paddle"
    ocr_lang: str = "es"
    ocr_use_gpu: bool = False
    ocr_pdf_dpi: int = 200
    ocr_sync_max_bytes: int = 10_000_000
    ocr_sync_max_pages: int = 5
    ocr_max_upload_bytes: int = 52_428_800
    ocr_max_concurrency: int = 2
    ocr_worker_interval_seconds: float = 2.0
    ocr_job_retention_days: int = 7
    ocr_callback_timeout_seconds: int = 10
    ocr_model_dir: str = "/app/backend/.paddlex"

    def throttle(self, raw: str) -> tuple[int, int]:
        limit, per = raw.split("/", 1)
        return int(limit), int(per)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def ocr_storage_dir(self) -> str:
        return f"{self.media_dir.rstrip('/')}/ocr"

    def validate_secret_key(self) -> None:
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")


settings = Settings()
settings.validate_secret_key()
