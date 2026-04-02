# ============================================================================
# AgentOps Demo — Makefile
# ============================================================================

.DEFAULT_GOAL := help

.PHONY: help up down logs logs-backend health setup-models rebuild \
        restart-backend restart-frontend restart-apps clean \
        lint lint-backend lint-frontend format format-backend format-frontend \
        typecheck typecheck-backend typecheck-frontend check \
        pre-commit pre-commit-install test test-backend

# ============================================================================
# Development Environment
# ============================================================================

## Show available commands
help:
	@echo "AgentOps Demo — Available commands:"
	@echo ""
	@echo "  \033[1;34mServices:\033[0m"
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## //' | awk 'BEGIN {target=""} /^[A-Za-z]/ {if(target) printf "  \033[36m%-24s\033[0m %s\n", target, $$0; target=""} !/^[A-Za-z]/ {target=$$0}' || true
	@grep -E '^[a-zA-Z_-]+:' $(MAKEFILE_LIST) | while IFS=: read -r target _; do \
		desc=$$(grep -B1 "^$$target:" $(MAKEFILE_LIST) | head -1 | sed -n 's/^## //p'); \
		if [ -n "$$desc" ]; then printf "  \033[36m%-24s\033[0m %s\n" "$$target" "$$desc"; fi; \
	done
	@echo ""

## Start all services (dev mode)
up:
	docker compose up -d
	@echo ""
	@echo "Services starting..."
	@echo "  Backend:  http://localhost:8501"
	@echo "  Frontend: http://localhost:3501"
	@echo "  Langfuse: http://localhost:3100"
	@echo "  Phoenix:  http://localhost:6006"
	@echo ""
	@echo "First run? Go to http://localhost:3100 to create a Langfuse account,"
	@echo "then update .env with your project API keys."

## Stop all services
down:
	docker compose down

## Follow all logs
logs:
	docker compose logs -f

## Follow backend logs
logs-backend:
	docker compose logs -f backend

## Backend health check
health:
	@curl -s http://localhost:8501/health | python3 -m json.tool 2>/dev/null || echo "Backend not reachable"

## Pull required Ollama models
setup-models:
	@echo "Pulling Ollama models..."
	ollama pull qwen2.5:14b
	ollama pull nomic-embed-text
	@echo "Models ready."

## Rebuild containers (no cache)
rebuild:
	docker compose build --no-cache
	docker compose up -d

## Restart backend (syncs deps, no rebuild)
restart-backend:
	docker compose restart backend

## Restart frontend (syncs deps, no rebuild)
restart-frontend:
	docker compose restart frontend

## Restart backend + frontend
restart-apps:
	docker compose restart backend frontend

## Clean all volumes (resets data)
clean:
	docker compose down -v
	@echo "All volumes removed (Langfuse DB, ChromaDB, node_modules)."

# ============================================================================
# Code Quality — Linting, Formatting, Type Checking
# ============================================================================

## Run all linters (backend + frontend)
lint: lint-backend lint-frontend

## Lint backend (ruff)
lint-backend:
	cd apps/backend && python3.12 -m ruff check .

## Lint frontend (eslint)
lint-frontend:
	cd apps/frontend && pnpm lint

## Format all code (backend + frontend)
format: format-backend format-frontend

## Format backend (ruff)
format-backend:
	cd apps/backend && python3.12 -m ruff format . && python3.12 -m ruff check --fix .

## Format frontend (prettier)
format-frontend:
	cd apps/frontend && pnpm format

## Run all type checks
typecheck: typecheck-backend typecheck-frontend

## Type-check backend (mypy)
typecheck-backend:
	cd apps/backend && python3.12 -m mypy src/ main.py --config-file pyproject.toml

## Type-check frontend (tsc)
typecheck-frontend:
	cd apps/frontend && pnpm typecheck

## Run all checks (lint + format-check + typecheck) — CI equivalent
check:
	@echo "Running backend checks..."
	cd apps/backend && python3.12 -m ruff check . && python3.12 -m ruff format --check .
	@echo ""
	@echo "Running frontend checks..."
	cd apps/frontend && pnpm lint && pnpm format:check && pnpm typecheck
	@echo ""
	@echo "All checks passed."

# ============================================================================
# Testing
# ============================================================================

## Run backend tests
test-backend:
	cd apps/backend && python3.12 -m pytest -q

## Run all tests
test: test-backend

# ============================================================================
# Pre-commit Hooks
# ============================================================================

## Install pre-commit hooks
pre-commit-install:
	pre-commit install
	@echo "Pre-commit hooks installed."

## Run pre-commit on all files
pre-commit:
	pre-commit run --all-files
