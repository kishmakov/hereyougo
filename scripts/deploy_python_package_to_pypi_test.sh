#!/usr/bin/env bash
# Build, test and upload the hereyougo Python package to TestPyPI.
# Set SKIP_UPLOAD=1 to only build and test.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="${ROOT_DIR}/python-package"
TEST_PYPI_URL="https://test.pypi.org/legacy/"

# Baked into the package by setup.py.
: "${HEREYOUGO_VM_IP:?HEREYOUGO_VM_IP is not set}"
: "${HEREYOUGO_BOT_PORT:?HEREYOUGO_BOT_PORT is not set}"
if [[ -z "${SKIP_UPLOAD:-}" ]]; then
  : "${PYPI_TEST_TOKEN_NAME:?PYPI_TEST_TOKEN_NAME is not set}"
  : "${PYPI_TEST_TOKEN_VALUE:?PYPI_TEST_TOKEN_VALUE is not set}"
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT

echo "==> Creating build environment"
python3 -m venv "${WORK_DIR}/venv"
PYTHON="${WORK_DIR}/venv/bin/python"
"${PYTHON}" -m pip install --quiet --upgrade pip build twine

echo "==> Building package"
rm -rf "${PACKAGE_DIR}/dist" "${PACKAGE_DIR}/build" "${PACKAGE_DIR}"/src/*.egg-info
"${PYTHON}" -m build "${PACKAGE_DIR}"
"${PYTHON}" -m twine check --strict "${PACKAGE_DIR}"/dist/*

echo "==> Testing built wheel"
"${PYTHON}" -m pip install --quiet "${PACKAGE_DIR}"/dist/*.whl
# Run outside the source tree so the installed wheel is what gets tested.
(
  cd "${WORK_DIR}"
  "${PYTHON}" -c 'import hereyougo._server as s; assert s.HOST and s.PORT, "server address not baked"'
  "${PYTHON}" -m unittest discover -s "${PACKAGE_DIR}/tests" -t "${PACKAGE_DIR}/tests" -v
)

if [[ -n "${SKIP_UPLOAD:-}" ]]; then
  echo "==> SKIP_UPLOAD is set, not uploading"
  exit 0
fi

echo "==> Uploading to TestPyPI using token '${PYPI_TEST_TOKEN_NAME}'"
# PyPI API tokens always authenticate with the username "__token__".
TWINE_USERNAME="__token__" \
TWINE_PASSWORD="${PYPI_TEST_TOKEN_VALUE}" \
  "${PYTHON}" -m twine upload \
    --non-interactive \
    --repository-url "${TEST_PYPI_URL}" \
    "${PACKAGE_DIR}"/dist/*

echo "Deployed to https://test.pypi.org/project/hereyougo/"
