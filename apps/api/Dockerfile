# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.12.2 AS uv

FROM python:3.14.8-slim-bookworm AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY apps/api/pyproject.toml apps/api/uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.14.8-slim-bookworm AS runtime

ENV PATH=/app/.venv/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 yaqin \
    && useradd --uid 10001 --gid yaqin --create-home --home-dir /home/yaqin yaqin

WORKDIR /app

COPY --from=builder --chown=yaqin:yaqin /app/.venv ./.venv
COPY --chown=yaqin:yaqin apps/api/app ./app

USER yaqin

EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

