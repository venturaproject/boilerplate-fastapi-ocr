.PHONY: up down restart build build-no-cache logs logs-backend logs-ocr-worker ps \
        shell-backend shell-frontend shell-db \
        migrate makemigration seed \
        process-outbox process-inbox process-ocr purge-ocr test-backend \
        lint tsc \
        format-backend lint-backend lint-backend-fix type-check-backend check-backend \
        observability observability-down \
        install-frontend \
        clean-volumes help

DC      = docker compose -f compose.dev.yml
BACKEND = boilerplate-fastapi-ocr-backend-1

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Servicios ─────────────────────────────────────────────────────────────────

up: ## Levanta todos los servicios en segundo plano
	$(DC) up -d

down: ## Detiene y elimina todos los contenedores
	$(DC) down

restart: ## Reinicia todos los servicios
	$(DC) restart

build: ## Reconstruye las imágenes
	$(DC) build

build-no-cache: ## Reconstruye sin caché
	$(DC) build --no-cache

logs: ## Logs de todos los servicios en tiempo real
	$(DC) logs -f

logs-backend: ## Logs solo del backend
	$(DC) logs -f backend

logs-ocr-worker: ## Logs del worker de OCR
	$(DC) logs -f ocr-worker

ps: ## Estado de los contenedores
	$(DC) ps

# ── Shells ────────────────────────────────────────────────────────────────────

shell-backend: ## Shell en el contenedor backend
	$(DC) exec backend sh

shell-frontend: ## Shell en el contenedor frontend
	$(DC) exec frontend sh

shell-db: ## psql directo en postgres
	$(DC) exec postgres psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-fastapi_ocr_db}

# ── FastAPI / Alembic ─────────────────────────────────────────────────────────
# Los comandos del backend corren en /app/backend (ahí viven el proyecto y el venv)

BE = $(DC) exec -w /app/backend backend

migrate: ## Ejecuta las migraciones (alembic upgrade head)
	$(BE) uv run alembic upgrade head

makemigration: ## Genera una nueva migración automática
	$(BE) uv run alembic revision --autogenerate -m "auto"

seed: ## Carga permisos, roles y usuario admin (idempotente)
	$(BE) uv run python seed.py

process-outbox: ## Publica los eventos pendientes del outbox (un lote)
	$(BE) uv run python -m app.events.worker --once --batch-size 200

process-inbox: ## Alias: el worker drena inbox y outbox en el mismo --once
	$(BE) uv run python -m app.events.worker --once --batch-size 200

process-ocr: ## Procesa un lote de jobs OCR pendientes y sale
	$(BE) uv run python -m app.ocr.worker --once --batch-size 20

purge-ocr: ## Purga jobs OCR vencidos (retención) y sus archivos
	$(BE) uv run python -m app.ocr.worker --purge

test-backend: ## Ejecuta la suite de pytest del backend
	$(BE) uv run pytest -q

# ── Backend ───────────────────────────────────────────────────────────────────

format-backend: ## Ruff format — aplica el estilo
	$(BE) uv run ruff format .

lint-backend: ## Ruff: formato (--check) + lint
	$(BE) uv run ruff format --check .
	$(BE) uv run ruff check .

lint-backend-fix: ## Ruff: aplica formato + lint con autofix
	$(BE) uv run ruff format .
	$(BE) uv run ruff check . --fix

type-check-backend: ## Mypy — análisis estático estricto
	$(BE) uv run mypy app/

check-backend: lint-backend type-check-backend test-backend ## Gate completo del backend (formato + lint + tipos + tests)

observability: ## Levanta el overlay Prometheus + Grafana (http://localhost:3001)
	docker compose -f compose.dev.yml -f compose.observability.yml up -d prometheus grafana ocr-worker

observability-down: ## Para el overlay de monitorización
	docker compose -f compose.dev.yml -f compose.observability.yml stop prometheus grafana

# ── Frontend ──────────────────────────────────────────────────────────────────

install-frontend: ## pnpm install en el frontend
	$(DC) exec frontend pnpm install

lint: ## ESLint en el frontend
	$(DC) exec frontend pnpm lint

tsc: ## TypeScript check en el frontend
	$(DC) exec frontend pnpm tsc

# ── Limpieza ──────────────────────────────────────────────────────────────────

clean-volumes: ## Elimina contenedores y volúmenes  ⚠️  borra datos
	$(DC) down -v
