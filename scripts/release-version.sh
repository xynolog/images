#!/usr/bin/env bash
# release-version.sh — the release version.json names, as GITHUB_OUTPUT lines:
#
#   version  YY.M.N, the version every image and the Browser package carry
#   tag      v<version>, the signed tag a release runs at
#
# Every release workflow, tagging or publishing, reads it here, and refuses a
# version.json whose version is not YY.M.N: a two-digit year, a month without
# a leading zero, and the release within that month, from 0.
set -euo pipefail
cd "$(dirname "$0")/.."

version="$(python3 -c 'import json; print(json.load(open("version.json"))["version"])')"
if [[ ! "$version" =~ ^[0-9]{2}\.(1[0-2]|[1-9])\.(0|[1-9][0-9]*)$ ]]; then
  echo "version.json's version $version is not YY.M.N: no release is cut from it" >&2
  exit 1
fi
echo "version=$version"
echo "tag=v$version"
