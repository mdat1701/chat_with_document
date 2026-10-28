.PHONY: lint-arch lint test fmt

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
