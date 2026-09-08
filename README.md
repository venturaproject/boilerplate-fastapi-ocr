# boilerplate-fastapi-ocr

An **OCR** API powered by [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), built on a
FastAPI + React boilerplate (cookie‑JWT auth, CQRS, outbox/inbox, Postgres, and an
**external API** layer with `client_id`/`client_secret` → Bearer + scopes).

Any external application can submit **images or PDFs** and get back the **recognized text** —
either **synchronously** (immediate response) or **asynchronously** (job queue + optional
webhook).

The domain is OCR-focused: **users / roles / permissions**, the **external API**
(`api_clients`), the **jobs** (`ocr_jobs`) and the **document registry** (`documents`).
The vertical-slice pattern (`app/domain/<x>/` + `app/repositories/<x>.py` +
`app/routers/<x>.py`) and the event infrastructure (CQRS · outbox · inbox) are left as
extension points.

## Features

- **Two OCR modes** — synchronous (`POST /api/ext/ocr`, immediate) or an asynchronous job
  queue with signed webhooks, dead-letter and redelivery.
- **Pluggable OCR engine** — PaddleOCR (default), Tesseract, or a deterministic `fake` stub
  for CI; automatic language detection.
- **Text-first PDFs** — digital PDFs are read straight from their embedded text layer
  (exact, no OCR); scanned pages fall back to rasterize + OCR, per page.
- **Output formats** — JSON, plain text, hOCR, ALTO v3 XML, or a **searchable PDF**
  (image + invisible text layer).
- **Document intelligence** — rule-based type classification (invoice, CV, payslip, contract…)
  + per-type field extraction (totals, dates, tax IDs, IBANs…), optional PII redaction.
- **External API** — `client_id`/`client_secret` → Bearer + scopes, per-client rate limits
  and monthly page quotas, secret rotation, usage metering (`client_usage`).
- **Document registry** — every call recorded in Postgres, survives the job retention purge.
- **Batteries included** — cookie-JWT admin panel (React 19 + shadcn/ui), RBAC, account
  lockout, audit log, CSRF, SSRF-guarded + IP-pinned callbacks.
- **Observability** — Prometheus `GET /metrics`, JSON logs, `X-Request-ID`, optional
  Grafana overlay with a provisioned dashboard.
- **Production build** — multi-stage nginx image that compiles the SPA and serves it +
  proxies the API; CQRS + outbox/inbox event infra as an extension point.

## Contents

