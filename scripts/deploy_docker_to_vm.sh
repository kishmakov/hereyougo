#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/common.sh"

: "${HEREYOUGOBOT_PORT:?HEREYOUGOBOT_PORT is not set}"

SSH_TARGET="${SSH_TARGET:-GC}"
REMOTE_ENV_FILE="${REMOTE_ENV_FILE:-/opt/hereyougo/hereyougo.env}"

gcloud auth print-access-token | ssh "${SSH_TARGET}" \
  "docker login -u oauth2accesstoken --password-stdin https://${REGISTRY}"

ssh "${SSH_TARGET}" "test -f '${REMOTE_ENV_FILE}'"
ssh "${SSH_TARGET}" "docker pull '${IMAGE_URI}'"
ssh "${SSH_TARGET}" "docker rm -f '${CONTAINER_NAME}' >/dev/null 2>&1 || true"
ssh "${SSH_TARGET}" "docker run -d \
  --name '${CONTAINER_NAME}' \
  --restart unless-stopped \
  --env-file '${REMOTE_ENV_FILE}' \
  -p '${HEREYOUGOBOT_PORT}:${HEREYOUGOBOT_PORT}' \
  '${IMAGE_URI}'"

echo "Deployed ${IMAGE_URI} to ${SSH_TARGET} as ${CONTAINER_NAME}"
