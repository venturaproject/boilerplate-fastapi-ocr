# boilerplate-fastapi-ocr

API de **OCR** basada en [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), construida
sobre el boilerplate FastAPI + React (auth cookie‑JWT, CQRS, outbox/inbox, Postgres, y una
capa de **API externa** con `client_id`/`client_secret` → Bearer + scopes).

Cualquier aplicación externa puede enviar **imágenes o PDFs** y recibir el **texto
reconocido** — de forma **síncrona** (respuesta inmediata) o **asíncrona** (cola de
trabajos + webhook opcional).

El dominio se centra en el OCR: **usuarios / roles / permisos**, la **API externa**
(`api_clients`), los **trabajos** (`ocr_jobs`) y el **registro de documentos** (`documents`).
El patrón vertical-slice (`app/domain/<x>/` + `app/repositories/<x>.py` +
`app/routers/<x>.py`) y la infraestructura de eventos (CQRS · outbox · inbox) quedan como
puntos de extensión.

### Estructura del repositorio

`backend/` y `frontend/` son **repositorios git independientes** (rama `main` cada uno). Este
repo raíz versiona solo la capa de infraestructura: `infrastructure/`, `compose*.yml`,
`Makefile`, `README.md`, `.env.example`.

## Puesta en marcha

```bash
cp .env.example .env          # ajusta SECRET_KEY, credenciales, puertos…
make build
make up                       # postgres · backend · ocr-worker · frontend (Vite) · nginx · worker de eventos
make migrate && make seed     # crea tablas, permisos y un API client de ejemplo ("ocr-demo")
```

El `Makefile` y `make` usan **`compose.dev.yml`** (hot-reload, Vite dev server).

### Producción — `compose.yml`

```bash
docker compose -f compose.yml up -d --build
docker compose -f compose.yml exec backend uv run alembic upgrade head
docker compose -f compose.yml exec backend uv run python seed.py
```

Diferencias con dev: **no hay servicio `frontend`** — la imagen de `nginx` es multi-stage
(`infrastructure/nginx/Dockerfile`): compila la SPA (`pnpm build`) y sirve el bundle
estático + hace de proxy a la API. `DOCS_ENABLED` por defecto lo pones a `false` en el
`.env`. El nombre de la app se sirve en runtime (`GET /api/v1/config`), así que no hay
que reconstruir el frontend para cambiarlo.

- API + docs (OpenAPI 3.1 autogenerado): Swagger UI `http://localhost:8087/api/docs` ·
  ReDoc `/api/redoc` · spec `/api/openapi.json`. El spec declara los dos esquemas de
  auth (`ExternalBearer` para `/api/ext/*`, `SessionCookie` para el panel), así que el
  botón **Authorize** de Swagger funciona. La variable de entorno del backend
  **`DOCS_ENABLED=false`** desactiva las tres rutas (`404`) — ponla así en el entorno de
  producción, sea cual sea el despliegue (uvicorn, systemd, k8s, Docker).
- Panel: `http://localhost:8087/admin` → menú **OCR** (playground · Trabajos · Documentos).
  El dashboard muestra métricas de OCR (por tipo de documento, por modo, latencia, actividad).
- `make seed` imprime el `client_id` / `client_secret` del cliente `ocr-demo`.

### Motores OCR (`OCR_ENGINE`)

| valor | motor | notas |
|---|---|---|
| `paddle` *(def.)* | **PaddleOCR** (pin en 2.x; `engine.py` ya soporta la API 3.x) | mejor precisión; `paddlepaddle` ≈ 1 GB, se instala en la imagen |
| `tesseract` | **Tesseract** (`pytesseract` + binario) | alternativa ligera; requiere los language packs de la imagen |
| `fake` | stub determinista | tests / CI / dev sin dependencias pesadas |

