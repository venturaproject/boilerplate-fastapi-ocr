FROM python:3.12-slim

WORKDIR /app/backend

# Runtime libs: libpq (asyncpg build helpers) + OpenCV/Paddle shared libs used by
# PaddleOCR + the Tesseract engine and language packs (OCR_ENGINE=tesseract).
RUN apt-get update && apt-get install -y \
        libpq-dev gcc postgresql-client \
        libgl1 libglib2.0-0 libgomp1 libsm6 libxext6 libxrender1 \
        tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng tesseract-ocr-fra tesseract-ocr-deu tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_SYSTEM_PYTHON=1
ENV HOME=/root

COPY backend/pyproject.toml ./
# Resolve deps (incl. the PaddleOCR + Tesseract engines) into /app/backend/.venv
RUN uv sync --no-dev --extra paddle --extra tesseract

COPY backend/ ./

EXPOSE 8000

COPY infrastructure/backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
