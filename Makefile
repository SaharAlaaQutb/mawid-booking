
.DEFAULT_GOAL := help

.PHONY: help install backend-install frontend-install dev down logs \
	backend-lint backend-format backend-typecheck backend-test \
	frontend-lint frontend-format frontend-typecheck frontend-test frontend-i18n-check \
	lint format typecheck test i18n-check check

help:
	@echo "Mawid development commands"
	@echo ""
	@echo "  make install              Install backend and frontend dependencies"
	@echo "  make dev                  Run the full Docker Compose stack"
	@echo "  make down                 Stop the stack"
	@echo "  make test                 Run backend and frontend tests"
	@echo "  make lint                 Run all linters"
	@echo "  make typecheck            Run mypy and tsc"
	@echo "  make i18n-check           Check translation key parity"
	@echo "  make check                Run lint, typecheck, tests, and i18n checks"

install: backend-install frontend-install

backend-install:
	cd backend && uv sync

frontend-install:
	cd frontend && npm install

dev:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

backend-lint:
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .

backend-format:
	cd backend && uv run ruff format .
	cd backend && uv run ruff check --fix .

backend-typecheck:
	cd backend && uv run mypy apps config

backend-test:
	cd backend && uv run pytest

frontend-lint:
	cd frontend && npm run lint
	cd frontend && npm run format:check

frontend-format:
	cd frontend && npm run format

frontend-typecheck:
	cd frontend && npm run typecheck

frontend-test:
	cd frontend && npm test

frontend-i18n-check:
	cd frontend && npm run i18n:check

lint: backend-lint frontend-lint

format: backend-format frontend-format

typecheck: backend-typecheck frontend-typecheck

test: backend-test frontend-test

i18n-check: frontend-i18n-check

check: lint typecheck test i18n-check