> En Apple Silicon, si `paddlepaddle` no tiene wheel para tu plataforma, usa
> `OCR_ENGINE=fake` (o `tesseract`), o ejecuta el servicio en un host x86_64. El wrapper
> de `engine.py` ya habla la API 3.x (PP‑OCRv5) pero el **pin sigue en 2.x**: paddle 3.x
> hace *segfault* / op no implementada (oneDNN+PIR) en CPU bajo emulación. Subir el pin a
> `>=3` y verificarlo en CI x86 es el paso pendiente (`OCR_PADDLE_MKLDNN` da el toggle).

**Detección automática de idioma**: con `OCR_LANG_AUTODETECT=true`, si la petición no
fija `lang`, se detecta del texto (heurística es/en/fr/de/pt) y se reejecuta una vez con
el idioma detectado; la respuesta marca `lang_detected: true`.

## Autenticación de la API externa

```bash
# 1. Obtener un token de acceso
curl -X POST http://localhost:8087/api/ext/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"client_id":"cli_…","client_secret":"…"}'
# → { "access_token": "…", "refresh_token": "…", "expires_in": 900, "scopes": ["ocr:write","ocr:read"] }
```

Scopes: `ocr:write` (enviar), `ocr:read` (consultar).

## Endpoints

### Síncrono — `POST /api/ext/ocr`  *(scope `ocr:write`)*

```bash
curl -X POST http://localhost:8087/api/ext/ocr \
  -H "Authorization: Bearer $TOKEN" \
  -F file=@factura.png \
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
        { "text": "FACTURA", "confidence": 0.998, "box": [[100,80],[260,80],[260,120],[100,120]] }
      ],
      "text": "FACTURA\n…"
    }
  ],
  "text": "FACTURA\n…",
  "processing_ms": 842,
  "cached": false
}
```

- **Formato de salida** con `?format=` — `json` (por defecto) · `text` · `hocr` · `alto` ·
  `pdf` (PDF buscable = imagen + capa de texto invisible). También en
  `GET /api/ext/ocr/jobs/{id}?format=` (el `pdf` re-lee el original vía el storage).
- Las líneas salen en **orden de lectura** (filas por `y`, cada fila de izquierda a
  derecha; desactivable con `OCR_SORT_READING_ORDER=false`).
- Resultados idénticos (mismo contenido + idioma) se sirven de **caché**
  (`cached: true`) durante `OCR_SYNC_CACHE_TTL_SECONDS`.
- Incluye `classification` y `extraction` (ver abajo).
- `lang` inválido → `422`. Límites: `OCR_SYNC_MAX_BYTES` (10 MB),
  `OCR_SYNC_MAX_PAGES` (5), `OCR_MAX_IMAGE_MEGAPIXELS` (40, anti-bomba). Para más, usa los jobs.

### Clasificación de documento — `POST /api/ext/ocr/classify`  *(scope `ocr:write`)*

Reconoce el tipo a partir del texto OCR (reglas de keywords, sin dependencias ni entrenamiento):
`invoice`, `cv`, `payslip`, `contract`, `id_document`, `bank_statement`, `delivery_note`, `receipt`.

```bash
curl -X POST http://localhost:8087/api/ext/ocr/classify \
  -H "Authorization: Bearer $TOKEN" -F file=@factura.pdf
# → { "doc_type": "invoice", "confidence": 0.86,
#     "scores": {"invoice": 0.86, "receipt": 0.14},
#     "lang": "es", "page_count": 1, "text_excerpt": "FACTURA Nº …",
#     "extraction": { "doc_type": "invoice",
#       "fields": { "total": {"value": "121,00", ...}, "tax_id": {...}, "date": {...} } } }
```

`doc_type` es `null` si ninguna clase supera `OCR_CLASSIFIER_MIN_SCORE` /
`OCR_CLASSIFIER_MIN_CONFIDENCE`. El mismo `classification` viaja en la respuesta de
`/api/ext/ocr` y se guarda como `doc_type` en los jobs (filtrable en `/jobs?doc_type=…`,
agregado en `/stats.by_doc_type`). Backends: `OCR_CLASSIFIER=rules` (por defecto) ·
`none` · `ml` (modelo `joblib` entrenado con `scripts/train_classifier.py`, extra `ml`) ·
`llm` (interfaz + stub, sin proveedor).

