FROM node:22-alpine

WORKDIR /app

# pnpm viene por Corepack; la versión exacta la fija "packageManager" en package.json.
# `corepack prepare` la baja ya en la imagen para no hacerlo en cada arranque.
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable && corepack prepare pnpm@12.3.4 --activate

EXPOSE 5173
