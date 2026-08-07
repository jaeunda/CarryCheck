#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv-api"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
  echo "Error: $PROJECT_ROOT/.env does not exist. Copy .env.example and add the API values." >&2
  exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install -r "$PROJECT_ROOT/requirements/api.txt"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$VENV_DIR/bin/python" -m airline_baggage_agent.run_api_web "$@"
