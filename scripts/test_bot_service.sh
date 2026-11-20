#!/usr/bin/env bash
set -euo pipefail

: "${HEREYOUGO_VM_IP:?HEREYOUGO_VM_IP is not set}"
: "${HEREYOUGO_BOT_PORT:?HEREYOUGO_BOT_PORT is not set}"
: "${HEREYOUGO_USER_ID:?HEREYOUGO_USER_ID is not set}"

MESSAGE="${*:-HereYouGo test message from scripts/test_bot_service.sh}"
URL="http://${HEREYOUGO_VM_IP}:${HEREYOUGO_BOT_PORT}/notify"

curl_args=(
  --fail-with-body
  -sS
  -X POST
  "${URL}"
  -H "Content-Type: text/plain"
  -H "X-HereYouGo-User-ID: ${HEREYOUGO_USER_ID}"
  --data-binary "${MESSAGE}"
)

if [[ -n "${NOTIFY_TOKEN:-}" ]]; then
  curl_args+=(-H "Authorization: Bearer ${NOTIFY_TOKEN}")
fi

curl "${curl_args[@]}"
printf "\n"
