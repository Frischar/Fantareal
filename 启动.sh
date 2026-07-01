#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-8000}"
VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN=""

find_python() {
  for candidate in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        return 0
      fi
    fi
  done
  return 1
}

open_url() {
  url="$1"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 || true
  fi
}

if ! find_python; then
  echo "[Error] Python 3.10+ was not found."
  echo "Install Python 3.10 or newer, then run this script again."
  exit 1
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[First run] Creating virtual environment in $VENV_DIR ..."
  if ! "$PYTHON_BIN" -m venv "$VENV_DIR"; then
    echo "[Error] Could not create the virtual environment."
    echo "On Debian/Ubuntu, install python3-venv and try again:"
    echo "  sudo apt install python3-venv"
    exit 1
  fi
fi

VENV_PYTHON="$VENV_DIR/bin/python"

echo "[Startup] Preparing pip ..."
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel

if [ -f "requirements.txt" ]; then
  echo "[Startup] Installing or checking dependencies ..."
  "$VENV_PYTHON" -m pip install -r requirements.txt
else
  echo "[Error] requirements.txt was not found."
  exit 1
fi

if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    echo "[Startup] Creating .env from .env.example ..."
    cp .env.example .env
  else
    echo "[Startup] Creating an empty .env ..."
    : > .env
  fi
fi

URL="http://$APP_HOST:$APP_PORT"
echo "========================================================="
echo " Fantareal WebUI"
echo " URL: $URL"
echo " Host: $APP_HOST"
echo " Port: $APP_PORT"
echo "========================================================="

if [ "${OPEN_BROWSER:-1}" != "0" ]; then
  open_url "$URL"
fi

exec "$VENV_PYTHON" -m uvicorn app:app --reload --host "$APP_HOST" --port "$APP_PORT" --no-access-log
