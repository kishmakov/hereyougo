#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/common.sh"

: "${HEREYOUGO_BOT_PORT:?HEREYOUGO_BOT_PORT is not set}"

SSH_TARGET="${SSH_TARGET:-GC}"
REMOTE_ENV_FILE="${REMOTE_ENV_FILE:-/opt/hereyougo/hereyougo.env}"
REMOTE_DATA_DIR="${REMOTE_DATA_DIR:-/opt/hereyougo/data}"

wait_until_running() {
  for _ in $(seq 1 10); do
    if [[ "$(ssh "${SSH_TARGET}" "docker inspect -f '{{.State.Running}}' '${CONTAINER_NAME}'" 2>/dev/null)" == "true" ]]; then
      sleep 2
      ssh "${SSH_TARGET}" "docker logs --tail 5 '${CONTAINER_NAME}'"
      return 0
    fi
    sleep 1
  done
  echo "Container ${CONTAINER_NAME} is not running on ${SSH_TARGET}" >&2
  ssh "${SSH_TARGET}" "docker logs --tail 20 '${CONTAINER_NAME}'" >&2 || true
  return 1
}

if [[ "${1:-}" == "--restart" ]]; then
  ssh "${SSH_TARGET}" "docker restart '${CONTAINER_NAME}'"
  wait_until_running
  echo "Restarted ${CONTAINER_NAME} on ${SSH_TARGET}"
  exit 0
fi

gcloud auth print-access-token | ssh "${SSH_TARGET}" \
  "docker login -u oauth2accesstoken --password-stdin https://${REGISTRY}"

ssh "${SSH_TARGET}" "test -f '${REMOTE_ENV_FILE}'"
ssh "${SSH_TARGET}" "docker pull '${IMAGE_URI}'"
ssh "${SSH_TARGET}" "docker rm -f '${CONTAINER_NAME}' >/dev/null 2>&1 || true"
ssh "${SSH_TARGET}" "docker run -d \
  --name '${CONTAINER_NAME}' \
  --restart unless-stopped \
  --env-file '${REMOTE_ENV_FILE}' \
  -v '${REMOTE_DATA_DIR}:/data' \
  -p '${HEREYOUGO_BOT_PORT}:${HEREYOUGO_BOT_PORT}' \
  '${IMAGE_URI}'"

wait_until_running
echo "Deployed ${IMAGE_URI} to ${SSH_TARGET} as ${CONTAINER_NAME}"
