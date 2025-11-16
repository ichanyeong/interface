FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# System deps (optional: for faster cryptography wheels etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY . /app

# Cloud Run provides PORT env. Use Gunicorn to serve Flask app.
# main.py exposes `app` at module level.
CMD exec gunicorn --bind 0.0.0.0:${PORT} --workers=2 --threads=4 --timeout=120 main:app

