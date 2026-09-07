# boilerplate-fastapi-ocr

API de **OCR** basada en [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), construida
sobre el boilerplate FastAPI + React (auth cookie‑JWT, CQRS, outbox/inbox, Postgres, y una
capa de **API externa** con `client_id`/`client_secret` → Bearer + scopes).

Cualquier aplicación externa puede enviar **imágenes o PDFs** y recibir el **texto
reconocido** — de forma **síncrona** (respuesta inmediata) o **asíncrona** (cola de
trabajos + webhook opcional).

## Puesta en marcha

```bash
cp .env.example .env          # ajusta SECRET_KEY, credenciales, puertos…
make build
make up                       # postgres + backend + ocr-worker + frontend + nginx
make migrate && make seed     # crea tablas, permisos y un API client de ejemplo ("ocr-demo")
```

- API + docs: `http://localhost:8087/api/docs`
- Panel (playground OCR e historial): `http://localhost:8087/admin` → menú **OCR**
- `make seed` imprime el `client_id` / `client_secret` del cliente `ocr-demo`.

> **PaddleOCR es pesado** (`paddlepaddle` ≈ 1 GB) y se instala dentro de la imagen. En
> desarrollo puedes trabajar sin él poniendo `OCR_ENGINE=fake` en `.env` (motor stub
> determinista). En Apple Silicon, si `paddlepaddle` no dispone de wheel para tu
> plataforma, usa `OCR_ENGINE=fake` o ejecuta el servicio en un host x86_64.

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
  "processing_ms": 842
}
```

Límites: `OCR_SYNC_MAX_BYTES` (10 MB), `OCR_SYNC_MAX_PAGES` (5). Para más, usa los jobs.

### Asíncrono — `POST /api/ext/ocr/jobs`  *(scope `ocr:write`)*

```bash
curl -X POST http://localhost:8087/api/ext/ocr/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -F file=@documento.pdf \
  -F lang=es \
  -F callback_url=https://mi-app.example/webhooks/ocr
# → 202  { "id": "…", "status": "pending", … }
```

- `GET /api/ext/ocr/jobs/{id}` — estado + `result` cuando `status = "done"`.
- `GET /api/ext/ocr/jobs` — listado paginado (solo los del cliente autenticado).
- Si se indicó `callback_url`, el worker hace `POST` con el mismo cuerpo que `GET .../jobs/{id}`.

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

## Configuración OCR (`.env`)

| Variable | Def. | Descripción |
|---|---|---|
| `OCR_ENGINE` | `paddle` | `paddle` o `fake` |
| `OCR_LANG` | `es` | idioma por defecto de PaddleOCR |
| `OCR_USE_GPU` | `false` | usar GPU (requiere `paddlepaddle-gpu`) |
| `OCR_PDF_DPI` | `200` | DPI al rasterizar PDFs |
| `OCR_SYNC_MAX_BYTES` / `OCR_SYNC_MAX_PAGES` | `10000000` / `5` | límites del endpoint síncrono |
| `OCR_MAX_UPLOAD_BYTES` | `52428800` | límite de subida para jobs |
| `OCR_MAX_CONCURRENCY` | `2` | inferencias OCR simultáneas |
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
- `app/routers/ext_ocr.py` (API externa) y `app/routers/ocr.py` (panel).
- `app/ocr/worker.py` + `app/ocr/processor.py` — worker de la cola (servicio `ocr-worker`):
  reclaim de jobs colgados → claim → OCR → callback → purga por retención.
