#!/usr/bin/env bash
# generated.sh generate|check: images' generated files, written by the
# generator the SDK bundle carries (sdk's codegen, at the commit upstream.lock.json
# pins) from the Protocol this checkout pins. generate writes them into the
# checkout; check writes them into a copy and fails naming each file that
# differs from the committed one, and each committed file that says it is
# generated, or lies in a generated directory, and that no run writes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$ROOT"
source "$ROOT/build-tools/container-runtime.sh"
[[ $# -eq 1 && ( "$1" == generate || "$1" == check ) ]] || { echo "Usage: $0 generate|check" >&2; exit 2; }
bundle="$(bash "$ROOT/build-tools/prepare-sdk-artifacts.sh" codegen)"
RT="$(detect_container_runtime)"
RUST_TOOLCHAIN="$(packages/rust/scripts/rust-toolchain.sh)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

if [[ "$1" == generate ]]; then
  target="$ROOT"
else
  target="$work/images"
  mkdir "$target"
  tar -C "$ROOT" --exclude=./.git --exclude=./.local --exclude=target --exclude=node_modules -cf - . \
    | tar -C "$target" -xf -
fi

# The bundle's copy has lost its mode, so the container installs it to run.
"$RT" run --rm --volume "$target:/images" --volume "$bundle/codegen:/codegen:ro" \
  "rust:$RUST_TOOLCHAIN-bookworm" sh -euc '
  install -m 0755 /codegen/xynolog-codegen /tmp/xynolog-codegen
  /tmp/xynolog-codegen generate images /images' | tee "$work/written"

if [[ "$1" == check ]]; then
  [[ -s "$work/written" ]]
  awk '{print $2}' "$work/written" | sort > "$work/paths"
  drifted=0
  while read -r path; do
    if [[ ! -f "$ROOT/$path" ]]; then
      echo "absent $path"
      drifted=$((drifted + 1))
    elif ! cmp -s "$target/$path" "$ROOT/$path"; then
      echo "DRIFT  $path"
      drifted=$((drifted + 1))
    fi
  done < "$work/paths"
  {
    git grep -l -E '^(//|#) Generated from .*; do not edit\.$' -- '*.rs' '*.py' ':!protocol' ':!build-tools'
    git ls-files -- packages/rust/core/src/generated
  } | sort -u > "$work/claimed"
  while read -r path; do
    echo "unwritten $path: it says it is generated, and no run writes it"
    drifted=$((drifted + 1))
  done < <(comm -23 "$work/claimed" "$work/paths")
  if ((drifted)); then
    echo "$drifted generated files differ from what the generator writes: run make generate" >&2
    exit 1
  fi
fi
