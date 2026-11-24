# Multi-stage Dockerfile for FastAPI Backend

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
    DATABASE_URL=sqlite:////data/app.db

COPY app/ ./app/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').getcode() == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
