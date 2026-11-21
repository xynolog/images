# The weaver image: the Weaver service (weaver, Python) and the three
# packages of this repository it runs on, built here from the repository, in
# an environment of exactly what weaver/uv.lock pins. Nothing is built,
# installed or fetched when the container starts: the entrypoint runs the
# service.
#
# Built from the repository root, on the oldest Python the repository's Python
# packages support, which the pinned SDK wheel's metadata states:
#
#   --build-arg PYTHON_FLOOR=$(shared/python/python-floor.sh .local/sdk-artifacts/current)
#
# There is no default: without it a FROM names no image and the build stops,
# rather than building on a Python nothing pinned.
ARG PYTHON_FLOOR

# uv makes the environment, in the builder stage alone.
FROM ghcr.io/astral-sh/uv:0.13.9 AS uv

FROM python:${PYTHON_FLOOR}-alpine AS builder
ARG SDK_ARTIFACT_BUNDLE
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /build
# Each package below takes its version from version.json when it is built.
COPY version.json ./
# The SDK, the graph stores and what every Python service is built on are
# this repository's, and no index holds the version the service is written
# against: each is built from its manifest, the README its manifest names,
# where it names one, and its source.
COPY .local/sdk-artifacts/${SDK_ARTIFACT_BUNDLE}/python/*.whl /build/.local/sdk-artifacts/current/python/
COPY .local/shared-python-packages/*.whl /build/.local/shared-python-packages/
COPY shared/python/graph/pyproject.toml shared/python/graph/README.md shared/python/graph/
COPY shared/python/graph/src shared/python/graph/src
COPY shared/python/service/pyproject.toml shared/python/service/
COPY shared/python/service/src shared/python/service/src
COPY weaver/pyproject.toml weaver/uv.lock weaver/
COPY weaver/src weaver/src
# The environment is made on this stage's Python and no other, with its
# bytecode written here: the image's user cannot write it. uv keeps no cache,
# and the stage mounts none: from a cache that outlives a build, uv installs
# the wheel it built of a package's earlier sources when only its sources have
# changed since.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    UV_COMPILE_BYTECODE=1
# What the lockfile pins and nothing else: --locked refuses a lockfile that no
# longer agrees with the manifests, --no-dev leaves the checkers and the tests'
# tools out, and --no-editable installs the four packages above as built
# wheels, so the environment is whole without this stage's tree.
#
# --all-extras is every graph database's client: each extra of xynolog-weaver
# brings the graph stores' extra of the same name, and with it the client
# that database is asked through. An image for one database names that
# database's extra in its place (`--extra neo4j`).
RUN uv sync --project weaver --locked --no-dev --no-editable --all-extras \
      --no-install-package xynolog \
      --no-install-package xynolog-graph \
      --no-install-package xynolog-service && \
    uv pip install --python /opt/venv/bin/python --no-deps \
      .local/sdk-artifacts/current/python/xynolog-1.2611.0.dev20261120131050+g548e4fb-py3-none-any.whl \
      .local/shared-python-packages/xynolog_graph-*.whl \
      .local/shared-python-packages/xynolog_service-*.whl

FROM python:${PYTHON_FLOOR}-alpine
# Patch base-image OS packages so Alpine's security fixes apply even when the
# base's snapshot has not been rebuilt against them yet.
RUN apk upgrade --no-cache && apk add --no-cache tini
# Nothing is installed in the image once it is built, so it carries no
# installer.
RUN pip uninstall --yes --root-user-action=ignore pip

# The uid every service image runs as.
RUN addgroup --system --gid 1001 xynolog && \
    adduser --system --uid 1001 --ingroup xynolog --home /home/xynolog xynolog

COPY --from=builder /opt/venv /opt/venv

COPY LICENSE weaver/NOTICE /home/xynolog/
COPY shared/supervise.sh /usr/local/bin/supervise.sh
COPY shared/boot.sh /usr/local/bin/boot.sh

WORKDIR /kb
RUN chown xynolog:xynolog /kb

USER xynolog

# `python` is the environment's.
ENV PATH=/opt/venv/bin:$PATH
EXPOSE 24102

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://localhost:24102/health || exit 1

ENV SUPERVISE_NAME=weaver \
    SUPERVISE_PROBE=http://localhost:24102/health
ENTRYPOINT ["/sbin/tini", "--", "/usr/local/bin/boot.sh"]
# --config names where the launcher mounts the Weaver's document; the
# launcher's census (TestConfigDocumentsAreWhereTheImagesLook) reads it here.
# `-P` keeps the working directory off the import path: a file in /kb is never
# a module the service imports.
CMD ["python", "-P", "-m", "xynolog_weaver", "--config", "/etc/xynolog/weaver.json"]
