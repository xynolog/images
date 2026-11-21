"""Run the smoke's up, e2e and down against stand-ins, without starting services."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import TypedDict, override

SOURCE = Path(__file__).with_name("smoke-stack.sh")
DOCUMENTS = {
    "browser": "image: ghcr.io/xynolog/xynolog-browser:previous\nkeep: browser-setting\n",
    "worker": "image: ghcr.io/xynolog/xynolog-worker:previous\nkeep: worker-setting\n",
}
ISSUER = "http://192.0.2.1:8080/realms/example.github.io-stack-smoke"
PROTECTED_RESOURCE = {
    "resource": "https://example.github.io/stack-smoke",
    "authorization_servers": [ISSUER],
    "bearer_methods_supported": ["header"],
}
# Keycloak's shape: the token endpoint again under mtls_endpoint_aliases, after the top-level one.
DISCOVERY = {
    "issuer": ISSUER,
    "token_endpoint": f"{ISSUER}/protocol/openid-connect/token",
    "mtls_endpoint_aliases": {"token_endpoint": f"{ISSUER}/protocol/openid-connect/token"},
}
# Each init writes a KnowledgeBase document whose gateway has a port of its own,
# as init gives a knowledge base beside another the next port block.
LAUNCHER = """import json
import os
from pathlib import Path
import sys
root = Path(os.environ["SMOKE_TEST_ROOT"])
command = sys.argv[1]
def log(name, entry):
    with (root / name).open("a") as f:
        f.write(json.dumps(entry) + "\\n")
if command == "--version":
    print("smoke-test xynolog")
elif command == "init":
    inits = root / "inits.jsonl"
    count = len(inits.read_text().splitlines()) if inits.exists() else 0
    log("inits.jsonl", {"cwd": os.getcwd(), "domain": sys.argv[sys.argv.index("--domain") + 1], "flags": sys.argv[2:]})
    stack = Path.cwd() / ".xynolog/stack"
    stack.mkdir(parents=True)
    port = 4000 + 10 * count
    (stack / "knowledge-base.yaml").write_text(
        "kind: KnowledgeBase\\nspec:\\n  gateway:\\n"
        "    image: ghcr.io/xynolog/xynolog-gateway:latest\\n"
        f"    port: {port}\\n    publicURL: http://localhost:{port}\\n"
        "  dispatcher:\\n    image: ghcr.io/xynolog/xynolog-dispatcher:latest\\n"
    )
elif command == "settings":
    print(root / "state home" / f"{sys.argv[2]}.yaml")
elif command == "start":
    starts = root / "starts.jsonl"
    count = len(starts.read_text().splitlines()) if starts.exists() else 0
    snapshot = {name: (root / "state home" / f"{name}.yaml").read_text() for name in ("browser", "worker")}
    snapshot["gateway"] = (Path.cwd() / ".xynolog/stack/knowledge-base.yaml").read_text()
    snapshot["cwd"] = os.getcwd()
    log("starts.jsonl", snapshot)
    statuses = os.environ["SMOKE_TEST_START_STATUS"].split(",")
    sys.exit(int(statuses[min(count, len(statuses) - 1)]))
elif command in ("stop", "clean", "forget", "useradd", "status"):
    log("xynolog.jsonl", sys.argv[1:])
    if command == "useradd":
        sys.stdin.read()
    # The dispatcher's line of a status report, as the launcher prints it when the
    # collector has a reading of its queue.
    if command == "status" and os.environ["SMOKE_TEST_QUEUE"]:
        print("    queue    " + os.environ["SMOKE_TEST_QUEUE"])
"""
DRAINED = "0 pending · 0 running · 4 completed · 0 failed since worker start"


class Init(TypedDict):
    """A line of the launcher's inits.jsonl: where an init ran, for which domain, and with what."""

    cwd: str
    domain: str
    flags: list[str]


class SmokeStackTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.kb = self.root / "kb"
        script = self.root / "tests/stack/smoke-stack.sh"
        script.parent.mkdir(parents=True)
        shutil.copyfile(SOURCE, script)
        runtime_helper = self.root / "build-tools/container-runtime.sh"
        runtime_helper.parent.mkdir(parents=True)
        shutil.copyfile(SOURCE.parents[2] / "build-tools/container-runtime.sh", runtime_helper)
        e2e_package = self.root / "e2e/package.json"
        e2e_package.parent.mkdir(parents=True)
        shutil.copyfile(SOURCE.parents[2] / "e2e/package.json", e2e_package)
        for directory in ("bin", "state home"):
            (self.root / directory).mkdir(parents=True)
        for name, text in DOCUMENTS.items():
            (self.root / "state home" / f"{name}.yaml").write_text(text)
        self.xynolog = self.root / "bin/xynolog"
        self.xynolog.write_text(f"#!{sys.executable}\n" + LAUNCHER)
        self.xynolog.chmod(0o755)
        self.use_runtime("smoke-test-runtime", 0)

    def use_runtime(self, runtime: str, e2e_status: int) -> None:
        self.runtime = runtime
        log = self.root / "runtime.log"
        for name, body in {
            # The gateway names an issuer on a host of the runtime's choosing, which
            # answers discovery and the Browser's origin. The URL is curl's last argument.
            "curl": f'for url; do :; done\nprintf "%s\\n" "$url" >> "{self.root / "curl.log"}"\n'
            'case "$url" in\n'
            f"  */.well-known/oauth-protected-resource) printf '%s' '{json.dumps(PROTECTED_RESOURCE)}' ;;\n"
            f"  {ISSUER}/.well-known/openid-configuration) printf '%s' '{json.dumps(DISCOVERY)}' ;;\n"
            f"  {DISCOVERY['token_endpoint']}) printf 'access-control-allow-origin: http://localhost:3000\\n' ;;\n"
            "  *) exit 7 ;;\n"
            "esac",
            "nc": "exit 1",
            # The smoke waits ten seconds between readings of a queue; the test does not. Every
            # other sleep is the real one: the runtime probe's watchdog kills a probe that a
            # sleep returning at once outran.
            "sleep": '[ "$*" = 10 ] && exit 0\nexec /bin/sleep "$@"',
            runtime: f'printf "%s\\n" "$*" >> "{log}"\n'
            # The suite's run: after `sh -c <script>`, the shell's $0 and arguments, one per field.
            'if [ "$1" = run ]; then\n'
            '  while [ $# -gt 0 ] && [ "$1" != -c ]; do shift; done\n'
            "  shift 2\n"
            f'  printf "%s\\t" "$@" >> "{self.root / "suites.log"}"\n'
            f'  printf "\\n" >> "{self.root / "suites.log"}"\n'
            f"  exit {e2e_status}\n"
            "fi\n"
            # Another knowledge base's container, stopped, as a machine keeps one.
            'case "$1" in ps|ls) echo xynolog-another-kb-gateway ;; logs) echo "a log line of $*" ;; esac\nexit 0',
        }.items():
            executable = self.root / "bin" / name
            executable.write_text(f"#!/bin/sh\n{body}\n")
            executable.chmod(0o755)

    def smoke(
        self,
        *args: str,
        start_status: str = "0",
        queue: str = DRAINED,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.root / "tests/stack/smoke-stack.sh"), *args],
            check=False,
            env={
                **os.environ,
                "PATH": str(self.root / "bin") + os.pathsep + os.environ["PATH"],
                "SMOKE_TEST_ROOT": str(self.root),
                "SMOKE_TEST_START_STATUS": start_status,
                "XYNOLOG": str(self.xynolog),
                "SMOKE_TEST_QUEUE": queue,
                "CONTAINER_RUNTIME": self.runtime,
                "SMOKE_KB": str(self.kb),
            },
            capture_output=True,
            text=True,
            timeout=60,
        )

    def logged(self, name: str) -> list[str]:
        """The lines of the launcher's log ``name``; none before it logs one."""
        path = self.root / name
        return path.read_text().splitlines() if path.exists() else []

    def commands(self) -> list[list[str]]:
        """The arguments of each stop, clean, forget, useradd and status."""
        return [json.loads(line) for line in self.logged("xynolog.jsonl")]

    def starts(self) -> list[dict[str, str]]:
        """Each start: the browser, worker and gateway documents it found, and its cwd."""
        return [json.loads(line) for line in self.logged("starts.jsonl")]

    def inits(self) -> list[Init]:
        """Each init."""
        return [json.loads(line) for line in self.logged("inits.jsonl")]

    def stopped(self) -> list[str]:
        """The root of each `stop`, resolved: macOS reports a temporary directory's cwd under /private."""
        stops = [call for call in self.commands() if call[0] == "stop"]
        for call in stops:
            assert "--root" in call, "a stop naming no root stops whichever stack it finds"
        return [os.path.realpath(call[call.index("--root") + 1]) for call in stops]

    def asked_status(self) -> list[str]:
        """The root of each `status`, resolved."""
        return [os.path.realpath(call[call.index("--root") + 1]) for call in self.commands() if call[0] == "status"]

    def suites(self) -> list[list[str]]:
        """Each run of the suite: its shell's $0 and arguments."""
        path = self.root / "suites.log"
        return [line.rstrip("\t").split("\t") for line in path.read_text().splitlines()] if path.exists() else []

    def assert_documents_restored(self) -> None:
        for name, original in DOCUMENTS.items():
            assert (self.root / "state home" / f"{name}.yaml").read_text() == original

    def test_up_names_the_images_and_down_restores_the_documents(self) -> None:
        for tag in ("local", "latest", "0.7.1"):
            with self.subTest(tag=tag):
                result = self.smoke("up", tag)
                assert result.returncode == 0, result.stdout + result.stderr
                for name in DOCUMENTS:
                    assert f"image: ghcr.io/xynolog/xynolog-{name}:{tag}\n" in (self.root / "state home" / f"{name}.yaml").read_text()
                started = self.starts()[-1]
                for name in ("browser", "worker", "gateway"):
                    assert f"ghcr.io/xynolog/xynolog-{name}:{tag}\n" in started[name]
                    if name != "gateway":
                        assert f"keep: {name}-setting\n" in started[name]
                result = self.smoke("down")
                assert result.returncode == 0, result.stdout + result.stderr
                self.assert_documents_restored()
                assert os.path.realpath(self.kb) in self.stopped()
                shutil.rmtree(self.kb)

    def test_stack_smoke_requires_xynolog_before_starting_anything(self) -> None:
        env = {**os.environ, "PATH": str(self.root / "bin")}
        (self.root / "bin/xynolog").unlink()
        result = subprocess.run(
            ["bash", str(self.root / "tests/stack/smoke-stack.sh"), "up", "local"],
            check=False,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        assert "needs the xynolog CLI" in result.stderr
        assert self.starts() == []

    def test_up_checks_the_realm_at_the_issuer_the_gateway_names(self) -> None:
        result = self.smoke("up", "local")
        assert result.returncode == 0, result.stdout + result.stderr
        assert (self.root / "curl.log").read_text().splitlines() == [
            "http://localhost:4000/.well-known/oauth-protected-resource",
            f"{ISSUER}/.well-known/openid-configuration",
            DISCOVERY["token_endpoint"],
        ]

    def test_a_failed_up_takes_its_stack_down(self) -> None:
        result = self.smoke("up", "local", start_status="1")
        assert result.returncode == 1, result.stdout + result.stderr
        self.assert_documents_restored()
        assert not (self.kb / ".smoke-kept").exists()
        assert self.smoke("down").returncode != 0
        assert "xynolog-another-kb-gateway" not in result.stdout + result.stderr, (
            "the launcher prints a failed container's log; the smoke prints none of the machine's"
        )

    def test_e2e_and_down_refuse_without_a_stack_up(self) -> None:
        for command in ("e2e", "down"):
            result = self.smoke(command)
            assert result.returncode == 1, result.stdout + result.stderr
            assert "up" in result.stderr
        assert self.starts() == []

    def test_a_second_up_refuses_while_one_is_up(self) -> None:
        assert self.smoke("up", "local").returncode == 0
        result = self.smoke("up", "local")
        assert result.returncode == 1
        assert "tests/stack/smoke-stack.sh down" in result.stderr
        assert len(self.starts()) == 1

    def test_each_e2e_runs_on_a_fresh_knowledge_base_beside_up(self) -> None:
        assert self.smoke("up", "0.7.1").returncode == 0
        for _ in range(2):
            result = self.smoke("e2e")
            assert result.returncode == 0, result.stdout + result.stderr
        inits = self.inits()
        assert len(inits) == 3
        assert len({init["domain"] for init in inits}) == 3
        assert len({init["cwd"] for init in inits}) == 3
        for e2e in inits[1:]:
            assert os.path.realpath(e2e["cwd"]) != os.path.realpath(self.kb)
            assert not Path(e2e["cwd"]).exists()
            assert os.path.realpath(e2e["cwd"]) in self.stopped()
            # A queue that reads empty is read once.
            assert self.asked_status().count(os.path.realpath(e2e["cwd"])) == 1
        for start in self.starts()[1:]:
            assert "ghcr.io/xynolog/xynolog-gateway:0.7.1\n" in start["gateway"]
        assert os.path.realpath(self.kb) not in self.stopped()
        calls = (self.root / "runtime.log").read_text()
        assert "E2E_GATEWAY_URL=http://localhost:4010" in calls
        assert "E2E_GATEWAY_URL=http://localhost:4020" in calls
        assert (self.kb / ".smoke-kept").exists()

    def test_e2e_runs_test_ci_unless_another_script_is_named(self) -> None:
        assert self.smoke("up", "0.7.1").returncode == 0
        for args in (
            (),
            ("--script", "test:slow"),
            ("--", "specs/20-x.spec.ts", "--repeat-each=5"),
            ("--script", "test:model", "--", "--grep", "two words"),
        ):
            with self.subTest(args=args):
                result = self.smoke("e2e", *args)
                assert result.returncode == 0, result.stdout + result.stderr
        assert self.suites() == [
            ["sh", "smoke-test-runtime", "test:ci"],
            ["sh", "smoke-test-runtime", "test:slow"],
            ["sh", "smoke-test-runtime", "test:ci", "specs/20-x.spec.ts", "--repeat-each=5"],
            ["sh", "smoke-test-runtime", "test:model", "--grep", "two words"],
        ]

    def test_run_gives_its_e2e_the_script_and_arguments(self) -> None:
        result = self.smoke("run", "local", "--e2e", "--script", "test:slow", "--", "specs/20-x.spec.ts")
        assert result.returncode == 0, result.stdout + result.stderr
        assert self.suites() == [["sh", "smoke-test-runtime", "test:slow", "specs/20-x.spec.ts"]]

    def test_e2e_binds_its_knowledge_base_to_the_model_named_and_up_to_inits(self) -> None:
        assert self.smoke("up", "0.7.1").returncode == 0
        for args in ((), ("--script", "test:slow", "--model", "gemma4:26b")):
            with self.subTest(args=args):
                result = self.smoke("e2e", *args)
                assert result.returncode == 0, result.stdout + result.stderr
        up, default, named = self.inits()
        assert up["flags"] == ["--yes", "--domain", "example.github.io:stack-smoke"]
        assert default["flags"] == ["--yes", "--domain", default["domain"]]
        assert named["flags"] == ["--yes", "--domain", named["domain"], "--model", "gemma4:26b"]
        assert self.suites() == [["sh", "smoke-test-runtime", "test:ci"], ["sh", "smoke-test-runtime", "test:slow"]]

    def test_run_gives_its_e2e_the_model(self) -> None:
        result = self.smoke("run", "local", "--e2e", "--model", "gemma4:26b")
        assert result.returncode == 0, result.stdout + result.stderr
        up, e2e = self.inits()
        assert "--model" not in up["flags"]
        assert e2e["flags"][-2:] == ["--model", "gemma4:26b"]

    def test_an_option_it_does_not_know_starts_nothing(self) -> None:
        for args in (
            ("e2e", "--scirpt", "test:slow"),
            ("e2e", "--script"),
            ("e2e", "--script", ""),
            ("e2e", "--model"),
            ("e2e", "--model", ""),
            ("e2e", "specs/20-x.spec.ts"),
            ("run", "local", "--script", "test:slow"),
            ("run", "local", "--e2e", "test:slow"),
        ):
            with self.subTest(args=args):
                result = self.smoke(*args)
                assert result.returncode == 2, result.stdout + result.stderr
                assert "usage" in result.stderr
        assert self.inits() == []

    def test_a_failed_e2e_leaves_its_knowledge_base_up_until_down(self) -> None:
        assert self.smoke("up", "0.7.1").returncode == 0
        self.use_runtime("smoke-test-runtime", 7)
        result = self.smoke("e2e")
        assert result.returncode == 1, result.stdout + result.stderr
        kept = os.path.realpath(self.inits()[1]["cwd"])
        assert Path(kept).exists()
        assert kept not in self.stopped()
        assert Path(kept).parent.name in result.stdout
        assert "tests/stack/smoke-stack.sh down" in result.stdout
        result = self.smoke("down")
        assert result.returncode == 0, result.stdout + result.stderr
        assert not Path(kept).exists()
        # The shared containers stop with the last knowledge base, so UP's is last.
        assert self.stopped() == [kept, os.path.realpath(self.kb)]
        self.assert_documents_restored()

    def test_e2e_fails_on_a_job_left_pending_or_running(self) -> None:
        assert self.smoke("up", "0.7.1").returncode == 0
        for queue, reason in (
            ("2 pending · 0 running", "2 pending and 0 running"),
            (
                "0 pending · 1 running · 3 completed · 0 failed since worker start",
                "0 pending and 1 running",
            ),
            ("", "no queue line"),
        ):
            with self.subTest(queue=queue):
                result = self.smoke("e2e", queue=queue)
                assert result.returncode == 1, result.stdout + result.stderr
                assert reason in result.stdout
                kept = os.path.realpath(self.inits()[-1]["cwd"])
                assert Path(kept).exists(), "a failed run leaves its KB"
                assert kept not in self.stopped()
                # Read again and again while it does not read empty.
                assert self.asked_status().count(kept) > 1
        left = [os.path.realpath(init["cwd"]) for init in self.inits()[1:]]
        result = self.smoke("down")
        assert result.returncode == 0, result.stdout + result.stderr
        for kept in left:
            assert not Path(kept).exists()
        assert self.stopped() == [*left, os.path.realpath(self.kb)]

    def test_run_with_e2e_uses_the_selected_runtime_and_takes_everything_down(
        self,
    ) -> None:
        for runtime in ("container", "docker", "podman"):
            for status in (0, 7):
                with self.subTest(runtime=runtime, status=status):
                    for name in (
                        "starts.jsonl",
                        "inits.jsonl",
                        "xynolog.jsonl",
                        "runtime.log",
                        "suites.log",
                    ):
                        (self.root / name).unlink(missing_ok=True)
                    shutil.rmtree(self.kb, ignore_errors=True)
                    self.use_runtime(runtime, status)
                    result = self.smoke("run", "local", "--e2e")
                    assert result.returncode == int(status != 0), result.stdout + result.stderr
                    self.assert_documents_restored()
                    assert not (self.kb / ".smoke-kept").exists()
                    calls = (self.root / "runtime.log").read_text()
                    assert "e2e-localhost-bridge.mjs" in calls
                    assert "sh " + runtime in calls
                    if runtime == "container":
                        assert "--network host" not in calls
                        assert "--ipc host" not in calls
                    else:
                        assert "--network host --ipc host" in calls
                    stops = self.stopped()
                    assert stops[-1] == os.path.realpath(self.kb)
                    assert os.path.realpath(self.kb) not in stops[:-1]
                    # Passed or failed, the e2e's knowledge base is gone when run is done.
                    e2e = os.path.realpath(self.inits()[1]["cwd"])
                    assert e2e in stops
                    assert not Path(e2e).exists()
                    assert self.suites() == [["sh", runtime, "test:ci"]]


if __name__ == "__main__":
    unittest.main()
