# The container scripts/test-python.sh runs each Python project's checks in:
# the oldest Python the pinned SDK wheel supports, with what the projects'
# images run beside it. uv is the one the Python images build with, the typst
# compiler is the worker's, and Tesseract with its English data is the
# smelter's. pyright is a Node program, and its Python wrapper runs the node
# it finds on PATH. test-python.sh derives each argument from the images'
# Dockerfiles and the SDK wheel; there is no default.
ARG PYTHON_FLOOR
ARG UV_IMAGE
ARG TYPST_IMAGE

FROM ${UV_IMAGE} AS uv
FROM ${TYPST_IMAGE} AS typst

FROM python:${PYTHON_FLOOR}-bookworm
COPY --from=uv /uv /usr/local/bin/uv
COPY --from=typst /bin/typst /usr/local/bin/typst
RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends nodejs tesseract-ocr tesseract-ocr-eng && \
    rm -rf /var/lib/apt/lists/*