### Extracción de campos

Tras clasificar, `OCR_EXTRACTOR=rules` (por defecto; `none` / `llm` disponibles) extrae
campos estructurados según el tipo — factura: `total`, `date`, `tax_id`, `invoice_number`;
nómina: `net_pay`, `gross_pay`, `period`; extracto: `iban`, `closing_balance`; DNI:
`document_number`, `birth_date`… Viaja como `extraction` en la respuesta de `/api/ext/ocr`
y `/classify`, y se guarda en `documents.extraction`. Cada campo lleva `value` + `raw`.

Con `DOCUMENT_REDACT_PII=true` el extracto guardado (`documents.text_excerpt` y el de
`/classify`) enmascara email / DNI / NIE / IBAN / teléfono / tarjeta.

### Asíncrono — `POST /api/ext/ocr/jobs`  *(scope `ocr:write`)*

```bash
curl -X POST http://localhost:8087/api/ext/ocr/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -F file=@documento.pdf \
  -F lang=es \
  -F callback_url=https://mi-app.example/webhooks/ocr
# → 202  { "id": "…", "status": "pending", … }
```

- `202` incluye la cabecera `Location: /api/ext/ocr/jobs/{id}`.
- `GET /api/ext/ocr/jobs/{id}` — estado + `result` completo cuando `status = "done"`.
- `GET /api/ext/ocr/jobs` — listado paginado **sin** `result` (solo metadatos; los del
  cliente autenticado). Parámetros: `page`, `per_page` (máx. 100), `status`, `doc_type`,
  `search`, `callback` (`failed` | `pending`), `batch_id`.
- `GET /api/ext/ocr/stats` — contadores por estado, antigüedad del pendiente más viejo, latencia media/p95.
- Si se indicó `callback_url`, el worker hace `POST` firmado con el mismo cuerpo que `GET .../jobs/{id}`.

### Lote — `POST /api/ext/ocr/jobs:batch`  *(scope `ocr:write`)*

Varios `files` en un multipart (o **un `.zip`**) → N jobs con el mismo `batch_id`
(máx. `OCR_BATCH_MAX_FILES`). `GET /api/ext/ocr/batches/{batch_id}` devuelve el desglose
por estado y la lista de jobs.
- Envía una cabecera `Idempotency-Key` para que un reintento de red no cree un job duplicado
  (se replica la respuesta original; ver `app/idempotency/`).
