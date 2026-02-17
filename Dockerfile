# Multi-stage build – production-ready, ~180 MB final image (2026 best practice)
FROM python:3.12-slim AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.12-slim
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy your code
COPY codebase_context_oracle.py oracle_server.py ./

# Volume for persistent index
VOLUME ["/app/.oracle_index"]

EXPOSE 8000

# Production: gunicorn + uvicorn workers (recommended for 2026)
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "oracle_server:app"]
