#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# The Makefile's groups: which images there are, and each one's SDK language.
rust_images="$(scripts/image-groups.sh RUST_IMAGES)"
typescript_images="$(scripts/image-groups.sh TYPESCRIPT_IMAGES)"
python_images="$(scripts/image-groups.sh PYTHON_IMAGES)"
every_image="$(scripts/image-groups.sh IMAGE_NAMES)"

usage() {
  echo "Usage: $0 [all|${every_image// /|}] ..." >&2
  exit 2
}

# language_of <image>: the SDK language of the group that names it.
language_of() {
  if [[ " $rust_images " == *" $1 "* ]]; then echo rust
  elif [[ " $typescript_images " == *" $1 "* ]]; then echo typescript
  elif [[ " $python_images " == *" $1 "* ]]; then echo python
  else usage
  fi
}

if [[ $# -eq 0 ]]; then set -- all; fi
if [[ "$1" == all ]]; then
  [[ $# -eq 1 ]] || usage
  read -r -a every <<< "$every_image"
  set -- "${every[@]}"
fi

source "$REPO_ROOT/build-tools/container-runtime.sh"
RT="$(detect_container_runtime)"
RUST_TOOLCHAIN="$(packages/rust/scripts/rust-toolchain.sh)"
VERSION="$(python3 -c 'import json; print(json.load(open("version.json"))["version"])')"

languages=()
for service in "$@"; do
  language="$(language_of "$service")"
  languages+=("$language")
done
languages_csv="$(printf '%s\n' "${languages[@]}" | sort -u | paste -sd, -)"
if [[ ",$languages_csv," == *,python,* ]]; then
  bash "$REPO_ROOT/scripts/build-shared-python.sh" --ensure
  shared_output="${XDG_CACHE_HOME:-$HOME/.cache}/xynolog-images/local/python/packages"
  shared_staging="$REPO_ROOT/.local/shared-python-packages"
  rm -rf "$shared_staging"
  mkdir -p "$shared_staging"
  cp "$shared_output"/*.whl "$shared_staging/"
fi
IFS=, read -r -a selected_languages <<< "$languages_csv"
bundle="$(bash "$REPO_ROOT/build-tools/prepare-sdk-artifacts.sh" "${selected_languages[@]}")"
bundle_id="$(SDK_ARTIFACTS="$bundle" bash "$REPO_ROOT/scripts/stage-sdk-artifacts.sh" "${selected_languages[@]}")"
bundle_dir=".local/sdk-artifacts/$bundle_id"
if [[ ",$languages_csv," == *,python,* ]]; then
  PYTHON_FLOOR="$(shared/python/python-floor.sh "$bundle_dir")"
fi

for service in "$@"; do
  language="$(language_of "$service")"
  case "$language" in
    rust)
      args=(--build-arg "RUST_TOOLCHAIN=$RUST_TOOLCHAIN" --build-arg "SDK_ARTIFACT_BUNDLE=$bundle_id")
      # A runner starts with an empty build cache, so on GitHub Actions the Rust
      # images' layers, the compiled dependencies among them, come from and go
      # to GitHub's cache (buildx exports it only after a build that succeeds).
      # The workflow exposes the runtime token buildx's gha cache needs.
      if [[ "${GITHUB_ACTIONS:-}" == true && "$RT" == docker ]]; then
        args+=(--cache-from type=gha,scope=rust-builder --cache-to type=gha,scope=rust-builder,mode=max)
      fi
      ;;
    python) args=(--build-arg "PYTHON_FLOOR=$PYTHON_FLOOR" --build-arg "SDK_ARTIFACT_BUNDLE=$bundle_id") ;;
    typescript)
      bash "$REPO_ROOT/scripts/build-browser-package.sh" "$REPO_ROOT/$bundle_dir"
      args=(--build-arg "XYNOLOG_BROWSER_VERSION=$VERSION" --build-arg "BROWSER_PACKAGE_DIR=.local/browser-package")
      ;;
  esac
  tag="ghcr.io/xynolog/xynolog-$service:local"
  echo "Building $tag using $RT"
  "$RT" build "${args[@]}" --file "$service/Dockerfile" --tag "$tag" .
done

echo "Built image version $VERSION locally. No image was pushed."
