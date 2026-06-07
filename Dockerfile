# HSR Club Dine — backend image. Host-agnostic (Render, Fly, Azure, a VM…).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# Seed the menu/tables on first boot if absent, then start the API.
# $PORT is provided by most PaaS hosts; defaults to 8000 otherwise.
CMD ["sh", "-c", "[ -f data/menu_items.json ] || python -m scripts.seed_data; uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
