# End-to-End Smoke Tests

Real-browser Playwright tests that drive the Browser against a locally
running gateway. Intended to catch cross-layer regressions (SSE timing,
React lifecycle, bus round-trips) that unit and component tests can't.

## Stack smoke test

The image repository builds images only. The optional real-stack smoke script
uses the separately installed `xynolog` CLI (set `XYNOLOG` to its executable path
if needed) to start a knowledge base from the selected images:

```sh
make build
make stack-up
make e2e
make stack-down
make smoke                 # self-cleaning combined flow
```

Set `SMOKE_TAG` to use another image tag. `E2E_SCRIPT`, `E2E_MODEL`, and
`E2E_ARGS` configure the suite; for example:

```sh
make e2e E2E_SCRIPT=test:slow E2E_MODEL=gemma4:26b E2E_ARGS='specs/01-sign-in.spec.ts --repeat-each=5'
```

`make e2e` expects a stack started with `make stack-up`. On failure it leaves
the test KB running for inspection; `make stack-down` cleans up the stack and
any failed test KBs. `make smoke` always attempts teardown.

A published image tag can replace `local`. `e2e` creates a separate test KB and
user, runs Playwright in the pinned Playwright container, and waits for its job
queue to drain. Successful runs clean up automatically; failed runs remain for
inspection until `down`. Use `--script` to choose an npm script, `--model` to
choose the test KB's model, and arguments after `--` for Playwright.

## Quick start

Prereqs: the dev stack is up, with its ports published on the host. Full
rebuild/start flow in [docs/containers.md](docs/containers.md).

```sh
# The image tag MUST match the installed library — see "Version pinning" below.
PW=$(node -p "require('./node_modules/@playwright/test/package.json').version")

container run --rm \
  -v "$(git rev-parse --show-toplevel):/workspace" \
  -w /workspace/e2e \
  -e E2E_EMAIL=admin@example.com \
  -e E2E_PASSWORD=password \
  -e E2E_BROWSER_URL=http://localhost:3000 \
  -e E2E_GATEWAY_URL=http://localhost:4000 \
  -e CI=1 \
  "mcr.microsoft.com/playwright:v$PW-noble" \
  sh -c 'node e2e-localhost-bridge.mjs & sleep 1; npm test'
```

