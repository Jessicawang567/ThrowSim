#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "[run.sh] project root: $ROOT"

# ---------- Backend ----------
echo "[run.sh] setting up backend..."
cd "$ROOT/backend"

if [ ! -d ".venv" ]; then
  echo "[run.sh] creating python venv..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[run.sh] installing backend requirements..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "[run.sh] starting backend (uvicorn on :8000)..."
python main.py &
BACKEND_PID=$!
echo "[run.sh] backend PID: $BACKEND_PID"

deactivate || true

# ---------- Frontend ----------
cd "$ROOT/frontend"

if [ ! -d "node_modules" ]; then
  echo "[run.sh] installing frontend deps..."
  npm install
fi

cleanup() {
  echo "[run.sh] shutting down backend (PID $BACKEND_PID)..."
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[run.sh] starting frontend (vite dev server)..."
if npm run | grep -qE '^\s*dev'; then
  npm run dev
else
  npm start
fi

wait
