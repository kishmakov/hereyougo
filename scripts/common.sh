#!/usr/bin/env bash
set -euo pipefail

HEREYOUGO_PROJECT_ID="${HEREYOUGO_PROJECT_ID:?HEREYOUGO_PROJECT_ID is not set}"

REGION="us-central1"
REPOSITORY="hereyougo"
IMAGE_NAME="hereyougo"
CONTAINER_NAME="hereyougo"
TAG="${TAG:-latest}"

REGISTRY="${REGION}-docker.pkg.dev"
IMAGE_URI="${REGISTRY}/${HEREYOUGO_PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"