> **`localhost`, through the bridge.** `e2e-localhost-bridge.mjs` forwards the
> container's `localhost` ports to the host bridge address, `192.168.64.1`,
> where a container reaches the stack. See
> [Container networking](#container-networking-reaching-the-host) for why.
>
> A container's own IP (from `container ls`) fails twice over:
>
> - **Container IPs change on every stack restart.** Reusing an address read
>   even minutes earlier fails in `globalSetup` with
>   `connect EHOSTUNREACH <ip>:4000`, before a single spec executes.
> - **It splits services across hosts.** `19-worker-vitals` derives the
>   worker's health endpoint as `<gateway-host>:24100`, because the published
>   ports are co-located on the host. Point the suite at the *gateway
>   container's* IP and that becomes the gateway's own `:24100`, which nothing
>   is listening on — `ECONNREFUSED`.
>
> `--network host` does not help: it is a Docker flag, and Apple's `container`
> rejects it with `Error: network host not found`.

> Use `npm test`, not `npx playwright test`: the `pretest` hook typechecks
> the specs first (`tsc --noEmit`) and aborts before launching a browser.
> `e2e` is not a root workspace, so this gate is the ONLY thing that
> typechecks these files — bypassing it means an SDK signature change
> surfaces as a runtime `TypeError` minutes in, instead of a file:line.

> If every test fails in the `signIn` fixture with *"Request failed due
> to a network error"*, the Playwright container can't reach the
> host-published gateway — see [Container networking](#container-networking-reaching-the-host).

## Version pinning: the image must match the installed library

Playwright refuses to run when the browser image and the `@playwright/test`
library disagree, so the tag is not decorative. Derive it rather than typing
it — `$PW` above reads the version off disk, which is the one source that
cannot be stale relative to what is about to run.

Dependabot bumps `package.json` and `package-lock.json` together, but
nothing installs them here, so the declared and installed versions diverge
silently until someone runs `npm ci`; a hard-coded tag would make a third.

**Nothing else catches this on a laptop.** `e2e` is not a root
workspace, so its dependencies are installed only by a person deciding to. After a Dependabot bump, sync before running:

```sh
npm ci        # installs the lockfile EXACTLY; never rewrites it
```

Use `npm ci`, not `npm install`: `ci` cannot alter `package-lock.json`, so
syncing your `node_modules` can never quietly re-resolve the suite's
dependencies for everyone else. The lockfile is tracked and is the authority.

## Container networking: reaching the host

The suite runs in a Playwright **container**, but the stack is published on
the **host**. Inside the container `localhost` is the container itself, and a
container's own IP changes on every restart.

Under Apple `container` the stack publishes what a person opens on the Mac's
loopback, which no container reaches, and what the containers dial on the
**host bridge address**, `192.168.64.1`, which every container reaches and
which is stable across restarts. The Browser and the gateway, which a person
and a container both open, take a second port there, 10000 above their own:
`:13000` and `:14000`.

`e2e-localhost-bridge.mjs` joins the two. Run inside the container, it listens
on the container's `localhost` and forwards each port to where a container
reaches it: `:3000`→`:13000`, `:4000`→`:14000`, and `:8080` (Keycloak) and
`:24100` (the worker's health) as they are. The suite then uses
`http://localhost:*` throughout, which gives Chromium the secure context PKCE
needs, and the knowledge base it registers is the origin the launcher
advertises. The launcher's tests hold the bridge's ports to the launcher's own.

Under Docker, `tests/stack/smoke-stack.sh e2e` runs the suite with
`--network host`, where `localhost` is the host, and starts no bridge.

> **No CORS origin to configure.** The gateway serves open CORS
> (`Access-Control-Allow-Origin: *`, bearer-only — no credentials), so the
> browser signs in from *any* origin.

Run the suite with the bridge in front of it:

```sh
container run --rm \
  -v "$(git rev-parse --show-toplevel):/workspace" \
  -w /workspace/e2e \
  -e E2E_EMAIL=admin@example.com \
  -e E2E_PASSWORD=password \
  -e E2E_BROWSER_URL=http://localhost:3000 \
  -e E2E_GATEWAY_URL=http://localhost:4000 \
  -e CI=1 \
  "mcr.microsoft.com/playwright:v$PW-noble" \
  sh -c 'node e2e-localhost-bridge.mjs & sleep 1; npm test'
```

## Docs

- [Running tests](docs/running.md) — invocation, single spec, headed,
  `--repeat-each`, host vs. container.
- [Containers and rebuild flow](docs/containers.md) — Apple container
  CLI, rebuilding gateway/Browser after code changes, IP
  refresh, Playwright image tag.
- [Writing tests](docs/writing.md) — spec template, fixture ordering,
  protocol-level assertions, seed assumptions, selector conventions.
- [Debugging failures](docs/debugging.md) — traces, report UI, JSONL
  extraction, diagnostic specs, gateway-log tailing, instrument don't
  speculate.
- [Bus logging](docs/bus-logging.md) — the `__XYNOLOG_BUS_LOG__` wire
  logger, the `bus` capture fixture, assertion helpers.
- [Jaeger evidence](docs/jaeger.md) — the `jaeger` fixture that pulls
  matching distributed traces on test teardown and attaches them to
  the Playwright report.
- [Page errors](docs/page-errors.md) — the `pageErrors` fixture that
  surfaces uncaught browser-side errors (exceptions, unhandled
  rejections, `console.error`) — invisible to bus/jaeger captures.
  Soft by default; flip `PAGE_ERRORS_FAIL=1` once clean.
- [Live monitoring](docs/live-monitoring.md) — sibling workflow for
  bug-hunting on the running stack (no Playwright). Streaming
  per-container error tails + on-demand snapshot of the last N
  seconds across logs and Jaeger spans. How "live monitoring caught
  X" turns into "e2e spec Y".
- [Known gotchas](docs/gotchas.md) — sharp edges:
  `crypto.randomUUID`, form-field ordering,
  stale tabs, fixture ordering, etc.

## The specs

[`specs/`](specs) holds one `NN-short-name.spec.ts` per path it
guards; a regression in that path fails that spec. Specs tagged
`@slow` run only under `npm run test:slow`.

Tests tagged `@model` pass or fail on what the inference model returns: a
delegated job's annotations, a generation, a structured reply. A model too small
to answer in valid JSON, or too slow on the machine, fails them while every
other test passes. They are in the default tier, which `npm test` runs;
`npm run test:model` runs them alone. CI runs `npm run test:ci`, the default
tier without them: on a four-core runner with no GPU, neither `gemma3:270m`
nor `gemma3:1b` answered them correctly within their timeouts.

## Scope

- **Not a gate on pull requests.** Run it against a stack you brought up.
- **Seeded.** Playwright's global setup ([`scripts/seed.ts`](scripts/seed.ts))
  authenticates through `@xynolog/sdk` and uploads the fixtures the specs
  assume: text resources for the annotation specs, PDFs for the PDF specs.
  Each seed has a stable
  storage URI, so a re-run against a seeded knowledge base skips it.
- **Real sign-in.** Connect leaves the Browser for the launcher-run
  Keycloak, and the `signIn` fixture types the credentials into its login
  page. An account's first sign-in asks for a name, which `xynolog useradd`
  does not set; the seed's sign-in, always the run's first, gives one.
- **One worker, no retries.** Specs share the knowledge base; a flake is
  diagnosed, not retried away.
- **Chromium only.**

## CI

Continuous integration builds the image set with `make build`. The real-stack
e2e smoke requires a running container engine, Ollama or another configured
inference provider, and an installed `xynolog` CLI, so it is run explicitly with
`tests/stack/smoke-stack.sh` rather than as part of the default image build.

## Running against freshly-built images

Build the image set from this checkout, then use a KB configured for the local
tags with `xynolog`:

```sh
make build
# In a knowledge base directory, update configured image references to :local,
# then run the stack with xynolog using that configuration.
xynolog start
```

The standalone `tests/stack/smoke-stack.sh` automates this flow for a fresh KB.
The browser e2e specs can also run directly against a stack already running on
the host; see the [Quick start](#quick-start).

## Gotchas

- **Apple Container `--rm` is unreliable.** Stopped xynolog-* containers
  often linger and conflict on next start with `Error: container with
  id xynolog-foo already exists`. Wipe with `container stop $name &&
  container rm $name` before retrying.
- **Host Ollama needs `OLLAMA_HOST=0.0.0.0`.** Otherwise the gateway
  container can't reach it. Either configure Ollama Desktop with
  `launchctl setenv OLLAMA_HOST 0.0.0.0` (and quit/relaunch), or use
  `xynolog start --config anthropic` to skip Ollama entirely.
- **Code changes require rebuilding the `:local` images.** `./tests/stack/smoke-stack.sh up` does it
  for you. On a stack you started yourself, rerun `make build`, then restart
  the stack with `xynolog start`, its documents naming the `:local` images. Without the
  rebuild + restart, you'll run yesterday's images with today's source.
- **SPA tracing is not wired.** Gateway / worker / smelter
  produce traces; the Browser SPA does not. End-to-end traces
  therefore start at `bus.dispatch:*` (server-side EMIT receive)
  rather than the SPA's `bus.emit:*`. Enabling SPA tracing
  would need `VITE_OTEL_OTLP_ENDPOINT` threaded
  through `make build` into the vite build container, plus
  `COLLECTOR_OTLP_HTTP_CORS_ALLOWED_ORIGINS=*` on the Jaeger sidecar.