- [Repository layout](#repository-layout)
- [Getting started](#getting-started)
- [Production](#production)
- [OCR engines](#ocr-engines)
- [External API authentication](#external-api-authentication)
- [Endpoints](#endpoints) — [sync](#synchronous-ocr) · [classify](#classification) ·
  [extraction](#field-extraction) · [async jobs](#asynchronous-jobs) · [batch](#batch) ·
  [webhooks](#webhook-verification) · [retries & retention](#retries-and-retention)
- [Document registry](#document-registry)
- [Quotas, metering & secret rotation](#quotas-metering-and-secret-rotation)
- [OCR configuration (`.env`)](#ocr-configuration-env)
- [Development](#development) — [code quality](#code-quality-backend) ·
  [architecture](#ocr-architecture) · [readiness](#readiness)
- [Observability](#observability)
- [Security](#security)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)

## Repository layout

**Monorepo** — a single git repo:

```
boilerplate-fastapi-ocr/
├── backend/            FastAPI + PaddleOCR + Alembic  (has its own .env.example for running standalone)
├── frontend/           React 19 + Vite + shadcn/ui
├── infrastructure/     Dockerfiles, nginx, prometheus, grafana
├── compose.dev.yml     development stack (hot-reload)
├── compose.yml         production stack
├── compose.observability.yml   optional Prometheus + Grafana overlay
├── Makefile            shortcuts (uses compose.dev.yml)
└── .env.example        configuration (copy to .env)
```

## Getting started

**Requirements**: Docker + Docker Compose. Nothing else — Python, Node and pnpm live in the
containers.

```bash
git clone https://github.com/venturaproject/boilerplate-fastapi-ocr.git
cd boilerplate-fastapi-ocr

cp .env.example .env          # set SECRET_KEY (≥32 chars), credentials, ports…
make build
make up                       # postgres · backend · ocr-worker · frontend (Vite) · nginx · event worker
make migrate && make seed     # creates tables, permissions, the admin user and a sample API client ("ocr-demo")
```

Ready at `http://localhost:8087` (port configurable with `NGINX_PORT`):

| | URL | Credentials |
|---|---|---|
| Admin panel | `http://localhost:8087/admin` | `admin@example.com` / `password` (from `.env`) |
| API + Swagger | `http://localhost:8087/api/docs` | — |

`make seed` prints the `client_id` / `client_secret` of the `ocr-demo` client so you can try
the external API. The `Makefile` uses **`compose.dev.yml`** (hot-reload, Vite dev server);
`make help` lists every shortcut.

## Production

`compose.yml`:

```bash
docker compose -f compose.yml up -d --build
docker compose -f compose.yml exec backend uv run alembic upgrade head
docker compose -f compose.yml exec backend uv run python seed.py
```

Differences from dev: **there is no `frontend` service** — the `nginx` image is multi-stage
(`infrastructure/nginx/Dockerfile`): it builds the SPA (`pnpm build`) and serves the static
bundle + proxies the API. Set `DOCS_ENABLED=false` in `.env`. The app name is served at
runtime (`GET /api/v1/config`), so you don't rebuild the frontend to change it.

- API + docs (auto-generated OpenAPI 3.1): Swagger UI `http://localhost:8087/api/docs` ·
  ReDoc `/api/redoc` · spec `/api/openapi.json`. The spec declares the two auth schemes
  (`ExternalBearer` for `/api/ext/*`, `SessionCookie` for the panel), so Swagger's
  **Authorize** button works. The backend env var **`DOCS_ENABLED=false`** disables all
  three routes (`404`) — set it that way in production, whatever the deployment (uvicorn,
  systemd, k8s, Docker).
- The `/admin` panel → **OCR** menu (playground · Jobs · Documents); the dashboard shows OCR
  metrics (by document type, by mode, latency, activity).

## OCR engines

Selected with `OCR_ENGINE`:

| value | engine | notes |
|---|---|---|
| `paddle` *(default)* | **PaddleOCR** (pinned to 2.x; `engine.py` already supports the 3.x API) | best accuracy; `paddlepaddle` ≈ 1 GB, installed in the image |
| `tesseract` | **Tesseract** (`pytesseract` + binary) | lightweight alternative; needs the image's language packs |
| `fake` | deterministic stub | tests / CI / dev without heavy deps |

> On Apple Silicon, if `paddlepaddle` has no wheel for your platform, use `OCR_ENGINE=fake`
> (or `tesseract`), or run the service on an x86_64 host. The `engine.py` wrapper already
> speaks the 3.x API (PP‑OCRv5) but the **pin stays on 2.x**: paddle 3.x segfaults / raises
> an unimplemented op (oneDNN+PIR) on CPU under emulation. Bumping the pin to `>=3` and
> verifying it on x86 CI is the pending step (`OCR_PADDLE_MKLDNN` is the toggle).

**Automatic language detection**: with `OCR_LANG_AUTODETECT=true`, if the request doesn't set
`lang`, it's detected from the text (es/en/fr/de/pt heuristic) and OCR re-runs once with the
detected language; the response sets `lang_detected: true`.

## External API authentication

```bash
# 1. Get an access token
curl -X POST http://localhost:8087/api/ext/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"client_id":"cli_…","client_secret":"…"}'
# → { "access_token": "…", "refresh_token": "…", "expires_in": 900, "scopes": ["ocr:write","ocr:read"] }
```

Scopes: `ocr:write` (submit), `ocr:read` (query).

## Endpoints

### Synchronous OCR

`POST /api/ext/ocr` — scope `ocr:write`.

```bash
curl -X POST http://localhost:8087/api/ext/ocr \
  -H "Authorization: Bearer $TOKEN" \
  -F file=@invoice.png \
  -F lang=es
```

```jsonc
{
  "engine": "paddleocr",
  "lang": "es",
  "page_count": 1,
  "pages": [
    {
      "page": 1, "width": 1240, "height": 1754,
      "lines": [
        { "text": "INVOICE", "confidence": 0.998, "box": [[100,80],[260,80],[260,120],[100,120]] }
      ],
      "text": "INVOICE\n…"
    }
  ],
  "text": "INVOICE\n…",
  "processing_ms": 842,
  "cached": false
}
```

- **PDFs** — a page with a real text layer (digital PDF) is read straight from it: exact
  text, `confidence: 1.0`, no OCR. Pages with little/no text (scanned) are rasterized and
  OCR'd. `engine` in the response reads `pdf-text`, or `<engine>+pdf-text` for a mixed
  document. Disable with `OCR_PDF_TEXT_LAYER=false`; the threshold is
  `OCR_PDF_TEXT_MIN_CHARS`.
- **Output format** with `?format=` — `json` (default) · `text` · `hocr` · `alto` · `pdf`
  (searchable PDF = image + invisible text layer). Also on
  `GET /api/ext/ocr/jobs/{id}?format=` (the `pdf` re-reads the original via the storage
  backend).
- Lines are returned in **reading order** (rows by `y`, each row left to right; disable with
  `OCR_SORT_READING_ORDER=false`).
- Identical results (same content + language) are served from a **cache** (`cached: true`)
  for `OCR_SYNC_CACHE_TTL_SECONDS`.
- Includes `classification` and `extraction` (see below).
- Invalid `lang` → `422`. Limits: `OCR_SYNC_MAX_BYTES` (10 MB), `OCR_SYNC_MAX_PAGES` (5),
  `OCR_MAX_IMAGE_MEGAPIXELS` (40, anti-bomb). For more, use jobs.

### Classification

`POST /api/ext/ocr/classify` — scope `ocr:write`.

Recognizes the type from the OCR text (keyword rules, no dependencies or training):
`invoice`, `cv`, `payslip`, `contract`, `id_document`, `bank_statement`, `delivery_note`, `receipt`.

```bash
curl -X POST http://localhost:8087/api/ext/ocr/classify \
  -H "Authorization: Bearer $TOKEN" -F file=@invoice.pdf
# → { "doc_type": "invoice", "confidence": 0.86,
#     "scores": {"invoice": 0.86, "receipt": 0.14},
#     "lang": "es", "page_count": 1, "text_excerpt": "INVOICE No …",
#     "extraction": { "doc_type": "invoice",
#       "fields": { "total": {"value": "121.00", ...}, "tax_id": {...}, "date": {...} } } }
```

`doc_type` is `null` if no class beats `OCR_CLASSIFIER_MIN_SCORE` /
`OCR_CLASSIFIER_MIN_CONFIDENCE`. The same `classification` travels in the `/api/ext/ocr`
response and is stored as `doc_type` on jobs (filterable via `/jobs?doc_type=…`, aggregated
in `/stats.by_doc_type`). Backends: `OCR_CLASSIFIER=rules` (default) · `none` · `ml`
(`joblib` model trained with `scripts/train_classifier.py`, extra `ml`) · `llm` (interface +
stub, no provider).

### Field extraction

After classification, `OCR_EXTRACTOR=rules` (default; `none` / `llm` available) extracts
structured fields per type — invoice: `total`, `date`, `tax_id`, `invoice_number`; payslip:
`net_pay`, `gross_pay`, `period`; bank statement: `iban`, `closing_balance`; ID card:
`document_number`, `birth_date`… It travels as `extraction` in the `/api/ext/ocr` and
`/classify` responses, and is stored in `documents.extraction`. Each field carries `value` +
`raw`.

With `DOCUMENT_REDACT_PII=true` the stored excerpt (`documents.text_excerpt` and the one from
`/classify`) masks email / national ID / IBAN / phone / card numbers.

### Asynchronous jobs

`POST /api/ext/ocr/jobs` — scope `ocr:write`.

```bash
curl -X POST http://localhost:8087/api/ext/ocr/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -F file=@document.pdf \
  -F lang=es \
  -F callback_url=https://my-app.example/webhooks/ocr
# → 202  { "id": "…", "status": "pending", … }
```

- `202` includes the header `Location: /api/ext/ocr/jobs/{id}`.
- `GET /api/ext/ocr/jobs/{id}` — status + full `result` once `status = "done"`.
- `GET /api/ext/ocr/jobs` — paginated list **without** `result` (metadata only; the
  authenticated client's jobs). Params: `page`, `per_page` (max 100), `status`, `doc_type`,
  `search`, `callback` (`failed` | `pending`), `batch_id`.
- `GET /api/ext/ocr/stats` — counters per status, age of the oldest pending job, mean/p95 latency.
- If `callback_url` was given, the worker sends a signed `POST` with the same body as
  `GET .../jobs/{id}`.

### Batch

`POST /api/ext/ocr/jobs:batch` — scope `ocr:write`.

Several `files` in one multipart (or **a single `.zip`**) → N jobs sharing a `batch_id`
(max `OCR_BATCH_MAX_FILES`). `GET /api/ext/ocr/batches/{batch_id}` returns the per-status
breakdown and the job list.
- Send an `Idempotency-Key` header so a network retry doesn't create a duplicate job (the
  original response is replayed; see `app/idempotency/`).
- A `429` includes `Retry-After` (seconds). Default rate limit `THROTTLE_OCR` (`30/60`), with
  a per-client override (see [Quotas & metering](#quotas-metering-and-secret-rotation)).

### Webhook verification

Every callback `POST` (to the job's `callback_url`) carries `X-OCR-Timestamp` and
`X-OCR-Signature` headers:

```
signature = "sha256=" + hmac_sha256(OCR_CALLBACK_SIGNING_SECRET, f"{X-OCR-Timestamp}." + raw_body)
```

Compare with `hmac.compare_digest` and reject stale timestamps. `callback_url` is validated
against SSRF (private/loopback/link-local IPs are rejected and, if `OCR_CALLBACK_ALLOWED_HOSTS`
is set, hosts outside the list). Redirects are not followed; the request is pinned to the IP
that was vetted (closes DNS rebinding).

### Retries and retention

- A failed job is retried up to `OCR_JOB_MAX_ATTEMPTS` times; if the worker dies mid-way,
  another picks it up after `OCR_JOB_STALE_SECONDS`.
- **Webhook dead-letter**: a failed callback is retried with backoff
  (`OCR_CALLBACK_BACKOFF_BASE_SECONDS * 2**n`) up to `OCR_CALLBACK_MAX_ATTEMPTS` and then
  dead-lettered (`next_callback_at = null`). `POST .../jobs/{id}/redeliver` (scope
  `ocr:write`) re-queues it; status lives in `callback_status` / `callback_attempts`.
- Finished jobs are deleted (with their files) after `OCR_JOB_RETENTION_DAYS` — automatic in
  the worker every `OCR_PURGE_INTERVAL_SECONDS`, or manual with `make purge-ocr`.
- On startup, backend and worker preload the models (`OCR_WARMUP_LANGS`), so the first
  request doesn't wait for the download/load.

## Document registry

**Every** call to the OCR API is recorded in the `documents` table — one row per request,
with a `mode`:

| `mode` | Source | `status` |
|---|---|---|
| `sync` | `POST /api/ext/ocr` | always `done` (on failure it returns an error and nothing is stored) |
| `classify` | `POST /api/ext/ocr/classify` | always `done` |
| `async` | `POST /api/ext/ocr/jobs` | `pending` → `done` / `error` (updated by the worker) |

Each row stores metadata (`original_filename`, `content_type`, `size_bytes`, `lang`,
`page_count`, `processing_ms`), the detected document type (`doc_type`,
`doc_type_confidence`), the recognized character count (`char_count`) and a **text excerpt**
(`text_excerpt`, first `DOCUMENT_TEXT_EXCERPT_CHARS` chars; `0` = store no text). `async` rows
link to their `ocr_jobs.id` (`ocr_job_id`); that link is `SET NULL`, so the registry
**survives the jobs' retention purge**.

- The registry can never break an OCR response: it's written in its own transaction and any
  error is only logged.
- `record_document` does not store the full OCR result (that lives in `ocr_jobs.result` until
  the job is purged) — only the excerpt.

### Panel — `/api/v1/documents` *(permission `documents.view`)*

Authenticated with the cookie‑JWT (not the external API Bearer):

- `GET /api/v1/documents` — paginated list; filters `mode`, `doc_type`, `status`, `search`
  (filename).
- `GET /api/v1/documents/{id}` — one row.
- `GET /api/v1/documents/stats` — totals, `by_mode` / `by_status` / `by_doc_type` breakdown,
  documents in the last 24 h, mean/p95 latency.
- `DELETE /api/v1/documents/{id}` — deletes the record (permission `documents.delete`); the
  associated OCR job is not affected.

In the panel: **OCR → Documents** menu.

Optional own retention: `DOCUMENT_RETENTION_DAYS` (0 = keep forever); the purge runs in the
OCR worker alongside the jobs purge.

## Quotas, metering and secret rotation

Every OCR call is metered per `api_client` in the `client_usage` table (one row per month
`YYYY-MM`: `pages` and `requests`). It's incremented on the sync endpoint, on `classify`,
when an async job is created and when it's processed.

- **Per-client limits** (optional, override the global default):
  - `rate_limit` — `«n/seconds»` format (e.g. `120/60`); if `null`, `THROTTLE_OCR` is used.
  - `monthly_page_quota` — monthly page cap; `null`/`0` = `OCR_DEFAULT_MONTHLY_PAGE_QUOTA`
    (0 = unlimited). Once exhausted, `ocr:write` endpoints return `429` with a quota `detail`;
    `ocr:read` keeps working.
- **Headers** on every OCR response: `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
  `X-RateLimit-Reset`; on quota'd writes, also `X-Quota-Limit` and `X-Quota-Remaining`. The
  `429` keeps `Retry-After`.
- `GET /api/ext/ocr/usage` *(scope `ocr:read`)* — current-month usage + the authenticated
  client's effective quota and rate limit.

### Panel *(permission `api_clients.manage`)*

- `PATCH /api/v1/api-clients/{id}` — sets `rate_limit` / `monthly_page_quota` (malformed
  `rate_limit` → `422`).
- `GET /api/v1/api-clients/{id}/usage` — same breakdown as `/usage` but for any client.
- `POST /api/v1/api-clients/{id}/rotate` — generates a new secret (shown **once**) and
  invalidates the previous secret and all its access tokens.

In the panel: **Users → API Clients** ("Limits & usage" column, edit limits, "Rotate secret").

## OCR configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `STORAGE_BACKEND` | `local` | `local` (volume) or `s3` (`S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`) |
| `OCR_ENGINE` | `paddle` | `paddle` · `tesseract` · `fake` |
| `OCR_LANG` | `es` | default language |
| `OCR_LANG_AUTODETECT` | `false` | if `lang` is omitted, detect it from the text and re-run |
| `TESSERACT_CMD` | *(empty)* | path to the `tesseract` binary (empty = on PATH) |
| `OCR_USE_GPU` | `false` | use GPU (requires `paddlepaddle-gpu`) |
| `OCR_MODEL_DIR` | `/app/backend/.paddlex` | PaddleOCR/PaddleX model cache |
| `OCR_PDF_DPI` | `200` | DPI when rasterizing PDF pages that need OCR |
| `OCR_PDF_TEXT_LAYER` | `true` | read the embedded text layer of digital PDFs instead of OCR'ing a render |
| `OCR_PDF_TEXT_MIN_CHARS` | `16` | a PDF page with less real text than this is treated as scanned |
| `OCR_SYNC_MAX_BYTES` / `OCR_SYNC_MAX_PAGES` | `10000000` / `5` | sync endpoint limits |
| `OCR_MAX_UPLOAD_BYTES` | `52428800` | upload limit for jobs |
| `OCR_MAX_IMAGE_MEGAPIXELS` | `40` | pixel cap per page/image (anti-bomb) |
| `OCR_MAX_CONCURRENCY` | `2` | concurrent OCR inferences (per process) |
| `OCR_ALLOWED_LANGS` | *(empty)* | allowed languages; empty = PaddleOCR's native set |
| `OCR_SORT_READING_ORDER` | `true` | sort lines by reading order |
| `OCR_CLASSIFIER` | `rules` | document type: `rules` · `none` · `ml` · `llm` |
| `OCR_CLASSIFIER_MIN_SCORE` / `OCR_CLASSIFIER_MIN_CONFIDENCE` | `2.5` / `0.4` | thresholds to assign a type |
| `OCR_EXTRACTOR` | `rules` | per-type field extraction: `rules` · `none` · `llm` |
| `DOCUMENT_REDACT_PII` | `false` | mask email/ID/IBAN/phone/card in the stored excerpt |
| `DOCUMENT_TEXT_EXCERPT_CHARS` | `500` | chars of OCR text stored in `documents.text_excerpt` (`0` = none) |
| `DOCUMENT_RETENTION_DAYS` | `0` | age to purge `documents` rows (`0` = keep forever) |
| `OCR_SYNC_CACHE_TTL_SECONDS` / `OCR_SYNC_CACHE_MAX_ENTRIES` | `300` / `64` | sync endpoint cache (0 = off) |
| `OCR_WORKER_INTERVAL_SECONDS` | `2` | worker poll frequency |
| `OCR_JOB_MAX_ATTEMPTS` | `3` | retries before marking a job `error` |
| `OCR_JOB_STALE_SECONDS` | `900` | age to re-queue a stuck `processing` job |
| `OCR_JOB_RETENTION_DAYS` | `7` | age to purge finished jobs |
| `OCR_PURGE_INTERVAL_SECONDS` | `3600` | purge frequency in the worker |
| `OCR_WARMUP_ON_STARTUP` / `OCR_WARMUP_LANGS` | `true` / `OCR_LANG` | model preload on startup |
| `OCR_CALLBACK_TIMEOUT_SECONDS` | `10` | webhook timeout |
| `OCR_CALLBACK_ALLOW_PRIVATE` | `false` | allow callbacks to private IPs (internal only) |
| `OCR_CALLBACK_ALLOWED_HOSTS` | *(empty)* | host allowlist for `callback_url` |
| `OCR_CALLBACK_SIGNING_SECRET` | *(→ `SECRET_KEY`)* | HMAC secret to sign the webhook |
| `THROTTLE_OCR` | `30/60` | rate limit for the OCR endpoints (default; overridden by `api_client.rate_limit`) |
| `OCR_DEFAULT_MONTHLY_PAGE_QUOTA` | `0` | default monthly page quota (`0` = unlimited; overridden by `api_client.monthly_page_quota`) |

## Development

### Code quality (backend)

| Command | What it does |
|---|---|
| `make format-backend` | `ruff format` — apply formatting |
| `make lint-backend` | `ruff format --check` + `ruff check` — verify, no changes |
| `make lint-backend-fix` | formatting + lint autofix |
| `make type-check-backend` | strict `mypy` over `app/` |
| `make check-backend` | format + lint + types + tests (the CI gate) |

`mypy` runs with `disallow_untyped_defs`, `disallow_incomplete_defs`, `strict_equality`,
`warn_unreachable`, `check_untyped_defs` and `extra_checks`; config in `backend/pyproject.toml`.

```bash
make check-backend       # full backend gate
make test-backend        # pytest (uses OCR_ENGINE=fake automatically)
make format-backend      # apply formatting
make process-ocr         # process a batch of pending jobs and exit
make purge-ocr           # purge expired jobs and their files
make logs-ocr-worker
```

All backend config is read by `app/config.py::Settings` (pydantic-settings) from the
environment or `.env`. To run the backend **without Docker** there's a dedicated template
with local commands and values: `backend/.env.example` (and `frontend/.env.example` for the
frontend).

**Frontend runtime config**: `GET /api/v1/config` (public) returns the SPA's public config
(today `app_name`, derived from `APP_NAME`). The frontend reads it on boot
(`src/app.tsx` → `applyRuntimeConfig`); the `VITE_*` vars are only a build-time fallback. So
the app name changes in the backend `.env`, with no frontend rebuild.

### OCR architecture

- `app/services/ocr/` — `loader.py` (image/PDF → pages), `engine.py` (`PaddleOcrEngine` /
  `FakeOcrEngine` + `warmup`), `service.py` (inference off the event loop), `jobs.py` (shared
  logic), `callback.py` (signed webhook + SSRF guard), `storage.py`.
- `app/models/ocr_job.py` + `app/repositories/ocr_job.py` — `ocr_jobs` table (claim/reclaim/purge).
- `app/models/document.py` + `app/repositories/document.py` + `app/domain/document/` +
  `app/routers/documents.py` — `documents` table (registry of everything the API processed).
- `app/routers/ext_ocr.py` (external API) and `app/routers/ocr.py` (panel).
- `app/models/api_client.py` (`ApiClient` + `ClientUsage`) + `app/repositories/client_usage.py` —
  quotas and metering; `app/dependencies.py::require_ocr` applies scope + rate limit + quota.
- `app/ocr/worker.py` + `app/ocr/processor.py` — queue worker (`ocr-worker` service): reclaim
  stuck jobs → claim → OCR → callback → retention purge.
- `app/services/ocr/langs.py` (language validation), `cache.py` (sync cache), `classifier.py`
  (rule-based document type; pluggable for ML/LLM later).

### Readiness

- `GET /api/v1/ocr/ready` → `200` when at least one model is loaded, `503` while warming up
  (useful as a *readiness probe*). `GET /api/health` includes the same state in `ocr.ready`.

## Observability

- **`GET /metrics`** — Prometheus format. Metrics: `ocr_requests_total{mode,engine,status}`,
  `ocr_processing_ms` (histogram), `ocr_cache_events_total{event}`, `ocr_engine_errors_total`,
  `ocr_callback_total{status}`, `ocr_queue_depth{status}` (sampled at scrape time),
  `http_requests_total` / `http_request_duration_seconds`. No auth unless you set
  `METRICS_TOKEN` (then it requires `Authorization: Bearer <token>`).
- **Logs** — one line per event; `LOG_FORMAT=json` emits them as a JSON object with
  `request_id`. `LOG_LEVEL` sets the level.
- **`X-Request-ID`** — the middleware generates one (or propagates the incoming one) and
  returns it in the response; it shows up in every log for that request.
- The **`ocr-worker`** serves its own `/metrics` when `WORKER_METRICS_PORT` > 0 (the overlay
  sets it).

### Prometheus + Grafana panel (optional overlay)

None of this is needed to run the app — in a real deployment your Prometheus scrapes
`backend:8000/metrics` directly.

```bash
make observability        # = compose -f compose.dev.yml -f compose.observability.yml up -d
make observability-down    # stop the panel (data kept)
```

| | URL | Access |
|---|---|---|
| **Grafana** | http://localhost:3001 | anonymous = *Viewer* (no login); to edit: `admin` / `${GRAFANA_PASSWORD:-admin}` |
| **Prometheus** | http://localhost:9090 | — |

- **Grafana** → *Dashboards → "Ocrer — OCR overview"** (direct: `http://localhost:3001/d/ocrer-overview`).
  It's provisioned already; adjust the time range top-right (30 s refresh).
- **Prometheus** → *Status → Target health*: `ocrer-backend` and `ocrer-worker` should be `UP`.
  In *Graph* you can try PromQL:
  ```promql
  sum by (mode,status) (rate(ocr_requests_total[5m]))
  histogram_quantile(0.95, sum by (le,mode) (rate(ocr_processing_ms_bucket[5m])))
  ocr_queue_depth
  ```
- On a quiet dev box the panels stay flat until you send traffic (`bash scratchpad/api_smoke.sh`,
  the `/admin/ocr` playground, or just browsing the admin). "Cache hit-rate 0%" and
  "Callbacks — No data" are normal if you don't resend documents or use `callback_url`.
- Ports configurable with `GRAFANA_PORT` / `PROMETHEUS_PORT`.

## Security

Covered out of the box:

- **Auth**: bcrypt passwords; signed panel JWT (validates `iss`/`aud`/`exp`/`token_type`),
  `httponly` + `SameSite` + `Secure` (prod) cookies. **Account lockout** after
  `LOGIN_MAX_ATTEMPTS` failures for `LOGIN_LOCKOUT_MINUTES`.
- **CSRF**: signed token required on the panel's mutating methods; skipped on `/api/ext/*`
  (Bearer isn't CSRF-able).
- **External API**: tokens and secrets stored only as SHA-256 hashes; constant-time
  `verify_secret`; refresh with rotation + `SELECT … FOR UPDATE`; `rotate` invalidates
  everything.
- **Callback SSRF**: scheme/host allowlist, private/reserved IP blocking, no redirects, and
  **the request is pinned to the vetted IP** (`_PinnedTransport`) → closes DNS rebinding.
  Webhook signed with HMAC-SHA256 + timestamp.
- **Input**: `Content-Length` + size guards, MIME allowlist, megapixel anti-bomb cap, and for
  batch `.zip`s: per-entry, total and compression-ratio caps.
- **Rate limit / quotas** per user / client / real IP (uvicorn `--proxy-headers`).
- **HTTP headers** in nginx: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`,
  `Permissions-Policy`, `CSP` and `HSTS` (prod); `server_tokens off`.
- **Audit log**: `audit_events` records logins (ok/fail/lock), user/role changes and API
  client lifecycle. `GET /api/v1/audit` (permission `audit.view`).
- **OpenAPI** disableable in prod (`DOCS_ENABLED=false`); `CORS_ALLOWED_ORIGINS` rejects `*`.

Left to the deployment:

- **TLS** is terminated in front (LB / ingress / nginx with a cert). `compose.yml`'s `nginx`
  listens on `:80`; put HTTPS in front and the `HSTS` it already emits makes sense.
- No 2FA. No configurable password policy. No multi-key `SECRET_KEY` rotation.
- Network *egress* policy is still the backstop for callbacks in hostile environments.

## Known limitations

- **Default on-disk storage**: `STORAGE_BACKEND=local` shares the `media_data` volume between
  backend and worker. For multi-node, `STORAGE_BACKEND=s3` (extra `s3`).
- **Callback dead-letter without re-alerts**: after `OCR_CALLBACK_MAX_ATTEMPTS` the job is
  flagged but nobody is notified — you must query it (`?callback=failed`) or re-queue it with
  `redeliver`.
- **paddleocr pinned to 2.x**: `engine.py` already supports the 3.x API, but paddle 3.x fails
  on CPU under emulation; bumping the pin and verifying on x86 CI is the pending step.
- **`OCR_MAX_CONCURRENCY` is per process**: with N worker replicas the real parallelism is
  N × that value. A global cap would need a semaphore in Redis/DB.
- **Rate limit and quota are per-process / fixed-window in DB**: the rate-limit counter is a
  fixed window (`rate_limit_counters`); the monthly quota is counted by `page_count` and is
  not billed when OCR fails before pages are counted (intended behavior).

## Roadmap

Ordered by value/effort:

1. *(done)* **Per-type field extraction** (`OCR_EXTRACTOR=rules`) — an `llm` backend with a
   real provider is missing.
2. *(done)* **Pluggable storage** `STORAGE_BACKEND=local|s3` — `S3Storage` (boto3, extra
   `s3`) decouples the worker from the shared disk.
3. *(done)* **Observability** — `GET /metrics` Prometheus + per-line logs (`LOG_FORMAT=json`)
   + `X-Request-ID`. Optional Prometheus/Grafana overlay.
4. *(done)* **Callback dead-letter** — backoff + `redeliver` + `?callback=` filter.
5. *(done)* **Per-client quotas & metering** — `rate_limit` and `monthly_page_quota` per
   `api_client`, `client_usage` table, `GET /usage`, `X-Quota-*` headers.
6. *(done)* **Output formats** `?format=text|hocr|alto|pdf` (a job's `pdf` re-reads the
   original via the storage backend).
7. *(done)* **Tesseract engine** (`OCR_ENGINE=tesseract`); a cloud-OCR adapter behind the
   same `OcrEngine` interface is still open.
8. *(done)* **Automatic language detection** (`OCR_LANG_AUTODETECT`).
9. *(done)* **PII redaction** (`DOCUMENT_REDACT_PII`).
10. *(done)* **Batch endpoint** `POST /jobs:batch` + `GET /batches/{id}`.
11. *(done)* **`api_client` secret rotation** (`POST .../rotate`) and `X-RateLimit-*` headers
    on every OCR response.
12. *(partial)* **ML/LLM classifier** — `OCR_CLASSIFIER=ml` (TF‑IDF +
    `scripts/train_classifier.py`) and `llm` (interface + stub) exist; a real LLM provider is
    missing.
13. *(blocked)* **`paddleocr` 3.x / PP‑OCRv5** — wrapper ready; bump the pin and verify on
    x86 CI (3.x breaks on CPU under emulation).
14. *(done)* **Text-first PDFs** (`OCR_PDF_TEXT_LAYER`) — read the embedded text layer of
    digital PDFs, OCR only scanned pages; hybrid per-page.
