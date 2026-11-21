#!/usr/bin/env python3
"""Stage verified SDK Cargo archives for a Rust image build."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import tarfile


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f"Usage: {sys.argv[0]} BUNDLE_DIR CARGO_LOCAL_DIR")

    bundle = pathlib.Path(sys.argv[1]).resolve()
    output = pathlib.Path(sys.argv[2]).resolve()
    manifest = json.loads((bundle / "artifacts.json").read_text())
    artifacts = [artifact for artifact in manifest["artifacts"] if artifact["ecosystem"] == "cargo"]
    if not artifacts:
        raise SystemExit("SDK artifact bundle contains no Cargo packages")

    crates_dir = output / "crates"
    crates_dir.mkdir(parents=True, exist_ok=True)
    patch_entries = []
    for artifact in sorted(artifacts, key=lambda item: item["package"]):
        name = artifact["package"]
        archive = bundle / artifact["path"]
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != artifact["sha256"]:
            raise SystemExit(f"Cargo archive checksum mismatch: {archive}")

        with tarfile.open(archive, "r:gz") as package:
            members = package.getmembers()
            prefix = f"{name}-{artifact['version']}/"
            for member in members:
                member_path = pathlib.PurePosixPath(member.name)
                if member_path.is_absolute() or ".." in member_path.parts or not member.name.startswith(prefix):
                    raise SystemExit(f"Unsafe Cargo archive member: {member.name}")
                if not (member.isdir() or member.isfile()):
                    raise SystemExit(f"Unsupported Cargo archive member: {member.name}")
                relative = pathlib.Path(*member_path.parts[1:])
                if not relative.parts:
                    continue
                destination = crates_dir / f"{name}-{artifact['version']}" / relative
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    source = package.extractfile(member)
                    if source is None:
                        raise SystemExit(f"Cannot read Cargo archive member: {member.name}")
                    with source, destination.open("wb") as target:
                        target.write(source.read())
                    os.chmod(destination, member.mode & 0o777)

        extracted = crates_dir / f"{name}-{artifact['version']}"
        if not (extracted / "Cargo.toml").is_file():
            raise SystemExit(f"Cargo archive did not contain Cargo.toml: {archive}")
        patch_entries.append(f'{name} = {{ path = "/sdk/cargo-local/crates/{name}-{artifact["version"]}" }}')

    config = "[patch.crates-io]\n" + "\n".join(patch_entries) + "\n"
    (output / "config.toml").write_text(config)


if __name__ == "__main__":
    main()
