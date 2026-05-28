#!/usr/bin/env bash
set -euo pipefail

GC_PROJECT_ID="${GC_PROJECT_ID:?GC_PROJECT_ID is not set}"

REGION="us-central1"
REPOSITORY="hereyougo"
IMAGE_NAME="hereyougo"
CONTAINER_NAME="hereyougo"
TAG="${TAG:-latest}"
CHAT_ID="100021"

REGISTRY="${REGION}-docker.pkg.dev"
IMAGE_URI="${REGISTRY}/${GC_PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"
