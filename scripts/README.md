# Image scripts

`scripts/build-session.sh` powers the Makefile's image build targets. It detects Docker, Podman, or Apple Container and builds selected image directories. `scripts/clean.sh` removes the local tags created by that build. Both, and CI's image grouping, take the images and each one's SDK language from the Makefile's groups through `scripts/image-groups.sh`. CI builds only the images a change affects: `scripts/changed-images.py` reads each image's inputs from its Dockerfile's copies, its language's shared code and what every build reads, and groups the affected ones.

`scripts/generated.sh` powers `make generate` and `make check-generated`: it runs the generator the SDK bundle carries, at the commit `upstream.lock.json` pins, against this checkout, and the check fails on a committed generated file that differs from what it writes.

`scripts/test-rust.sh`, `scripts/test-python.sh`, `scripts/test-browser.sh` and `scripts/check-e2e.sh` power `make test-rust`, `make test-python`, `make test-browser` and `make check-e2e`, which CI runs: each runs its checks in a container, against the SDK bundle. `scripts/python-checks.Dockerfile` is the Python checks' container. `scripts/browser-container.sh` installs the Browser's dependencies in its build container, for `scripts/build-browser-package.sh` to build the package there and `scripts/test-browser.sh` to check it there.

The `check-*-image.sh` scripts and `check-*.mjs` files support image validation and repository maintenance. `shared/boot.sh` and `shared/supervise.sh` are copied into the runtime images by their Dockerfiles.

`scripts/release-version.sh` is the one reader of the release every release workflow runs at: version.json's `YY.M.N` and its tag `v<version>`. `scripts/image-tags.sh` names the tags each published image carries.
