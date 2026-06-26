# Multi-stage build — keeps the final image lean
# Stage 1: install deps (layer-cached unless requirements.txt changes)
FROM python:3.11-slim AS deps
WORKDIR /build
COPY backend/requirements.txt .
# ECS extras: postgres async driver + redis
RUN pip install --no-cache-dir -r requirements.txt \
    psycopg[binary] \
    langgraph-checkpoint-postgres \
    redis

# Stage 2: final image
FROM python:3.11-slim
WORKDIR /app

# Copy installed packages from stage 1
COPY --from=deps /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/ ./backend/
COPY deploy/ecs/overrides/config.py ./backend/config.py
COPY deploy/ecs/overrides/main.py ./backend/main.py
COPY deploy/ecs/overrides/api/ws.py ./backend/api/ws.py
COPY deploy/ecs/overrides/db/session.py ./backend/db/session.py

# Non-root user — security best practice
RUN useradd -m appuser
USER appuser

EXPOSE 8000

# ECS health check: ALB pings /health before routing traffic to this task
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
