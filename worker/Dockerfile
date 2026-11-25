# The worker image: the Worker service (worker, Python) and the three
# packages of this repository it runs on, built here from the repository, in
# an environment of exactly what worker/uv.lock pins. Nothing is built,
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
# The SDK wheel is built and pinned by the SDK repository. The inference
# drivers and shared service packages are owned here.
COPY .local/sdk-artifacts/${SDK_ARTIFACT_BUNDLE}/python/*.whl /build/.local/sdk-artifacts/current/python/
COPY .local/shared-python-packages/*.whl /build/.local/shared-python-packages/
COPY shared/python/inference/pyproject.toml shared/python/inference/README.md shared/python/inference/
COPY shared/python/inference/src shared/python/inference/src
COPY shared/python/service/pyproject.toml shared/python/service/
COPY shared/python/service/src shared/python/service/src
COPY worker/pyproject.toml worker/uv.lock worker/
COPY worker/src worker/src
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
# --all-extras is every provider's library: each extra of xynolog-worker
# brings the inference drivers' extra of the same name, and with it the
# library that provider is asked through. An image for one provider names
# that provider's extra in its place (`--extra anthropic`), and one for Ollama
# alone names none: Ollama is asked with what every install has.
RUN uv sync --project worker --locked --no-dev --no-editable --all-extras \
      --no-install-package xynolog \
      --no-install-package xynolog-inference \
      --no-install-package xynolog-service && \
    uv pip install --python /opt/venv/bin/python --no-deps \
      .local/sdk-artifacts/current/python/xynolog-1.2611.0.dev20261120131050+g548e4fb-py3-none-any.whl \
      .local/shared-python-packages/xynolog_inference-*.whl \
      .local/shared-python-packages/xynolog_service-*.whl

FROM python:${PYTHON_FLOOR}-alpine
# Patch base-image OS packages so Alpine's security fixes apply even when the
# base's snapshot has not been rebuilt against them yet.
RUN apk upgrade --no-cache && apk add --no-cache tini
# Nothing is installed in the image once it is built, so it carries no
# installer.
RUN pip uninstall --yes --root-user-action=ignore pip

# The uid the launcher's state mount is written as, as in every service image.
RUN addgroup --system --gid 1001 xynolog && \
    adduser --system --uid 1001 --ingroup xynolog --home /home/xynolog xynolog

COPY --from=builder /opt/venv /opt/venv

# Typst renderer for PDF generation. Pinned to the
# version whose PDF text-layer geometry was measured — the recorded citation
# geometry is a property of this version's layout. Alpine/musl build, same
# libc as this base. The binary embeds its default Latin fonts (Libertinus,
# SIL OFL), which covers en/es/de/fr with no separate font files; non-Latin
# scripts have no font in this image. Every
# invocation must pin --creation-timestamp — unpinned compiles change bytes on
# identical input, which churns content checksums and re-embeds forever
# (smelter axioms S11/S12).
# Attribution lives in NOTICE (Apache-2.0 + the embedded font licenses, which
# no scanner can see inside a bare binary) — bump the version there in the
# same diff as this tag.
COPY --from=ghcr.io/typst/typst:0.15.1 /bin/typst /usr/local/bin/typst

COPY LICENSE worker/NOTICE /home/xynolog/

# The model catalogue: what models.dev says each model of Google, OpenAI and
# Together can take, which those providers' own APIs do not say. A model of one
# of them is asked with these facts, and the service's document names this
# path (modelCatalogue). It is the repository's one generated copy, made by
# shared/python/inference/scripts/generate-model-catalogue.mjs from the npm package
# shared/python/inference/package.json pins, and held to that pin by CI's drift job. Nothing is fetched
# to build it here. Its licence notice goes with it.
COPY shared/python/inference/tests/catalogue/model-catalogue.json /usr/share/xynolog/model-catalogue.json
COPY shared/python/inference/tests/catalogue/model-catalogue.LICENSE /usr/share/xynolog/model-catalogue.LICENSE
COPY shared/supervise.sh /usr/local/bin/supervise.sh
COPY shared/boot.sh /usr/local/bin/boot.sh

WORKDIR /kb
RUN chown xynolog:xynolog /kb

USER xynolog

# `python` is the environment's.
ENV PATH=/opt/venv/bin:$PATH
EXPOSE 24100

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://localhost:24100/health || exit 1

ENV SUPERVISE_NAME=worker \
    SUPERVISE_PROBE=http://localhost:24100/health
ENTRYPOINT ["/sbin/tini", "--", "/usr/local/bin/boot.sh"]
# --config names where the launcher mounts the worker's document; the
# launcher's census (TestConfigDocumentsAreWhereTheImagesLook) reads it here.
# `-P` keeps the working directory off the import path: a file in /kb is never
# a module the service imports.
CMD ["python", "-P", "-m", "xynolog_worker", "--config", "/etc/xynolog/worker.json"]
