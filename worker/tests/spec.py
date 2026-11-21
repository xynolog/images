"""Where the repository around this project is, for the tests that hold the project to it."""

from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
SPEC = ROOT / "protocol/specs/src"
SDK = ROOT / ".local/sdk-artifacts/current/python/sdk-manifest"
