FROM python:3.11-slim AS base

WORKDIR /app

# System deps for faiss-cpu's compiled wheel dependencies (libgomp) --
# kept minimal on purpose; this image should stay small since it's what
# scales horizontally in production (see docs/PRODUCTION.md).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY kb ./kb
COPY scripts ./scripts

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
