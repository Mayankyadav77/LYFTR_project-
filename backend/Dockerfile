# Multi-stage Dockerfile for FastAPI Backend (Production & Render compatible)

# Stage 1: Build & Dependencies
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final Runtime
FROM python:3.11-slim as runner

WORKDIR /app

# Create a non-root user and /data directory for SQLite volume
RUN addgroup --system appgroup && adduser --system --group appuser \
    && mkdir -p /data && chown -R appuser:appgroup /data

# Copy installed python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/app.db \
    PORT=8000

COPY app/ ./app/

USER appuser

EXPOSE 8000

# Run with shell form so $PORT is evaluated dynamically by Render
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
