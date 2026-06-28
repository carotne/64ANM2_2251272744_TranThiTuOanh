#!/usr/bin/env bash
# Package the FastAPI Lambda code with its Python dependencies for `terraform apply`.
# Output: backend/dist/  (consumed by the lambda module's archive_file)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${ROOT_DIR}/dist"

rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

cp -r "${ROOT_DIR}/app" "${DIST_DIR}/"
cp "${ROOT_DIR}/lambda_handler.py" "${DIST_DIR}/"

python -m pip install \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --implementation cp \
    --python-version 3.12 \
    --target "${DIST_DIR}" \
    --upgrade \
    -r "${ROOT_DIR}/requirements.txt"

find "${DIST_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} +
# NOTE: do NOT strip *.dist-info — packages such as email-validator read their own
# version via importlib.metadata at import time and crash without the metadata.

echo "Lambda artifact prepared at ${DIST_DIR}"
