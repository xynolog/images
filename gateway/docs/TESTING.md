# Gateway Testing

The gateway's behavioural contract is one suite, and it lives outside this
crate: [`protocol/conformance/gateway`](https://github.com/xynolog/protocol/blob/main/conformance/gateway/README.md).
It is black-box. It starts gateway processes, talks to them over HTTP and SSE,
and checks what they answer against the protocol as `protocol/specs/` states it — the
OpenAPI document and the bus registry — and as
[TRANSPORT-HTTP.md](https://github.com/xynolog/protocol/blob/main/contract/TRANSPORT-HTTP.md) states the
semantics a schema cannot hold. It imports nothing from the gateway, so it
checks any implementation that answers to the same spec.

Every case runs on both signal planes — in-process, and NATS against a real
`nats-server` — except those that need a broker (two replicas) or do not depend
on the plane.

## What checks what

| Where | Checks |
|---|---|
| Protocol's reader (`make reader` in protocol) | The spec states the whole protocol: every operation says whether it is public; every response has a body schema, every error body is an `ErrorResponse`, every 401 a challenge; the stream's messages, frame and id formats are schemas; every JSON body has a `maxBodyBytes` and a 413; the limits are positive integers; the gateway's waits for the Archivist end inside a client's deadline |
| Protocol's reader, its identifier rules (`make reader` in protocol) | The spec names its ids: every property named for an id refers to its kind's schema, and every string [`protocol/specs/src/identifiers/kinds.json`](https://github.com/xynolog/protocol/blob/main/specs/src/identifiers/kinds.json) says a kind accepts or refuses agrees with that kind's pattern |
| `make check-generated` (CI's generated job) | The spec bundles, and the committed bundles and service-only types (`xynolog-core`) are what the pinned SDK's generator writes from them; a schema of a shape the generator does not know, or a service-only type the SDK already declares, fails it |
| `xynolog-core`'s spec tests (`make test-rust`) | Every component schema compiles, and the bus registry names only schemas the spec declares |
| `protocol/conformance/gateway` | A running gateway conforms: spec-derived probes of every operation, every response and stream message validated against the spec, and hand-written cases for credentials, content, emitting, the stream, the connection bounds, the limits on one principal (a person and an agent alike) and on one process, replicas, readiness, boot refusals, the headers on every response, the environment, and the telemetry census |
| The gateway's boot | Its route table is exactly the spec's operations — no undeclared route, no declared operation unserved ([src/routes/mod.rs](../src/routes/mod.rs)) — and every Archivist operation it calls is in the Archivist's spec; every suite run boots gateways, so a route added without a spec entry fails CI |
| `cargo test` (`make test-rust`; CI's rust job, on every run) | The tests of the crates the gateway is built from, and the gateway's own unit tests, which run on the in-process plane: among them an emit's key (its digest, which outcomes it holds, its lifetime) and a request whose publish failed being published when sent again. Beside them it relies on the runners for the shared case tables ([Rust SDK test tables](https://github.com/xynolog/sdk/blob/main/rust/sdk/tests/tables.rs)), against the SDK it names its principals with: the principals and the knowledge base's resource identifier, as core and the launcher compute them |
| The crates' dependency boundaries ([check-dependency-boundaries.sh](../../packages/rust/scripts/check-dependency-boundaries.sh); `make test-rust`) | No NATS client in `xynolog-core` (but through its `nats` feature), `xynolog-http-service`, `xynolog-observability` or `xynolog-dispatcher-handlers`; no HTTP, git or NATS crate in `xynolog-archivist-record` |
| `cargo fmt` and `cargo clippy` (`make test-rust`) | The workspace is formatted, and clippy finds nothing in any crate, target or feature |
| `scripts/check-broker-boundary.mjs` (CI's checks job) | The broker is reached only through its interface: `async_nats` only in `signal/nats.rs`, the dispatcher's JetStream queue and `xynolog-core`'s broker helpers; that plane chosen only in `app.rs`; no NATS client in any TypeScript |
| `scripts/check-service-environment.mjs` (CI's crates job) | The environment it reads is exactly [variables.json](https://github.com/xynolog/protocol/blob/main/specs/src/service-environment/variables.json)'s |
| `scripts/check-image-crates.mjs` | Every crate it links is under a permitted licence, and credited in the image's NOTICE; every crate that compiles native code in says what, and a library under a licence of its own is credited too |
| `cargo deny` ([deny.toml](../../packages/rust/deny.toml); CI's crates job, on every run) | Every crate comes from crates.io, named by a version, not a wildcard |
| `build-tools/advisories.py` ([advisories.toml](../../advisories.toml); CI's advisories job, on every run) | No crate the workspace locks has a published advisory, except those ignored with a reason, and an ignore that stops matching fails |
| `scripts/check-gateway-image.sh` | The built image carries no source and serves `/api/health` within its start bound |

## Running it

From the repository root,

```bash
make test-rust
```

runs `cargo fmt`, `cargo clippy`, every crate's tests and the dependency boundaries over the
whole workspace, as CI does. It runs in the toolchain's image, on a copy of the checkout, against
the SDK's crates from the SDK artifact bundle (`SDK_REPO` or `SDK_ARTIFACTS`; `make help`).

The conformance suite is protocol's: it runs against a built gateway, named in an implementation
manifest, as [its README](https://github.com/xynolog/protocol/blob/main/conformance/gateway/README.md#running-it) says. The suite
needs `nats-server` 2.10 or later on `PATH`.

## Load

[bench/load.sh](../bench/load.sh) puts gateway binaries under the same load, one
after another, on Alpine as the image is: `GET /api/health`, and `POST /bus/emit`
with an empty payload and with an 8 KiB one, each from `wrk` on CPUs the gateway
does not use. It is a measurement, not a gate, and nothing in CI runs it. The
allocator is chosen by it (eight gateway CPUs, 256 connections,
median of three 10 s runs):

| Allocator | health req/s | emit req/s | emit p50 | peak RSS |
|---|---|---|---|---|
| musl's malloc: the gateway built without the `#[global_allocator]` in [src/main.rs](../src/main.rs) | 39,876 | 15,681 | 15.0 ms | 40 MiB |
| jemalloc: the gateway as it is built | 589,293 | 266,000 | 0.9 ms | 49 MiB |

musl's malloc is the bottleneck under eight workers.

## Adding to the protocol

Change the spec first — a gateway whose routes are not the spec's operations
refuses to start. A handler is unauthenticated until it takes a credential
(`Authenticated` or `MediaOrBearer`), and nothing protects a route by default. A new route is probed by the spec-derived cases as soon as the
spec declares it — unauthenticated, with a bad credential, with a body that does
not validate — and every reply it gives is checked against its declaration.
Then write the cases no schema can state, each citing the text it checks, and
watch each fail against a gateway that does not do it yet.
