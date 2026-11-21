# Browser Container Image

[![ghcr](https://img.shields.io/badge/ghcr-latest-blue)](https://github.com/xynolog/images/pkgs/container/xynolog-browser)

`ghcr.io/xynolog/xynolog-browser`: the Xynolog Browser's built files and a small static
file server, for `linux/amd64` and `linux/arm64`. How it is run, by the launcher or on your own
platform, is [Deployment](DEPLOYMENT.md). How every Xynolog image is tagged and verified is
the operator's [Container Images](https://github.com/xynolog/docs/blob/main/operator/administration/IMAGES.md).

## Run it

```bash
docker run -d -p 3000:3000 --name xynolog-browser \
  ghcr.io/xynolog/xynolog-browser:latest
```

Open <http://localhost:3000> and add a knowledge base in the Knowledge Bases panel: its
gateway's protocol, host and port. Then sign in.

## The browser connects, not the container

The image is a static file server (`server.js`) for the prebuilt app. It has no gateway
address, at build time or at run time, and it proxies nothing.

Connections to knowledge bases are made in the running app, by the person using it:

1. They add a knowledge base (protocol, host, port) in the Knowledge Bases panel.
2. The app sends them to the identity provider that knowledge base trusts, and finishes the
   sign-in on its own callback route. The SDK keeps an access and refresh token pair for each
   knowledge base in the web browser's `localStorage`, and renews the access token at the
   identity provider before it expires.
3. The app then calls that gateway **directly from the web browser**: who the person is, media
   tokens and content over HTTP routes, and everything else over the bus (`POST /bus/emit`,
   and `POST /bus/subscribe` for the event stream).

```
Web browser ── GET  https://app.example.com/ ───────────▶ Browser container (static files)
Web browser ── sign-in and token renewal ───────────────▶ the knowledge base's identity provider
Web browser ── POST https://kb.example.com/bus/emit ────▶ the knowledge base's gateway
               POST https://kb.example.com/bus/subscribe
```

So the one network requirement is that each gateway, and its identity provider, is reachable
**from the person's web browser**. Reachability from the Browser's container is irrelevant, and
no reverse proxy or path-based routing sits between them. A gateway answers any origin. Several
knowledge bases can be added side by side, and they survive a reload.

## Configuration

One runtime variable:

| | | |
|---|---|---|
| `PORT` | run time | The port the static server listens on. Default `3000` |
| `/discovery` | run time | A read-only mount the launcher uses to tell the app which knowledge bases are running on the machine. Optional |

There are no `XYNOLOG_*` variables. The bundle is built when this repository packs the
`@xynolog/browser` package for the image, and the server does no templating.

## What is in it

- **Base image:** Node 26 on Alpine, as the [Dockerfile](../Dockerfile)'s `FROM` names it.
- **Contents:** the `@xynolog/browser` package, at the image's version, which
  [`scripts/build-browser-package.sh`](../../scripts/build-browser-package.sh) builds from this
  directory and the SDK bundle and packs. The package is never published to a registry, and the
  image installs it from that file rather than building from source.
- **Entrypoint:** `tini`, then `node node_modules/@xynolog/browser/server.js`.
- **Health check:** built in. It requests `/` every 30 seconds.
- **Logs:** one line when the server starts listening, and any server error. It does not log
  requests.

`server.js` serves files out of `dist/`, answers `index.html` for every route that is not a
file, and serves `/discovery/*` from its mount: a file or a 404, never the app.

## Tags

- **The version**: the release, `YY.M.N`, which is every image's version and the package's.
- **`sha-<commit>`**: the commit the image was published from.
- **`latest`**: moved to each release as it is published. It is what the launcher names in the
  Browser's document when it writes one; the document's `spec.image` decides what runs.

A tag can be moved and a digest cannot. To pin exactly what you verified, reference the image
by digest ([Container Images](https://github.com/xynolog/docs/blob/main/operator/administration/IMAGES.md#supply-chain-verification)).

## Building it yourself

The image is built from [`browser/Dockerfile`](../Dockerfile), from the package
`scripts/build-browser-package.sh` packs. Both build arguments are required:

```bash
# From the repository root, with a verified SDK bundle
bash scripts/build-browser-package.sh <sdk-bundle-directory>
docker build \
  --build-arg XYNOLOG_BROWSER_VERSION="$(node -p 'require("./version.json").version')" \
  --build-arg BROWSER_PACKAGE_DIR=.local/browser-package \
  -t ghcr.io/xynolog/xynolog-browser:custom \
  -f browser/Dockerfile .
```

| Build argument | |
|---|---|
| `XYNOLOG_BROWSER_VERSION` | The package's version, `version.json`'s |
| `BROWSER_PACKAGE_DIR` | The directory, in the build context, that holds the packed package |

To run a change, build every image from your working tree with
[`make build`](../../Makefile)
([Local Development](https://github.com/xynolog/docs/blob/main/contributor/LOCAL-DEVELOPMENT.md)). Published images come
from the `publish-browser.yml` workflow: scanned, with an SBOM and build provenance attested.

## Secrets

The image holds none and needs none. A person's tokens exist only in their own web browser's
`localStorage` and never pass through this container. The gateway's signing key and its service
account are the gateway's ([Secrets](https://github.com/xynolog/docs/blob/main/operator/services/SECRETS.md)).

## Troubleshooting

**A knowledge base cannot be added: a network error.** Its gateway must be reachable from the
person's web browser, not from this container. For a knowledge base running on this computer that is `localhost:4000`, the
port published to the host. A container's name on the container network, such as
`xynolog-example.org-my-kb-gateway`, does not resolve in a web browser.

**Requests are blocked as mixed content.** The app was loaded over `https` and the knowledge
base was added with `http`. Serve the gateway over HTTPS and choose `https` when adding it.

**A knowledge base drops to signed out.** Its identity provider would not renew the session:
the refresh token expired or was revoked, or the account was disabled there. The gateway's
`JWT_SECRET` plays no part: it signs agent and media tokens, never a person's. Sign in again.

## Related

- [Deployment](DEPLOYMENT.md): running the image, with the launcher or without
- [Development](DEVELOPMENT.md): running the app from source
- [Container Topology](https://github.com/xynolog/docs/blob/main/operator/CONTAINER-TOPOLOGY.md): how the containers of a stack connect
- [Container Images](https://github.com/xynolog/docs/blob/main/operator/administration/IMAGES.md): every image, its tags and verifying one
