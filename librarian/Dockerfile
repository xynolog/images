# The librarian image: the Librarian service (librarian, Python) and the
# five packages of this repository it runs on, built here from the
# repository, in an environment of exactly what librarian/uv.lock pins.
# Nothing is built, installed or fetched when the container starts: the
# entrypoint runs the service.
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
# The SDK wheel is built and pinned by the SDK repository. The graph stores,
# vector stores, inference drivers and shared service packages are owned here.
COPY .local/sdk-artifacts/${SDK_ARTIFACT_BUNDLE}/python/*.whl /build/.local/sdk-artifacts/current/python/
COPY .local/shared-python-packages/*.whl /build/.local/shared-python-packages/
COPY shared/python/graph/pyproject.toml shared/python/graph/README.md shared/python/graph/
COPY shared/python/graph/src shared/python/graph/src
COPY shared/python/vectors/pyproject.toml shared/python/vectors/README.md shared/python/vectors/
COPY shared/python/vectors/src shared/python/vectors/src
COPY shared/python/inference/pyproject.toml shared/python/inference/README.md shared/python/inference/
COPY shared/python/inference/src shared/python/inference/src
COPY shared/python/service/pyproject.toml shared/python/service/
COPY shared/python/service/src shared/python/service/src
COPY librarian/pyproject.toml librarian/uv.lock librarian/
COPY librarian/src librarian/src
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
# tools out, and --no-editable installs the six packages above as built
# wheels, so the environment is whole without this stage's tree.
#
# --all-extras is every graph database's client and every provider's library:
# each extra of xynolog-librarian brings the extra of the same name of the
# graph stores or of the inference drivers, and with it the client that
# database is asked through or the library that provider is asked through. An
# image for one database and one provider names those two extras in its place
# (`--extra neo4j --extra anthropic`), and one whose models are Ollama's names
# the database's alone: Ollama is asked with what every install has. The
# vector index and the embedding providers are asked over HTTP, with what
# every install has too.
RUN uv sync --project librarian --locked --no-dev --no-editable --all-extras \
      --no-install-package xynolog \
      --no-install-package xynolog-graph \
      --no-install-package xynolog-inference \
      --no-install-package xynolog-service \
      --no-install-package xynolog-vectors && \
    uv pip install --python /opt/venv/bin/python --no-deps \
      .local/sdk-artifacts/current/python/xynolog-1.2611.0.dev20261120131050+g548e4fb-py3-none-any.whl \
      .local/shared-python-packages/xynolog_graph-*.whl \
      .local/shared-python-packages/xynolog_inference-*.whl \
      .local/shared-python-packages/xynolog_service-*.whl \
      .local/shared-python-packages/xynolog_vectors-*.whl

FROM python:${PYTHON_FLOOR}-alpine
# Patch base-image OS packages so Alpine's security fixes apply even when the
# base's snapshot has not been rebuilt against them yet.
RUN apk upgrade --no-cache && apk add --no-cache tini
# Nothing is installed in the image once it is built, so it carries no
# installer.
RUN pip uninstall --yes --root-user-action=ignore pip

# The uid every service image runs as. The Librarian mounts nothing: what it
# reads of the record and of its principals' profiles it asks the Archivist
# on the bus.
RUN addgroup --system --gid 1001 xynolog && \
    adduser --system --uid 1001 --ingroup xynolog --home /home/xynolog xynolog

COPY --from=builder /opt/venv /opt/venv

COPY LICENSE librarian/NOTICE /home/xynolog/

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
EXPOSE 24104

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://localhost:24104/health || exit 1

ENV SUPERVISE_NAME=librarian \
    SUPERVISE_PROBE=http://localhost:24104/health
ENTRYPOINT ["/sbin/tini", "--", "/usr/local/bin/boot.sh"]
# --config names where the launcher mounts the Librarian's document; the
# launcher's census (TestConfigDocumentsAreWhereTheImagesLook) reads it here.
# `-P` keeps the working directory off the import path: a file in /kb is never
# a module the service imports.
CMD ["python", "-P", "-m", "xynolog_librarian", "--config", "/etc/xynolog/librarian.json"]
