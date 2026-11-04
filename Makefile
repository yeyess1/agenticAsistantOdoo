.DEFAULT_GOAL := help
COMPOSE      ?= docker compose
COMPOSE_GPU  ?= docker compose -f compose.yaml -f compose.override.yaml -f compose.gpu.yaml

.PHONY: help env up up-gpu seed insights-backfill eval test lint graph openapi fmt watch down logs ps

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

env: ## Create .env from .env.example if missing
	@test -f .env || { cp .env.example .env && echo "Created .env from .env.example: set the API key of LLM_PROVIDER"; }

up: env ## Build and start the stack (TEI on CPU), wait for init and healthy datastores
	$(COMPOSE) up -d --build
	$(COMPOSE) up -d --no-build --wait postgres qdrant embeddings ingestion agent frontend

up-gpu: env ## Same as `up` with TEI on GPU (NVIDIA Container Toolkit required)
	$(COMPOSE_GPU) up -d --build
	$(COMPOSE_GPU) up -d --no-build --wait postgres qdrant embeddings ingestion agent frontend

seed: ## Ingest the corpus snapshot through POST /documents (FORCE=1 reindexes unchanged docs)
	$(COMPOSE) exec ingestion python -m ingestion.seed /data/corpus/odoo19-dev $(if $(FORCE),--force)

insights-backfill: ## Fill query_log (insights view) from the existing LangGraph checkpoints; idempotent
	$(COMPOSE) exec agent python -m agent.insights.backfill $(ARGS)

eval: ## Run the evaluation (`eval` profile, E-13); ARGS="--only q01,q28" to select items
	GIT_SHA=$$(git rev-parse --short HEAD 2>/dev/null || echo unknown) EVAL_UID=$$(id -u) EVAL_GID=$$(id -g) \
		$(COMPOSE) --profile eval run --rm --build eval $(ARGS)
	cp eval/reports/dashboard.json frontend/public/eval/latest.json

test: ## Python tests
	uv run pytest

lint: ## ruff (lint + format check) and mypy
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy packages infra services eval

graph: ## Export the agent graph as Mermaid to docs/graph.mmd (compare with ARCHITECTURE section 3.1)
	uv run python scripts/export_graph.py

openapi: ## Export the agent/ingestion OpenAPI specs and regenerate the frontend TS types (U-05)
	cd frontend && npm run gen:api:full

watch: ## Dev loop: rebuild agent/ingestion/frontend on source changes (compose.override.yaml)
	$(COMPOSE) watch

fmt: ## Auto-format and fix
	uv run ruff format .
	uv run ruff check --fix .

down: ## Stop the stack. Keeps volumes: never use `down -v` (it wipes the index and the conversations)
	$(COMPOSE) down

logs: ## Follow logs
	$(COMPOSE) logs -f --tail=100

ps: ## Service status
	$(COMPOSE) ps
