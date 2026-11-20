#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/common.sh"

: "${HEREYOUGO_BOT_PORT:?HEREYOUGO_BOT_PORT is not set}"

docker build \
  --build-arg "HEREYOUGO_BOT_PORT=${HEREYOUGO_BOT_PORT}" \
  -t "${IMAGE_URI}" \
  "${ROOT_DIR}"
echo "Built ${IMAGE_URI}"
