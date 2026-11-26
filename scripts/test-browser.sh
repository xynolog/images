#!/usr/bin/env bash
# test-browser.sh — the Browser's checks (`make test-browser`): its tests
# (vitest), the type checks of its sources and of its tests, and stylelint
# over its CSS (browser/.stylelintrc.json), in the Browser's build container
# (scripts/browser-container.sh), against the SDK's npm packages from the SDK
# artifact bundle. Every check runs, and the run
# fails if any did.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
bundle="$(bash "$ROOT/build-tools/prepare-sdk-artifacts.sh" typescript)"

bash "$ROOT/scripts/browser-container.sh" "$bundle" '
    status=0
    npm test || status=1
    npm run typecheck || status=1
    npm run typecheck:test || status=1
    npm run lint:css || status=1
    exit "$status"'
