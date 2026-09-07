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
make up                       # postgres · backend · ocr-worker · frontend · nginx (dev añade `worker` de eventos)
make migrate && make seed     # crea tablas, permisos y un API client de ejemplo ("ocr-demo")
```

- API + docs: `http://localhost:8087/api/docs`
- Panel: `http://localhost:8087/admin` → menú **OCR** (playground · Trabajos · Documentos).
  El dashboard muestra métricas de OCR (por tipo de documento, por modo, latencia, actividad).
- `make seed` imprime el `client_id` / `client_secret` del cliente `ocr-demo`.

### Motores OCR (`OCR_ENGINE`)

| valor | motor | notas |
|---|---|---|
| `paddle` *(def.)* | **PaddleOCR 3.x / PP‑OCRv5** | mejor precisión; `paddlepaddle` ≈ 1 GB, se instala en la imagen |
| `tesseract` | **Tesseract** (`pytesseract` + binario) | alternativa ligera; requiere los language packs de la imagen |
| `fake` | stub determinista | tests / CI / dev sin dependencias pesadas |

> En Apple Silicon, si `paddlepaddle` no tiene wheel para tu plataforma, usa
> `OCR_ENGINE=fake` (o `tesseract`), o ejecuta el servicio en un host x86_64. El bump a
> PaddleOCR 3.x está en el código pero **la ejecución real de paddle 3.x hay que
> verificarla en CI / host x86** — `fake` y `tesseract` no se ven afectados.

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

- Las líneas salen en **orden de lectura** (filas por `y`, cada fila de izquierda a
  derecha; desactivable con `OCR_SORT_READING_ORDER=false`).
- Resultados idénticos (mismo contenido + idioma) se sirven de **caché**
  (`cached: true`) durante `OCR_SYNC_CACHE_TTL_SECONDS`.
- Incluye `classification` con el **tipo de documento** detectado (ver abajo).
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
  `search` (nombre de archivo).
- `GET /api/ext/ocr/stats` — contadores por estado, antigüedad del pendiente más viejo, latencia media/p95.
- Si se indicó `callback_url`, el worker hace `POST` firmado con el mismo cuerpo que `GET .../jobs/{id}`.
- Envía una cabecera `Idempotency-Key` para que un reintento de red no cree un job duplicado
  (se replica la respuesta original; ver `app/idempotency/`).
- Un `429` incluye `Retry-After` (segundos). Rate‑limit por defecto `THROTTLE_OCR` (`30/60`).

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

## Configuración OCR (`.env`)

| Variable | Def. | Descripción |
|---|---|---|
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
| `THROTTLE_OCR` | `30/60` | rate‑limit de los endpoints OCR |

## Desarrollo

```bash
make test-backend        # pytest (usa OCR_ENGINE=fake automáticamente)
make lint-backend
make type-check-backend
make process-ocr         # procesa un lote de jobs pendientes y sale
make purge-ocr           # purga jobs vencidos y sus archivos
make logs-ocr-worker
```

Arquitectura OCR:

- `app/services/ocr/` — `loader.py` (imagen/PDF → páginas), `engine.py` (`PaddleOcrEngine` /
  `FakeOcrEngine` + `warmup`), `service.py` (inferencia fuera del event loop), `jobs.py`
  (lógica común), `callback.py` (webhook firmado + guarda SSRF), `storage.py`.
- `app/models/ocr_job.py` + `app/repositories/ocr_job.py` — tabla `ocr_jobs` (claim/reclaim/purge).
- `app/models/document.py` + `app/repositories/document.py` + `app/domain/document/` +
  `app/routers/documents.py` — tabla `documents` (registro de todo lo procesado por la API).
- `app/routers/ext_ocr.py` (API externa) y `app/routers/ocr.py` (panel).
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
- **Storage en disco local**: backend y worker comparten un volumen (`media_data`). Para
  multi-nodo hace falta almacenamiento de objetos (S3).
- **Callbacks sin dead-letter**: 2 reintentos inmediatos; si fallan, queda `callback_status`
  pero no hay reenvío automático posterior.
- **paddleocr 3.x sin verificar en x86**: el wrapper de `engine.py` ya usa la API 3.x
  (PP‑OCRv5) pero la ejecución real requiere validación en CI / host x86.
- **`OCR_MAX_CONCURRENCY` es por proceso**: con N réplicas del worker el paralelismo real es
  N × ese valor. Para un tope global haría falta un semáforo en Redis/BD.
- **Rate‑limit global**: un único `THROTTLE_OCR` para todos los clientes; no hay cuota ni
  límite por `api_client`.

## Posibles mejoras (roadmap)

Ordenadas por relación valor/esfuerzo:

1. *(hecho)* **Extracción de campos por tipo** (`OCR_EXTRACTOR=rules`) — falta un
   backend `llm` con proveedor real.
2. **Almacenamiento de objetos (S3/MinIO)** para las subidas — desacopla worker del disco
   compartido y permite escalar el worker horizontalmente de verdad.
3. **Observabilidad** — logs JSON estructurados + `/metrics` Prometheus (histograma de
   latencia OCR, profundidad de cola, hit‑rate de caché, errores de motor).
4. **Dead‑letter de callbacks** — backoff con más reintentos, registro de intentos por job y
   endpoint para reenviar manualmente.
5. **Cuotas y medición por cliente** — rate‑limit y cuota mensual de páginas por
   `api_client` (base para facturación); los datos ya están en `documents`.
6. **Formatos de salida** — `?format=text|hocr|alto|pdf` (PDF con capa de texto es una
   petición habitual en APIs de OCR).
7. *(hecho)* **Motor alternativo Tesseract** (`OCR_ENGINE=tesseract`); queda abrir un
   adaptador a un OCR cloud tras la misma interfaz `OcrEngine`.
8. *(hecho)* **Detección automática de idioma** (`OCR_LANG_AUTODETECT`).
9. *(hecho)* **Redacción de PII** (`DOCUMENT_REDACT_PII`).
10. **Endpoint batch** — subir un zip o varios archivos y devolver un `batch_id`.
11. **Rotación de secreto** de `api_client` (hoy solo crear/revocar) y cabeceras
    `X-RateLimit-*` en las respuestas.
12. *(parcial)* **Clasificador ML/LLM** — `OCR_CLASSIFIER=ml` (TF‑IDF + `scripts/
    train_classifier.py`) y `llm` (interfaz + stub) ya existen; falta el proveedor LLM real.
13. *(en curso)* **`paddleocr` 3.x / PP‑OCRv5** — código migrado; falta verificación en x86.
