#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/common.sh"

if ! gcloud artifacts repositories describe "${REPOSITORY}" \
  --location="${REGION}" \
  --project="${GC_PROJECT_ID}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${REPOSITORY}" \
    --repository-format=docker \
    --location="${REGION}" \
    --project="${GC_PROJECT_ID}" \
    --description="HereYouGo Docker images"
fi

gcloud auth configure-docker "${REGISTRY}" --quiet
docker push "${IMAGE_URI}"
echo "Pushed ${IMAGE_URI}"
