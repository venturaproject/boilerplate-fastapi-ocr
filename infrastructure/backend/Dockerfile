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

COPY backend/pyproject.toml backend/uv.lock ./
# Resolve deps (incl. the PaddleOCR engine) into /app/backend/.venv.
# For OCR_ENGINE=tesseract instead, build with:  --build-arg OCR_EXTRA=tesseract
ARG OCR_EXTRA=paddle
RUN uv sync --no-dev --extra ${OCR_EXTRA}

COPY backend/ ./

EXPOSE 8000

COPY infrastructure/backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
