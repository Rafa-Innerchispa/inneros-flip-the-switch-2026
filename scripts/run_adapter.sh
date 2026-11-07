#!/usr/bin/env bash
set -euo pipefail

MODULE_DIR=/home/rlopez/inneros/modules/switch-liveops
ENV_FILE="$MODULE_DIR/compose/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env file not found at $ENV_FILE" >&2
  exit 1
fi

ADMIN_PASS=$(grep '^GATEWAY_ADMIN_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)
ADMIN_EMAIL=$(grep '^GATEWAY_ADMIN_EMAIL=' "$ENV_FILE" | cut -d= -f2-)

export PYTHONPATH="$MODULE_DIR/src:${PYTHONPATH:-}"
export LOCAL_MODEL_URL="http://127.0.0.1:8000/v1"

exec "$MODULE_DIR/venv/bin/python3" -m inneros_incident_room.connector \
  --switch-url "http://127.0.0.1:62326" \
  --admin-email "$ADMIN_EMAIL" \
  --admin-password "$ADMIN_PASS" \
  --room "inneros-live-operations" \
  --agent "inneros-incident-triage" \
  --node-id "AMD-1.5" \
  --llm-url "http://127.0.0.1:8000/v1"
