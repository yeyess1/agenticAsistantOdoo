# syntax=docker/dockerfile:1
# ingestion: FastAPI (skeleton; app code arrives in Phase 1)
# Build (see compose.yaml): context = ./services/ingestion; additional contexts:
#   common    = ./packages/common   (shared library, COPY --from=common)
#   workspace = .                   (uv.lock + pyproject files only, via bind mounts)
ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

# --- deps: third-party dependencies only (cached until uv.lock / pyprojects change) ----
FROM ${PYTHON_IMAGE} AS deps
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /workspace
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,from=workspace,source=uv.lock,target=/workspace/uv.lock \
    --mount=type=bind,from=workspace,source=pyproject.toml,target=/workspace/pyproject.toml \
    --mount=type=bind,from=workspace,source=packages/common/pyproject.toml,target=/workspace/packages/common/pyproject.toml \
    --mount=type=bind,from=workspace,source=services/agent/pyproject.toml,target=/workspace/services/agent/pyproject.toml \
    --mount=type=bind,from=workspace,source=services/ingestion/pyproject.toml,target=/workspace/services/ingestion/pyproject.toml \
    --mount=type=bind,from=workspace,source=infra/init/pyproject.toml,target=/workspace/infra/init/pyproject.toml \
    --mount=type=bind,from=workspace,source=eval/pyproject.toml,target=/workspace/eval/pyproject.toml \
    uv sync --frozen --no-dev --no-install-workspace --package odoo-rag-ingestion

# --- build: install workspace members (common + this service) into the venv -----------
FROM deps AS build
COPY --from=common . /build/common
COPY . /build/service
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /opt/venv/bin/python --no-deps /build/common /build/service

# --- runtime: venv only, non-root ------------------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
USER 10001:10001
EXPOSE 8001
ENTRYPOINT ["uvicorn", "ingestion.main:app", "--host", "0.0.0.0", "--port", "8001"]
