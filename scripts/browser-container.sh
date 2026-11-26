#!/usr/bin/env bash
# browser-container.sh <verified-sdk-bundle-directory> <commands> — run
# <commands> in the Browser's build container, at /tmp/browser: a copy of
# browser/ with its dependencies installed, the SDK's npm packages from the
# bundle among them, and the brand submodule's favicons beside it. The checkout is at /source.
# build-browser-package.sh builds the package there, and test-browser.sh
# checks the Browser there.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SDK_BUNDLE_DIR="${1:?Usage: browser-container.sh <verified-sdk-bundle-directory> <commands>}"
COMMANDS="${2:?Usage: browser-container.sh <verified-sdk-bundle-directory> <commands>}"
[[ -f "$SDK_BUNDLE_DIR/artifacts.json" ]] || {
  echo "SDK artifact manifest not found: $SDK_BUNDLE_DIR/artifacts.json" >&2
  exit 2
}

source "$ROOT/build-tools/container-runtime.sh"
RUNTIME="$(detect_container_runtime)"
"$RUNTIME" run --rm --memory 6g \
  --volume "$ROOT:/source" \
  --volume "$SDK_BUNDLE_DIR:/sdk-bundle:ro" \
  --workdir /tmp \
  node:26-bookworm bash -euc '
    mkdir -p /tmp/browser
    cp -a /source/browser/. /tmp/browser/
    # Beside the app, as in the repository: scripts/copy-favicons.js and the
    # index.html test read brand/favicons there.
    mkdir -p /tmp/brand
    cp -a /source/brand/favicons /tmp/brand/
    # Beside the app, as in the repository: the build reads its version there.
    cp /source/version.json /tmp/version.json
    python3 /source/build-tools/prepare-sdk-package.py /sdk-bundle /tmp/browser/package.json
    cd /tmp/browser
    npm install --no-audit --no-fund
    npm install-scripts approve --all --no-allow-scripts-pin
    npm rebuild
    '"$COMMANDS"
