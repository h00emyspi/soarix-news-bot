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
elif [[ "$MODE" == "collector" ]]; then
  export APP_MODE=collector
else
  export APP_MODE=bot
fi

python -m app
