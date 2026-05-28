#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/common.sh"

: "${HEREYOUGOBOT_PORT:?HEREYOUGOBOT_PORT is not set}"
: "${CHAT_ID:?CHAT_ID is not set}"

docker build \
  --build-arg "HEREYOUGOBOT_PORT=${HEREYOUGOBOT_PORT}" \
  --build-arg "CHAT_ID=${CHAT_ID}" \
  -t "${IMAGE_URI}" \
  "${ROOT_DIR}"
echo "Built ${IMAGE_URI}"
