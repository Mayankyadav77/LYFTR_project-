# Production Dockerfile for FastAPI Backend on Render / Cloud platforms
FROM python:3.11-slim

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies system-wide
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create /data directory for persistent SQLite database
RUN mkdir -p /data && chmod 777 /data

# Create symlink so any cached command looking for /home/appuser/.local/bin/uvicorn will succeed
RUN mkdir -p /home/appuser/.local/bin && \
    ln -s /usr/local/bin/uvicorn /home/appuser/.local/bin/uvicorn

# Copy application source code
COPY app/ ./app/

ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/app.db \
    PORT=8000 \
    PATH="/usr/local/bin:/home/appuser/.local/bin:${PATH}"

EXPOSE 8000

# Execute uvicorn via python -m with dynamic PORT evaluation
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
