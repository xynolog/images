#!/usr/bin/env bash
# test-python.sh [<project>...] — each Python project's checks
# (`make test-python`): its type checks (mypy and pyright, as its
# pyproject.toml configures them), its lints and format (ruff), and its tests
# (pytest). The projects are the directories that hold a pyproject.toml, or
# those named.
#
# They run in the container scripts/python-checks.Dockerfile builds: the
# oldest Python the pinned SDK wheel supports (shared/python/python-floor.sh),
# uv from the image the Python images copy it from, and what the projects'
# images run beside them. Each runs on a copy of the checkout, with the SDK
# wheel and manifest from the SDK artifact bundle staged where each project's
# [tool.uv.sources] and tests name them (scripts/stage-sdk-artifacts.sh). Each
# project's environment is exactly its uv.lock (`--locked`). Every check of
# every project runs, and the run fails if any did.
#
# uv's cache outlives the container, under the XDG cache's
# xynolog-images/python, so a run downloads only what changed since the last
# one. CI's python job caches that directory.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
source "$ROOT/build-tools/container-runtime.sh"
RT="$(detect_container_runtime)"

if (( $# )); then
  projects=("$@")
else
  projects=()
  while IFS= read -r manifest; do
    projects+=("$(dirname "$manifest")")
  done < <(git ls-files '*pyproject.toml')
fi
for project in "${projects[@]}"; do
  [[ -f "$project/pyproject.toml" && -f "$project/uv.lock" ]] || {
    echo "test-python.sh: $project has no pyproject.toml and uv.lock" >&2
    exit 2
  }
done

# The one image the Dockerfiles after `what` and `pattern` take `what` from, by
# the line `pattern` matches.
one_image() {
  local what="$1" pattern="$2" found
  shift 2
  found="$(sed -n "s|$pattern|\1|p" "$@" | sort -u)"
  [[ -n "$found" && "$found" != *$'\n'* ]] || {
    echo "test-python.sh: $* do not take $what from one image: ${found:-none}" >&2
    exit 2
  }
  printf '%s\n' "$found"
}
dockerfiles=()
for image in $(scripts/image-groups.sh PYTHON_IMAGES); do dockerfiles+=("$image/Dockerfile"); done
uv_image="$(one_image uv '^FROM \(ghcr.io/astral-sh/uv:[^ ]*\) AS uv$' "${dockerfiles[@]}")"
typst_image="$(one_image typst '^COPY --from=\([^ ]*typst[^ ]*\) .*$' worker/Dockerfile)"

bundle="$(bash "$ROOT/build-tools/prepare-sdk-artifacts.sh" python)"
# Staged as the Python images stage it: the wheel, and the SDK's manifest
# beside it, which the projects' census tests read.
staged=".local/sdk-artifacts/$(SDK_ARTIFACTS="$bundle" bash scripts/stage-sdk-artifacts.sh python)"
python_floor="$(shared/python/python-floor.sh "$staged")"

cache="${XDG_CACHE_HOME:-$HOME/.cache}/xynolog-images/python"
mkdir -p "$cache"

"$RT" build \
  --build-arg "PYTHON_FLOOR=$python_floor" \
  --build-arg "UV_IMAGE=$uv_image" \
  --build-arg "TYPST_IMAGE=$typst_image" \
  --tag xynolog-images-python-checks \
  --file scripts/python-checks.Dockerfile scripts

"$RT" run --rm --memory 6g \
  --volume "$ROOT:/source:ro" \
  --volume "$ROOT/$staged/python:/sdk/python:ro" \
  --volume "$cache:/uv-cache" \
  --env UV_CACHE_DIR=/uv-cache \
  --env UV_PYTHON_DOWNLOADS=never \
  xynolog-images-python-checks \
  bash -euc '
    mkdir /tmp/images
    tar -C /source --exclude=.git --exclude=.claude --exclude=.local --exclude=.venv --exclude=node_modules -cf - . \
      | tar -C /tmp/images -xf -
    mkdir -p /tmp/images/.local/sdk-artifacts/current
    cp -a /sdk/python /tmp/images/.local/sdk-artifacts/current/python
    status=0
    for project in "$@"; do
      echo "==> $project"
      cd "/tmp/images/$project"
      if uv sync --locked --quiet; then
        uv run --no-sync mypy || status=1
        uv run --no-sync pyright || status=1
        uv run --no-sync ruff check || status=1
        uv run --no-sync ruff format --check || status=1
        uv run --no-sync pytest || status=1
      else
        status=1
      fi
    done
    exit "$status"' bash "${projects[@]}"
