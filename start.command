#!/bin/bash
set -e
cd "$(dirname "$0")"

LOG_FILE="run.log"
VENV_DIR=".venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PORT=8000

touch "$LOG_FILE"

ensure_venv() {
  if [ ! -x "$PYTHON_BIN" ]; then
    if [ -x "/opt/homebrew/bin/python3.11" ]; then
      /opt/homebrew/bin/python3.11 -m venv "$VENV_DIR"
    else
      python3 -m venv "$VENV_DIR"
    fi
  fi
  source "$VENV_DIR/bin/activate"
  python - <<'PY' || python -m pip install -r requirements.txt
try:
    import fastapi  # noqa: F401
    import uvicorn  # noqa: F401
except Exception:
    raise SystemExit(1)
PY
}

find_free_port() {
  if lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
    for p in 8001 8002 8003 8004 8010 8080; do
      if ! lsof -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1; then
        PORT=$p
        break
      fi
    done
  fi
}

start_server() {
  echo "Starting server on port $PORT..." >> "$LOG_FILE"
  nohup "$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" >> "$LOG_FILE" 2>&1 &
}

wait_and_open() {
  for _ in {1..40}; do
    if curl -s "http://127.0.0.1:$PORT/" >/dev/null 2>&1; then
      open "http://127.0.0.1:$PORT/"
      echo "Server ready: http://127.0.0.1:$PORT" >> "$LOG_FILE"
      return 0
    fi
    sleep 0.5
  done
  echo "Server failed to start. Check $LOG_FILE for details." >> "$LOG_FILE"
  return 1
}

ensure_venv
find_free_port

if curl -s "http://127.0.0.1:$PORT/" >/dev/null 2>&1; then
  open "http://127.0.0.1:$PORT/"
  exit 0
fi

start_server
wait_and_open || true

echo ""
echo "If the page did not open, visit: http://127.0.0.1:$PORT"
echo "Log file: $LOG_FILE"
read -p "Press Enter to close this window..."
