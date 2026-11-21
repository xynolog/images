# Real-stack smoke test

The stack smoke exercises built images through the separately installed `xynolog`
launcher. Set `XYNOLOG` to its executable path if it is not on `PATH`.

From the repository root:

```sh
make build
./tests/stack/smoke-stack.sh up local
./tests/stack/smoke-stack.sh e2e
./tests/stack/smoke-stack.sh e2e --script test:slow --model gemma4:26b -- specs/01-sign-in.spec.ts
./tests/stack/smoke-stack.sh down
./tests/stack/smoke-stack.sh run local --e2e
```

A published image tag can replace `local`. `up` starts a fresh knowledge base,
checks service health, identity, and Browser origins, and leaves it running. `e2e`
creates a separate knowledge base and user, then runs the selected Playwright tier.
It checks the job queue and removes a successful run; a failed run stays available
for diagnosis until `down` removes it. `down` stops the stack and restores the
launcher-managed service documents.

`make test-python` checks the smoke script against stand-ins without starting
containers, with the repository's other Python (`scripts/test-python.sh .` runs
only that).
