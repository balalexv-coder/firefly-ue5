#!/usr/bin/env bash
# Запуск dialogue server на Linux/macOS/WSL.

set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "[!] .venv not found. Creating..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

if [ ! -f .env ]; then
    echo "[!] .env not found — copying .env.example"
    cp .env.example .env
fi

echo ""
echo "Starting Firefly Dialogue Server on http://127.0.0.1:8765"
echo "Docs: http://127.0.0.1:8765/docs"
echo "Ctrl+C to stop."
echo ""

exec python -m uvicorn server:app --host 127.0.0.1 --port 8765
