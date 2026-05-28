#!/usr/bin/env bash
set -euo pipefail

: "${GC_VM_IP:?GC_VM_IP is not set}"
: "${HEREYOUGOBOT_PORT:?HEREYOUGOBOT_PORT is not set}"

MESSAGE="${*:-HereYouGo test message from scripts/test_bot_service.sh}"
URL="http://${GC_VM_IP}:${HEREYOUGOBOT_PORT}/notify"

curl_args=(
  --fail-with-body
  -sS
  -X POST
  "${URL}"
  -H "Content-Type: text/plain"
  --data-binary "${MESSAGE}"
)

if [[ -n "${NOTIFY_TOKEN:-}" ]]; then
  curl_args+=(-H "Authorization: Bearer ${NOTIFY_TOKEN}")
fi

curl "${curl_args[@]}"
printf "\n"
