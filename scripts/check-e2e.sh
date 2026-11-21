#!/usr/bin/env bash
# check-e2e.sh — e2e's type check (`make check-e2e`): its specs, fixtures and
# scripts compile against the SDK's npm packages from the SDK artifact bundle,
# in a Node container. The specs themselves run against a booted stack
# (`make e2e`).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
bundle="$(bash "$ROOT/build-tools/prepare-sdk-artifacts.sh" typescript)"

source "$ROOT/build-tools/container-runtime.sh"
RUNTIME="$(detect_container_runtime)"
"$RUNTIME" run --rm --memory 6g \
  --volume "$ROOT:/source:ro" \
  --volume "$bundle:/sdk-bundle:ro" \
  --workdir /tmp \
  node:26-bookworm bash -euc '
    cp -a /source/e2e /tmp/e2e
    rm -rf /tmp/e2e/node_modules
    python3 /source/build-tools/prepare-sdk-package.py /sdk-bundle /tmp/e2e/package.json
    cd /tmp/e2e
    npm install --no-audit --no-fund --ignore-scripts
    npm run typecheck'
