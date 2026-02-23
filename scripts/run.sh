#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-bot}"

if [[ ! -d ".venv" ]]; then
  python -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

if [[ "$MODE" == "dashboard" ]]; then
  export APP_MODE=dashboard
fi

python -m app
