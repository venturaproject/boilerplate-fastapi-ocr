# ── Build the SPA ────────────────────────────────────────────────────────────
# Context = repo root (see compose.yml). Only frontend/ is needed here.
FROM node:22-alpine AS build
WORKDIR /app
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable

COPY frontend/package.json frontend/pnpm-lock.yaml frontend/.npmrc ./
RUN pnpm install --frozen-lockfile

COPY frontend/ ./
# App name is loaded at runtime from GET /api/v1/config; these only affect the
# pre-hydration flash / the API base URL baked into the bundle.
ARG VITE_APP_NAME=Ocrer
ARG VITE_PUBLIC_API_URL=
ENV VITE_APP_NAME=$VITE_APP_NAME
ENV VITE_PUBLIC_API_URL=$VITE_PUBLIC_API_URL
RUN pnpm build

# ── Serve ────────────────────────────────────────────────────────────────────
FROM nginx:alpine
COPY infrastructure/nginx/nginx.prod.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
