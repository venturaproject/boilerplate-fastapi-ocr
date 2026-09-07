# Eventos: CQRS · Outbox · Inbox · Idempotencia · Rate limiting

Infraestructura de eventos para FastAPI async, **sin dependencias runtime nuevas**
(el dispatcher es `python -m app.events.worker`; el rate limiting usa una tabla
Postgres). Portado del mismo diseño que `apps/shared` en `boilerplate-django-react`.

## Flujo

```
HTTP (router)                            Webhook entrante (routers/webhooks.py)
     │                                          │
     │ await command_bus.dispatch(db, Cmd)      │ await store(db, source, message_id, …)  ── UNIQUE(source, message_id)
     ▼                                          ▼
 CommandBus                               inbox_messages (pending)
  └─ collector_scope()                          │  python -m app.events.worker   (claim SKIP LOCKED)
       ├─ await handler(session, cmd)           ▼
       │     └─ repositories.*  (repos existentes, sin cambios)
       │     └─ record_events([DomainEvent(...)])
       └─ drain_events() → session.add(OutboxMessage) + flush   [misma transacción]
                                    │
                                    ▼
                       translate(payload) → Command ──► CommandBus (mismo pipeline)
                                    │
                        outbox_messages (pending)
                                    │  worker  (claim SKIP LOCKED)
                                    ▼
                       await event_bus.publish(event_name, payload)
                                    ▼
                       @subscribe(...) corutinas  (notificaciones, side-effects, acks…)
```

La transacción la aporta el contexto: `get_db` en request (commit al final),
`async with session.begin()` en el worker. Un error en el handler propaga y hace
rollback de todo (incluidas las filas del outbox).

Lectura: `await query_bus.ask(db, Query(...))` → handler directo, sin outbox.

## Cómo añadir…

### …un comando

```python
# app/domain/<x>/commands.py
@dataclass(frozen=True)
class HacerAlgo(Command):
    cosa_id: uuid.UUID

# app/domain/<x>/handlers.py   (lo importa app/domain/__init__.py al arrancar)
@command_handler(HacerAlgo)
async def handle_hacer_algo(session, cmd: HacerAlgo) -> uuid.UUID:
    obj = await repo.get(session, cmd.cosa_id)
    ...
    return obj.id

# app/routers/<x>.py
nuevo_id = await command_bus.dispatch(db, HacerAlgo(cosa_id=...))
```

### …un evento de dominio + subscriber

```python
# app/domain/<x>/events.py
@dataclass(frozen=True)
class AlgoPaso(DomainEvent):
    detalle: str = ""
    @classmethod
    def name(cls) -> str:
        return "algo.paso"

# en el handler, tras persistir:
record_events([AlgoPaso(aggregate_id=str(obj.id), aggregate_type="Algo", detalle="x")])

# app/domain/<x>/subscribers.py
@subscribe("algo.paso")
async def cuando_algo_paso(payload: dict) -> None:
    ...
```

### …un traductor del inbox (mensaje entrante → comando)

```python
# app/domain/<x>/translators.py
@inbox_translator("synergy", "employee.upserted")
def _(payload: dict) -> Command:
    return SyncTrabajadorFromERP(**payload)
```

Registra cada subpaquete en `app/domain/<x>/__init__.py` y añádelo a
`app/domain/__init__.py`.

## Operación

| Comando | Uso |
|---|---|
| `python -m app.events.worker` | Bucle: drena inbox + outbox cada `EVENTS_WORKER_INTERVAL_SECONDS`. |
| `python -m app.events.worker --once [--batch-size N]` | Un lote y sale (cron / systemd timer). |
| `make process-outbox` / `make process-inbox` | Atajos a `--once`. |

`compose.dev.yml` levanta un servicio `worker` con el bucle. En producción, cron:

```cron
* * * * *  cd /app/backend && python -m app.events.worker --once --batch-size 200
```

Reintentos: backoff exponencial (`app/events/retry.py`, base 10 s, tope 1 h) hasta
`max_attempts` (5); luego `failed` para inspección manual.

## Rate limiting

Dependencias `rate_limit(scope, limit, per_seconds)` (`app/ratelimit/limiter.py`)
sobre la tabla `rate_limit_counters` (ventana fija, `INSERT … ON CONFLICT`):

| Scope | Endpoint | Rate (`.env`) |
|---|---|---|
| `login` | `POST /api/v1/auth/login` | `THROTTLE_LOGIN` (5/60) |
| `ext_auth` | `POST /api/ext/auth/token`, `/refresh` | `THROTTLE_EXT_AUTH` (10/60) |
| `ext_api` | `GET /api/ext/{trabajadores,telefonos,dispositivos}` | `THROTTLE_EXT_API` (600/60) |
| `webhook` | `POST /api/ext/webhooks/synergy` | `THROTTLE_WEBHOOK` (120/60) |

No hay límite global por request (golpearía la DB en cada llamada). Para añadirlo,
un middleware ASGI que llame al mismo `rate_limit` helper.

## Idempotencia HTTP

`IdempotencyMiddleware` (`app/idempotency/middleware.py`, montado en `main.py`).
Con la cabecera `Idempotency-Key` en `POST/PUT/PATCH/DELETE` bajo `/api/`:

- misma key + mismo cuerpo → se ejecuta una vez, luego **replica** la respuesta
  (con cabecera `Idempotent-Replay: true`)
- misma key + cuerpo distinto → `422`
- petición idéntica en curso → `409`

Filas en `idempotency_keys`; principal = `user:<id>` (JWT cookie) / `client:<hash>`
(Bearer) / `anon:<ip>`. `IDEMPOTENCY_KEY_TTL_HOURS` documenta la retención.

## Webhook de Synergy

`POST /api/ext/webhooks/synergy` — Bearer token con scope `webhooks:write`,
cabecera `X-Message-Id` (o `id` en el cuerpo), `event` en el cuerpo. Responde
`202 accepted` / `200 duplicate` y encola en el inbox. El scope `webhooks:write`
se añade al array `ApiClient.scopes` (JSON libre, sin registro central).

## Migrar el dispatcher a Celery / ARQ

Sólo cambia el disparador: una task periódica que llame a
`app.events.outbox.process_outbox_batch()` y `app.events.inbox.process_inbox_batch()`.
El resto (buses, outbox, inbox, event bus) no cambia.
