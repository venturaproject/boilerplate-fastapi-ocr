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

    # Media / storage
    media_dir: str = "/app/backend/media"
    storage_backend: Literal["local", "s3"] = "local"
    s3_bucket: str = ""
    s3_prefix: str = "ocr/"
    s3_endpoint_url: str = ""  # e.g. http://minio:9000 for a self-hosted S3
    s3_region: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""

    # App — nombre de marca; la doc OpenAPI usa "<app_name> API".
    app_name: str = "Ocrer"
    app_url: str = "http://localhost"

    # Observabilidad
    log_format: Literal["text", "json"] = "text"
    log_level: str = "INFO"
    metrics_token: str = ""  # si se fija, GET /metrics exige Bearer <token>
    worker_metrics_port: int = 0  # >0: el ocr-worker sirve /metrics en ese puerto
    # Swagger UI / ReDoc / openapi.json. Desactívalo en producción (DOCS_ENABLED=false).
    docs_enabled: bool = True

    # Account lockout (panel login) — 0 attempts disables it
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    # Admin seed
    admin_email: str = "admin@example.com"
    admin_password: str = "password"
    admin_name: str = "Admin"

    # Dashboard
    dashboard_recent_documents_limit: int = 10

    # Document registry (every OCR API call is recorded in the `documents` table)
    document_text_excerpt_chars: int = 500  # 0 -> store no text at all
    document_retention_days: int = 0  # 0 -> keep forever
    document_redact_pii: bool = False  # mask emails / IDs / IBANs in the stored excerpt

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
    ocr_engine: Literal["paddle", "fake", "tesseract"] = "paddle"
    ocr_lang: str = "es"
    ocr_use_gpu: bool = False
    ocr_pdf_dpi: int = 200
    tesseract_cmd: str = ""  # path to the tesseract binary; empty -> found on PATH
    ocr_lang_autodetect: bool = False  # when `lang` is omitted, detect it from the OCR text
    ocr_paddle_mkldnn: bool = False  # PaddlePaddle 3.x oneDNN CPU path (buggy on some CPUs)
    ocr_sync_max_bytes: int = 10_000_000
    ocr_sync_max_pages: int = 5
    ocr_max_upload_bytes: int = 52_428_800
    ocr_max_concurrency: int = 2
    ocr_worker_interval_seconds: float = 2.0
    ocr_model_dir: str = "/app/backend/.paddlex"

    # Input hardening
    ocr_max_image_megapixels: float = 40.0  # per rendered page / image frame
    ocr_allowed_langs: str = ""  # comma list; empty -> built-in PaddleOCR language set
    ocr_sort_reading_order: bool = True

    # Document classification (runs on the OCR text)
    ocr_classifier: Literal["none", "rules", "ml", "llm"] = "rules"
    ocr_classifier_min_score: float = 2.5  # min raw weight of matched signals
    ocr_classifier_min_confidence: float = 0.4  # min dominance of the top type

    # Field extraction (runs on the OCR text, keyed by doc_type)
    ocr_extractor: Literal["none", "rules", "llm"] = "rules"

    # Sync-endpoint result cache (content-hash keyed, in-process)
    ocr_sync_cache_ttl_seconds: int = 300  # 0 disables
    ocr_sync_cache_max_entries: int = 64

    # Job queue resilience
    ocr_job_max_attempts: int = 3
    ocr_job_stale_seconds: int = 900  # a "processing" job older than this is reclaimed

    # Retention / purge
    ocr_job_retention_days: int = 7
    ocr_purge_interval_seconds: float = 3600.0

    # Webhook callbacks
    ocr_callback_timeout_seconds: int = 10
    ocr_callback_allow_private: bool = False  # allow callbacks to private/loopback IPs
    ocr_callback_allowed_hosts: str = ""  # comma list; empty = any public host
    ocr_callback_signing_secret: str = ""  # empty -> falls back to secret_key
    ocr_callback_max_attempts: int = 5  # dead-letter after this many failed deliveries
    ocr_callback_backoff_base_seconds: int = 60  # retry after base * 2**(attempt-1)

    # Batch job submission
    ocr_batch_max_files: int = 50
    ocr_batch_max_total_bytes: int = 209_715_200  # 200 MiB — cap on a .zip's decompressed size

    # Per-client OCR quota (pages/month; 0 = unlimited unless the client overrides it)
    ocr_default_monthly_page_quota: int = 0

    # Model warmup
    ocr_warmup_on_startup: bool = True
    ocr_warmup_langs: str = ""  # comma list; empty -> [ocr_lang]

    def throttle(self, raw: str) -> tuple[int, int]:
        limit, per = raw.split("/", 1)
        return int(limit), int(per)

    @property
    def ocr_callback_allowed_hosts_list(self) -> list[str]:
        return [h.strip().lower() for h in self.ocr_callback_allowed_hosts.split(",") if h.strip()]

    @property
    def ocr_warmup_langs_list(self) -> list[str]:
        langs = [x.strip() for x in self.ocr_warmup_langs.split(",") if x.strip()]
        return langs or [self.ocr_lang]

    @property
    def ocr_allowed_langs_list(self) -> list[str]:
        return [x.strip() for x in self.ocr_allowed_langs.split(",") if x.strip()]

    @property
    def ocr_callback_secret(self) -> str:
        return self.ocr_callback_signing_secret or self.secret_key

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def ocr_storage_dir(self) -> str:
        return f"{self.media_dir.rstrip('/')}/ocr"

    def validate_secret_key(self) -> None:
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")

    def validate_cors(self) -> None:
        # "*" + credentials is a CSRF-style hole (Starlette echoes the Origin back).
        if "*" in self.cors_origins_list:
            raise ValueError(
                "CORS_ALLOWED_ORIGINS no puede contener '*' (se envían cookies). "
                "Lista los orígenes exactos, o déjalo vacío si el frontend es del mismo origen."
            )


settings = Settings()
settings.validate_secret_key()
settings.validate_cors()