- Un `429` incluye `Retry-After` (segundos). Rate‑limit por defecto `THROTTLE_OCR` (`30/60`),
  con override por cliente (ver [Cuotas y medición](#cuotas-medición-y-rotación-de-secreto)).

### Verificar el webhook (`callback_url`)

Cada `POST` de callback lleva cabeceras `X-OCR-Timestamp` y `X-OCR-Signature`:

```
firma = "sha256=" + hmac_sha256(OCR_CALLBACK_SIGNING_SECRET, f"{X-OCR-Timestamp}." + cuerpo_crudo)
```

Compara con `hmac.compare_digest` y rechaza timestamps viejos. `callback_url` se valida
contra SSRF (se rechazan IPs privadas/loopback/link-local y, si `OCR_CALLBACK_ALLOWED_HOSTS`
está fijado, hosts fuera de la lista). Los redirects no se siguen.

### Reintentos y retención

- Un job que falla se reintenta hasta `OCR_JOB_MAX_ATTEMPTS` veces; si el worker se cae a
  mitad, otro lo recupera pasados `OCR_JOB_STALE_SECONDS`.
- **Webhook con dead-letter**: un callback fallido se reintenta con backoff
  (`OCR_CALLBACK_BACKOFF_BASE_SECONDS * 2**n`) hasta `OCR_CALLBACK_MAX_ATTEMPTS` y luego
  queda en *dead-letter* (`next_callback_at = null`). `POST .../jobs/{id}/redeliver`
  (scope `ocr:write`) lo reencola; el estado va en `callback_status` / `callback_attempts`.
- Los jobs terminados se borran (con sus archivos) pasados `OCR_JOB_RETENTION_DAYS`
  — automático en el worker cada `OCR_PURGE_INTERVAL_SECONDS`, o manual con `make purge-ocr`.
- Al arrancar, backend y worker precargan los modelos (`OCR_WARMUP_LANGS`), así la primera
  petición no espera la descarga/carga.

## Registro de documentos

**Toda** llamada a la API de OCR queda registrada en la tabla `documents` — una fila por
petición, con `mode`:

| `mode` | Origen | `status` |
|---|---|---|
| `sync` | `POST /api/ext/ocr` | siempre `done` (si falla, responde error y no se guarda) |
| `classify` | `POST /api/ext/ocr/classify` | siempre `done` |
| `async` | `POST /api/ext/ocr/jobs` | `pending` → `done` / `error` (lo actualiza el worker) |

Cada fila guarda metadatos (`original_filename`, `content_type`, `size_bytes`, `lang`,
`page_count`, `processing_ms`), el tipo de documento detectado (`doc_type`,
`doc_type_confidence`), el número de caracteres reconocidos (`char_count`) y un **extracto
del texto** (`text_excerpt`, primeros `DOCUMENT_TEXT_EXCERPT_CHARS` caracteres; `0` = no
guardar texto). Las filas `async` enlazan con su `ocr_jobs.id` (`ocr_job_id`); ese enlace es
`SET NULL`, así que el registro **sobrevive a la purga por retención de los jobs**.

- El registro nunca puede tumbar una respuesta OCR: se escribe en su propia transacción y
  cualquier error solo se loguea.
- `record_document` no guarda el resultado OCR completo (eso vive en `ocr_jobs.result`
  mientras el job no se purgue) — solo el extracto.

### Panel — `/api/v1/documents` *(permiso `documents.view`)*

Autenticado con cookie‑JWT (no con el Bearer de la API externa):

- `GET /api/v1/documents` — listado paginado; filtros `mode`, `doc_type`, `status`,
  `search` (nombre de archivo).
- `GET /api/v1/documents/{id}` — una fila.
- `GET /api/v1/documents/stats` — totales, desglose `by_mode` / `by_status` / `by_doc_type`,
  documentos en las últimas 24 h, latencia media/p95.
- `DELETE /api/v1/documents/{id}` — borra el registro (permiso `documents.delete`); el job
  OCR asociado no se ve afectado.

En el panel: menú **OCR → Documentos**.

Retención propia opcional: `DOCUMENT_RETENTION_DAYS` (0 = conservar siempre); la purga corre
en el worker de OCR junto con la de jobs.

## Cuotas, medición y rotación de secreto

Cada llamada OCR se contabiliza por `api_client` en la tabla `client_usage` (una fila por
mes `YYYY-MM`: `pages` y `requests`). Se incrementa en el endpoint síncrono, en `classify`,
al crear un job async y al procesarlo.

- **Límites por cliente** (opcionales, sobrescriben el default global):
  - `rate_limit` — formato `«n/segundos»` (p. ej. `120/60`); si es `null` se usa `THROTTLE_OCR`.
  - `monthly_page_quota` — tope de páginas al mes; `null`/`0` = `OCR_DEFAULT_MONTHLY_PAGE_QUOTA`
    (0 = ilimitado). Al agotarse, los endpoints `ocr:write` responden `429` con
    `detail` de cuota; los `ocr:read` siguen funcionando.
- **Cabeceras** en toda respuesta OCR: `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
  `X-RateLimit-Reset`; en escrituras con cuota, además `X-Quota-Limit` y `X-Quota-Remaining`.
  El `429` mantiene `Retry-After`.
- `GET /api/ext/ocr/usage` *(scope `ocr:read`)* — uso del mes en curso + cuota y rate‑limit
  efectivos del cliente autenticado.

### Panel *(permiso `api_clients.manage`)*

- `PATCH /api/v1/api-clients/{id}` — fija `rate_limit` / `monthly_page_quota` (`rate_limit`
  mal formado → `422`).
- `GET /api/v1/api-clients/{id}/usage` — mismo desglose que `/usage` pero para cualquier cliente.
- `POST /api/v1/api-clients/{id}/rotate` — genera un secreto nuevo (se muestra **una vez**) e
  invalida el secreto anterior y todos sus tokens de acceso.

En el panel: **Usuarios → Clientes API** (columna «Límites y uso», editar límites, «Rotar secreto»).

## Configuración OCR (`.env`)

| Variable | Def. | Descripción |
|---|---|---|
| `STORAGE_BACKEND` | `local` | `local` (volumen) o `s3` (`S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`) |
| `OCR_ENGINE` | `paddle` | `paddle` · `tesseract` · `fake` |
| `OCR_LANG` | `es` | idioma por defecto |
| `OCR_LANG_AUTODETECT` | `false` | si no se pasa `lang`, detectarlo del texto y reejecutar |
| `TESSERACT_CMD` | *(vacío)* | ruta al binario `tesseract` (vacío = en el PATH) |
| `OCR_USE_GPU` | `false` | usar GPU (requiere `paddlepaddle-gpu`) |
| `OCR_MODEL_DIR` | `/app/backend/.paddlex` | caché de modelos PaddleOCR/PaddleX |
| `OCR_PDF_DPI` | `200` | DPI al rasterizar PDFs |
| `OCR_SYNC_MAX_BYTES` / `OCR_SYNC_MAX_PAGES` | `10000000` / `5` | límites del endpoint síncrono |
| `OCR_MAX_UPLOAD_BYTES` | `52428800` | límite de subida para jobs |
| `OCR_MAX_IMAGE_MEGAPIXELS` | `40` | tope de píxeles por página/imagen (anti-bomba) |
| `OCR_MAX_CONCURRENCY` | `2` | inferencias OCR simultáneas (por proceso) |
| `OCR_ALLOWED_LANGS` | *(vacío)* | idiomas permitidos; vacío = set nativo de PaddleOCR |
| `OCR_SORT_READING_ORDER` | `true` | ordenar líneas por orden de lectura |
| `OCR_CLASSIFIER` | `rules` | tipo de documento: `rules` · `none` · `ml` · `llm` |
| `OCR_CLASSIFIER_MIN_SCORE` / `OCR_CLASSIFIER_MIN_CONFIDENCE` | `2.5` / `0.4` | umbrales para asignar un tipo |
| `OCR_EXTRACTOR` | `rules` | extracción de campos por tipo: `rules` · `none` · `llm` |
| `DOCUMENT_REDACT_PII` | `false` | enmascarar email/DNI/NIE/IBAN/teléfono/tarjeta en el extracto |
| `DOCUMENT_TEXT_EXCERPT_CHARS` | `500` | caracteres del texto OCR guardados en `documents.text_excerpt` (`0` = ninguno) |
| `DOCUMENT_RETENTION_DAYS` | `0` | antigüedad para purgar filas de `documents` (`0` = conservar siempre) |
| `OCR_SYNC_CACHE_TTL_SECONDS` / `OCR_SYNC_CACHE_MAX_ENTRIES` | `300` / `64` | caché del endpoint síncrono (0 = off) |
| `OCR_WORKER_INTERVAL_SECONDS` | `2` | frecuencia de sondeo del worker |
| `OCR_JOB_MAX_ATTEMPTS` | `3` | reintentos antes de marcar el job como `error` |
| `OCR_JOB_STALE_SECONDS` | `900` | antigüedad para reencolar un job `processing` colgado |
| `OCR_JOB_RETENTION_DAYS` | `7` | antigüedad para purgar jobs terminados |
| `OCR_PURGE_INTERVAL_SECONDS` | `3600` | frecuencia de purga en el worker |
| `OCR_WARMUP_ON_STARTUP` / `OCR_WARMUP_LANGS` | `true` / `OCR_LANG` | precarga de modelos al arranque |
| `OCR_CALLBACK_TIMEOUT_SECONDS` | `10` | timeout del webhook |
| `OCR_CALLBACK_ALLOW_PRIVATE` | `false` | permitir callbacks a IPs privadas (solo interno) |
| `OCR_CALLBACK_ALLOWED_HOSTS` | *(vacío)* | lista blanca de hosts para `callback_url` |
| `OCR_CALLBACK_SIGNING_SECRET` | *(→ `SECRET_KEY`)* | secreto HMAC para firmar el webhook |
| `THROTTLE_OCR` | `30/60` | rate‑limit de los endpoints OCR (default; se sobrescribe por `api_client.rate_limit`) |
| `OCR_DEFAULT_MONTHLY_PAGE_QUOTA` | `0` | cuota mensual de páginas por defecto (`0` = ilimitada; override por `api_client.monthly_page_quota`) |

## Desarrollo

### Calidad de código (backend)

Equivalencias con el stack de Laravel:

| Laravel | Aquí | Comando |
|---|---|---|
| Pint (formateador) | `ruff format` | `make format-backend` |
| PHP_CodeSniffer / lint | `ruff check` | (incluido en `make lint-backend`) |
| PHPStan (análisis estático) | `mypy` estricto | `make type-check-backend` |
| — (gate CI) | todo junto | `make check-backend` |

- `make lint-backend` verifica **formato** (`ruff format --check`) **y** lint sin modificar nada.
- `make lint-backend-fix` aplica formato + autofix de lint.
- `mypy` corre con `disallow_untyped_defs`, `strict_equality`, `warn_unreachable`,
  `check_untyped_defs`, `extra_checks` y `disallow_incomplete_defs` sobre `app/`
  (nivel "PHPStan max"); config en `backend/pyproject.toml`.
- `make check-backend` = formato + lint + tipos + tests (lo que corre CI).

```bash
make check-backend       # gate completo del backend
make test-backend        # pytest (usa OCR_ENGINE=fake automáticamente)
make format-backend      # aplica el formateo
make process-ocr         # procesa un lote de jobs pendientes y sale
make purge-ocr           # purga jobs vencidos y sus archivos
make logs-ocr-worker
```

Toda la configuración del backend la lee `app/config.py::Settings` (pydantic-settings) de
la variable de entorno o del `.env`. Para correr el backend **sin Docker** hay una
plantilla propia con los comandos y valores locales: `backend/.env.example`
(y `frontend/.env.example` para el frontend).

**Config del frontend en runtime**: `GET /api/v1/config` (público) devuelve la config
pública de la SPA (hoy `app_name`, derivado de `APP_NAME`). El frontend la lee al arrancar
(`src/app.tsx` → `applyRuntimeConfig`); las `VITE_*` quedan solo como fallback de build.
Así el nombre de la app se cambia en el `.env` del backend, sin rebuild del frontend.

Arquitectura OCR:

- `app/services/ocr/` — `loader.py` (imagen/PDF → páginas), `engine.py` (`PaddleOcrEngine` /
  `FakeOcrEngine` + `warmup`), `service.py` (inferencia fuera del event loop), `jobs.py`
  (lógica común), `callback.py` (webhook firmado + guarda SSRF), `storage.py`.
- `app/models/ocr_job.py` + `app/repositories/ocr_job.py` — tabla `ocr_jobs` (claim/reclaim/purge).
- `app/models/document.py` + `app/repositories/document.py` + `app/domain/document/` +
  `app/routers/documents.py` — tabla `documents` (registro de todo lo procesado por la API).
- `app/routers/ext_ocr.py` (API externa) y `app/routers/ocr.py` (panel).
- `app/models/api_client.py` (`ApiClient` + `ClientUsage`) + `app/repositories/client_usage.py` —
  cuotas y medición; `app/dependencies.py::require_ocr` aplica scope + rate‑limit + cuota.
- `app/ocr/worker.py` + `app/ocr/processor.py` — worker de la cola (servicio `ocr-worker`):
  reclaim de jobs colgados → claim → OCR → callback → purga por retención.
- `app/services/ocr/langs.py` (validación de idioma), `cache.py` (caché síncrona),
  `classifier.py` (tipo de documento por reglas; pluggable para ML/LLM más adelante).

### Readiness

- `GET /api/v1/ocr/ready` → `200` cuando hay al menos un modelo cargado, `503` mientras calienta
  (útil como *readiness probe*). `GET /api/health` incluye el mismo estado en `ocr.ready`.

## Limitaciones conocidas

- **DNS rebinding**: el guarda SSRF de callbacks resuelve el host y luego httpx vuelve a
  resolver al conectar. Cierre completo = transport de httpx con IP fijada. Mitígalo con
  política de egress de red en entornos hostiles.
- **Storage por defecto en disco**: `STORAGE_BACKEND=local` comparte el volumen
  `media_data` entre backend y worker. Para multi-nodo, `STORAGE_BACKEND=s3` (extra `s3`).
- **Dead-letter de callbacks sin re-alertas**: tras agotar `OCR_CALLBACK_MAX_ATTEMPTS` el
  job queda marcado pero no notifica a nadie — hay que consultarlo (`?callback=failed`) o
  reencolarlo con `redeliver`.
- **paddleocr pin en 2.x**: `engine.py` ya soporta la API 3.x, pero paddle 3.x falla en
  CPU bajo emulación; subir el pin y verificar en CI x86 es el paso pendiente.
- **`OCR_MAX_CONCURRENCY` es por proceso**: con N réplicas del worker el paralelismo real es
  N × ese valor. Para un tope global haría falta un semáforo en Redis/BD.
- **Rate‑limit y cuota son por proceso/ventana fija en BD**: el contador de rate‑limit es una
  ventana fija (`rate_limit_counters`); la cuota mensual se cuenta por `page_count` y no se
  factura cuando el OCR falla antes de contar páginas (comportamiento deseado).

## Posibles mejoras (roadmap)

Ordenadas por relación valor/esfuerzo:

1. *(hecho)* **Extracción de campos por tipo** (`OCR_EXTRACTOR=rules`) — falta un
   backend `llm` con proveedor real.
2. *(hecho)* **Storage enchufable** `STORAGE_BACKEND=local|s3` — `S3Storage` (boto3, extra
   `s3`) desacopla el worker del disco compartido.
3. **Observabilidad** — logs JSON estructurados + `/metrics` Prometheus (histograma de
   latencia OCR, profundidad de cola, hit‑rate de caché, errores de motor).
4. *(hecho)* **Dead-letter de callbacks** — backoff + `redeliver` + filtro `?callback=`.
5. *(hecho)* **Cuotas y medición por cliente** — `rate_limit` y `monthly_page_quota` por
   `api_client`, tabla `client_usage`, `GET /usage`, cabeceras `X-Quota-*`.
6. *(hecho)* **Formatos de salida** `?format=text|hocr|alto|pdf` (el `pdf` de un job
   re-lee el original vía el storage).
7. *(hecho)* **Motor alternativo Tesseract** (`OCR_ENGINE=tesseract`); queda abrir un
   adaptador a un OCR cloud tras la misma interfaz `OcrEngine`.
8. *(hecho)* **Detección automática de idioma** (`OCR_LANG_AUTODETECT`).
9. *(hecho)* **Redacción de PII** (`DOCUMENT_REDACT_PII`).
10. *(hecho)* **Endpoint batch** `POST /jobs:batch` + `GET /batches/{id}`.
11. *(hecho)* **Rotación de secreto** de `api_client` (`POST .../rotate`) y cabeceras
    `X-RateLimit-*` en todas las respuestas OCR.
12. *(parcial)* **Clasificador ML/LLM** — `OCR_CLASSIFIER=ml` (TF‑IDF + `scripts/
    train_classifier.py`) y `llm` (interfaz + stub) ya existen; falta el proveedor LLM real.
13. *(bloqueado)* **`paddleocr` 3.x / PP‑OCRv5** — wrapper listo; subir el pin y verificar
    en CI x86 (3.x rompe en CPU bajo emulación).
