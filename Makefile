.PHONY: lint-arch lint test fmt up down logs reset-db smoke-infra

COMPOSE = docker compose -f infra/docker-compose.yml

# Hạ tầng cục bộ (PostgreSQL, Redis, MinIO, ClamAV, TEI — SADD §2.3, T-002).
up:
	$(COMPOSE) up -d --wait

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

# Xóa sạch volume rồi dựng lại (bảng/extension được tạo lại từ đầu).
reset-db:
	$(COMPOSE) down -v postgres
	$(COMPOSE) up -d --wait postgres

smoke-infra:
	python scripts/smoke_infra.py

# Kiểm tra ranh giới module back-end (SADD §2.2.1, T-001).
lint-arch:
	cd backend && lint-imports

lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run lint && npm run format:check

fmt:
	cd backend && ruff format .
	cd frontend && npm run format

test:
	cd backend && pytest tests/unit tests/integration -m "not isolation"
	cd frontend && npm test
