#!/bin/sh
# image-tags.sh <service> <version> — the image a service publishes to and the
# tags it carries, as GITHUB_OUTPUT lines:
#
#   image  ghcr.io/xynolog/xynolog-<service>
#   tags   <image>:<version>,<image>:sha-<commit>,<image>:latest, since latest
#          moves with each release published
#   sha    the checkout's short commit
#
# One decider for every publishing job that names a tag: publish-browser.yml's,
# and publish-service-images.yml's matrix legs and manifest job, which tags the
# platform images a service's per-architecture legs pushed by digest.
set -eu
USAGE="usage: image-tags.sh <service> <version>"
SERVICE="${1:?$USAGE}"
VERSION="${2:?$USAGE}"
test "$#" -eq 2 || { echo "$USAGE" >&2; exit 2; }
SHA=$(git rev-parse --short HEAD)
IMAGE="ghcr.io/xynolog/xynolog-$SERVICE"
echo "tags=$IMAGE:$VERSION,$IMAGE:sha-$SHA,$IMAGE:latest"
echo "image=$IMAGE"
echo "sha=$SHA"
