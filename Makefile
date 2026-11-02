.DEFAULT_GOAL := help
COMPOSE      ?= docker compose
COMPOSE_GPU  ?= docker compose -f compose.yaml -f compose.override.yaml -f compose.gpu.yaml

.PHONY: help env up up-gpu seed eval test lint fmt down logs ps

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

env: ## Create .env from .env.example if missing
	@test -f .env || { cp .env.example .env && echo "Created .env from .env.example: set ANTHROPIC_API_KEY"; }

up: env ## Build and start the stack (TEI on CPU), wait for init and healthy datastores
	$(COMPOSE) up -d --build
	$(COMPOSE) wait init
	$(COMPOSE) up -d --no-build --wait postgres qdrant embeddings

up-gpu: env ## Same as `up` with TEI on GPU (NVIDIA Container Toolkit required)
	$(COMPOSE_GPU) up -d --build
	$(COMPOSE_GPU) wait init
	$(COMPOSE_GPU) up -d --no-build --wait postgres qdrant embeddings

seed: ## Ingest the corpus snapshot through the ingestion endpoint (available from Phase 1)
	$(COMPOSE) exec ingestion python -m ingestion.seed /data/corpus/odoo19-dev

eval: ## Run the evaluation, `eval` profile (available from Phase 4)
	$(COMPOSE) --profile eval run --rm eval

test: ## Python tests
	uv run pytest

lint: ## ruff (lint + format check) and mypy
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy packages infra services eval

fmt: ## Auto-format and fix
	uv run ruff format .
	uv run ruff check --fix .

down: ## Stop the stack. Keeps volumes: never use `down -v` (it wipes the index and the conversations)
	$(COMPOSE) down

logs: ## Follow logs
	$(COMPOSE) logs -f --tail=100

ps: ## Service status
	$(COMPOSE) ps
