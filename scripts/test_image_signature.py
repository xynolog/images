"""Exercise image input invalidation without building an image or modifying runtime state."""

import importlib.util
import json
import tempfile
import threading
import unittest
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import override
from urllib.parse import unquote

import pytest

SPEC = importlib.util.spec_from_file_location("image_signature", Path(__file__).with_name("image-signature.py"))
if SPEC is None or SPEC.loader is None:
    raise ImportError("scripts/image-signature.py cannot be loaded")
image_signature = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(image_signature)
signature_of: Callable[[Path, Path, str, str, str], str] = image_signature.signature


class SignatureTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dockerfile = self.root / "Dockerfile"
        self.dockerfile.write_text("FROM scratch\nCOPY source.txt /source.txt\n")
        (self.root / "source.txt").write_text("first")

    def signature(self, registry: str = "http://127.0.0.1:1", rust: str = "rust", python: str = "python") -> str:
        return signature_of(self.root, self.dockerfile, registry, rust, python)

    def test_copy_inputs_dockerfile_and_toolchain_all_invalidate(self) -> None:
        before = self.signature()
        (self.root / "source.txt").write_text("second")
        assert self.signature() != before
        before = self.signature()
        self.dockerfile.write_text(self.dockerfile.read_text() + "ARG RUST_TOOLCHAIN\n")
        assert self.signature() != before
        assert self.signature(rust="new") != self.signature(rust="old")
        (self.root / "source.txt").unlink()
        with pytest.raises(FileNotFoundError):
            self.signature()

    def test_transitive_npm_integrity_changes_without_a_version_bump(self) -> None:
        packages: dict[str, dict[str, dict[str, str]]] = {
            "@xynolog/app": {
                "dist": {"integrity": "app"},
                "dependencies": {"@xynolog/core": "*"},
            },
            "@xynolog/core": {"dist": {"integrity": "first"}},
        }

        class Registry(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                package = packages.get(unquote(self.path.lstrip("/")))
                if package is None:
                    self.send_error(404)
                    return
                body = json.dumps(
                    {
                        "dist-tags": {"latest": "same-version"},
                        "versions": {"same-version": package},
                    }
                ).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            @override
            def log_message(self, format: str, *args: object) -> None:
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Registry)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            self.dockerfile.write_text("FROM scratch\nRUN npm install @xynolog/app\n")
            address = f"http://127.0.0.1:{server.server_port}"
            before = self.signature(registry=address)
            packages["@xynolog/core"]["dist"]["integrity"] = "second"
            assert self.signature(registry=address) != before
            del packages["@xynolog/core"]
            assert self.signature(registry=address) == ""
        finally:
            server.shutdown()
            server.server_close()
            worker.join()


if __name__ == "__main__":
    unittest.main()
