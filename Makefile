.DEFAULT_GOAL := build

# Each image by the language of the SDK it builds against: the one place the
# groups are written (scripts/image-groups.sh reads them). The Rust images share
# one compile of the Rust workspace; the Python images, the shared Python packages.
RUST_IMAGES := gateway archivist dispatcher
TYPESCRIPT_IMAGES := browser
PYTHON_IMAGES := librarian smelter weaver worker
IMAGE_NAMES := $(RUST_IMAGES) $(TYPESCRIPT_IMAGES) $(PYTHON_IMAGES)

.PHONY: help build shared clean $(IMAGE_NAMES) generate check-generated test-rust test-python test-browser check-e2e stack-up e2e stack-down smoke

# `make help` prints the `##` lines below, in order (build-tools/make-help.awk).
##@ Xynolog Images: make [target] [VARIABLE=value ...]
##@ Variables
## CONTAINER_RUNTIME=name: container|docker|podman; else the first to respond
CONTAINER_RUNTIME ?=
## SDK_REPO=path: The SDK checkout that builds and resolves artifacts when SDK_ARTIFACTS is unset
SDK_REPO ?= ../sdk
## SDK_ARTIFACTS=path: Use and verify this SDK artifact bundle instead
## SMOKE_TAG=tag: The image tag stack-up and smoke run
SMOKE_TAG ?= local
## E2E_SCRIPT=name: The E2E npm script
E2E_SCRIPT ?= test:ci
## E2E_MODEL=id: The E2E KB's model; else the one init picks
E2E_MODEL ?=
## E2E_ARGS=words: Extra Playwright arguments, after --
E2E_ARGS ?=
## XYNOLOG=path: The xynolog executable; else the one on PATH
XYNOLOG ?=
export CONTAINER_RUNTIME SDK_REPO XYNOLOG

help:
	@awk -v list="$(IMAGE_NAMES)" -f build-tools/make-help.awk Makefile Makefile

##@ Build locally (images are not pushed)
## build: Every image
build: shared
	@./scripts/build-session.sh all

## shared: The shared Python distributions the Python images install, under the XDG cache's xynolog-images/local/python/packages
shared:
	@./scripts/build-shared-python.sh

## <image>: One image: <list>
$(IMAGE_NAMES):
	@./scripts/build-session.sh "$@"

$(PYTHON_IMAGES): shared

##@ Generated files
## generate: Write the generated files with the pinned SDK's generator, from the pinned Protocol
generate:
	@./scripts/generated.sh generate

## check-generated: Fail when a committed generated file differs from what the generator writes, or no run writes it
check-generated:
	@./scripts/generated.sh check

##@ Test
## test-rust: The Rust workspace's format, lints, tests and dependency boundaries, in its toolchain's container
test-rust:
	@./scripts/test-rust.sh

## test-python: Each Python project's type checks, lints, format and tests, in a container of the SDK wheel's oldest Python
test-python:
	@./scripts/test-python.sh

## test-browser: The Browser's tests and the type checks of its sources and tests, in its build container
test-browser:
	@./scripts/test-browser.sh

## check-e2e: E2E's specs, fixtures and scripts type-check against the SDK bundle, in a Node container
check-e2e:
	@./scripts/check-e2e.sh

##@ Stack and E2E
## stack-up: Boot and check the SMOKE_TAG images, and leave them up
stack-up:
	@./tests/stack/smoke-stack.sh up "$(SMOKE_TAG)"

## e2e: Run E2E_SCRIPT against a fresh KB beside the stack
e2e:
	@./tests/stack/smoke-stack.sh e2e --script "$(E2E_SCRIPT)" $(if $(strip $(E2E_MODEL)),--model "$(E2E_MODEL)") $(if $(strip $(E2E_ARGS)),-- $(E2E_ARGS))

## stack-down: Stop the stack and remove failed E2E KBs
stack-down:
	@./tests/stack/smoke-stack.sh down

# A standalone `make e2e` leaves a failed KB for inspection. This combined
# target is the self-cleaning stack smoke flow and always attempts teardown.
## smoke: stack-up, e2e and stack-down, tearing down whatever e2e did
smoke:
	@status=0; down_status=0; \
	./tests/stack/smoke-stack.sh up "$(SMOKE_TAG)" || status=$$?; \
	if [ $$status -eq 0 ]; then \
	  ./tests/stack/smoke-stack.sh e2e --script "$(E2E_SCRIPT)" $(if $(strip $(E2E_MODEL)),--model "$(E2E_MODEL)") $(if $(strip $(E2E_ARGS)),-- $(E2E_ARGS)) || status=$$?; \
	fi; \
	./tests/stack/smoke-stack.sh down || down_status=$$?; \
	if [ $$status -ne 0 ]; then exit $$status; else exit $$down_status; fi

##@ Clean
## clean: Remove local image tags and shared-package distributions; keep staged SDK artifacts
clean:
	@./scripts/clean.sh
