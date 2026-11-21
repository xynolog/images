#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SDK_BUNDLE_DIR="${1:?Usage: build-browser-package.sh <verified-sdk-bundle-directory>}"
mkdir -p "$ROOT/.local/browser-package" "$ROOT/.local/browser-lock"

bash "$ROOT/scripts/browser-container.sh" "$SDK_BUNDLE_DIR" '
    mkdir -p /tmp/browser-publish
    npm run build
    # The lock this install resolved, for the advisory scan; nothing commits one.
    cp /tmp/browser/package-lock.json /source/.local/browser-lock/package-lock.json
    cp /source/browser/server.js /tmp/browser-publish/server.js
    # The package takes the version in version.json, the browser image version.
    node -e '"'"'const fs = require("node:fs"); const p = JSON.parse(fs.readFileSync("/source/browser/package.publish.json", "utf8")); p.version = JSON.parse(fs.readFileSync("/source/version.json", "utf8")).version; fs.writeFileSync("/tmp/browser-publish/package.json", JSON.stringify(p, null, 2) + "\n");'"'"'
    cp -a /tmp/browser/dist /tmp/browser-publish/dist
    cd /tmp
    npm pack /tmp/browser-publish --pack-destination /source/.local/browser-package
  '
