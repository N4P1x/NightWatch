#!/bin/bash
# Night-Watch - Start Script
# Usage: ./start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON="${PYTHON:-python3}"

# Check for virtual environments
if [ -f "$SCRIPT_DIR/backend/venv/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/backend/venv/bin/python"
elif [ -d "$SCRIPT_DIR/venv" ] && [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/venv/bin/python"
fi

echo "[*] Starting Night-Watch..."

# Kill any existing processes
kill_processes() {
    local pids
    pids=$(ps aux | grep -E "(uvicorn.*backend.api.main:app|serve -s dist)" | grep -v grep | awk '{print $2}')
    if [ -n "$pids" ]; then
        echo "[*] Stopping existing processes..."
        kill $pids 2>/dev/null || true
        sleep 2
    fi
}

kill_processes

# Run Alembic migrations
echo "[*] Running database migrations..."
$PYTHON -m alembic -c backend/alembic.ini upgrade head 2>&1 || echo "[!] Migration issue (non-fatal)"

# Seed database
echo "[*] Seeding database..."
$PYTHON -m backend.seed 2>&1 || echo "[!] Seed issue (non-fatal)"

# Start backend
echo "[*] Starting backend on port 8000..."
cd "$SCRIPT_DIR"
$PYTHON -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "[+] Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "[!] Backend failed to start. Check backend.log"
    cat backend.log | tail -20
    exit 1
fi

# Verify backend responds
if curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
    echo "[+] Backend is responding"
else
    echo "[!] Backend not responding. Check backend.log"
    cat backend.log | tail -20
    exit 1
fi

# Start frontend
echo "[*] Starting frontend on port 3000..."
cd "$SCRIPT_DIR/frontend"
if [ ! -d "dist" ]; then
    echo "[*] Building frontend..."
    npm run build
fi
npx serve -s dist -l 3000 --no-clipboard > "$SCRIPT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "[+] Frontend started (PID: $FRONTEND_PID)"

sleep 2

echo ""
echo "==================================="
echo " Night-Watch is running!"
echo "==================================="
echo " Frontend: http://127.0.0.1:3000"
echo " Backend:  http://127.0.0.1:8000"
echo " Docs:     http://127.0.0.1:8000/docs"
echo "==================================="
echo ""
echo " Default login: admin / admin123"
echo ""
echo " To stop: run './stop.sh'"