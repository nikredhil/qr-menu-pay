#!/usr/bin/env bash
# Convenience launcher: starts the API (8000) and the SPA dev server (5174)
# together, seeding the menu on first run. Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")"

# --- backend ---
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q --upgrade pip
  ./.venv/bin/pip install -q -r requirements.txt
fi
[ -f .env ] || cp .env.example .env
[ -f data/menu_items.json ] || ./.venv/bin/python -m scripts.seed_data

./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# --- frontend ---
cd frontend
[ -d node_modules ] || npm install
[ -f .env ] || cp .env.example .env
npm run dev &
WEB_PID=$!

trap 'kill $API_PID $WEB_PID 2>/dev/null || true' EXIT
echo ""
echo "  API : http://localhost:8000/docs"
echo "  App : http://localhost:5174   (staff: /admin)"
echo ""
wait
