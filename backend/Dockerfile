# Image dùng chung cho `api` và `worker` — chỉ khác CMD (SADD §4.4, T-003).
# Multi-stage, tối giản, KHÔNG chạy bằng root.

FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim AS runtime
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin appuser
WORKDIR /app

COPY --from=builder /install /usr/local
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

USER 10001
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Mặc định chạy api; worker/beat override CMD khi triển khai
# (SADD §4.4, docker-compose.yml service worker/beat — T-006).
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
