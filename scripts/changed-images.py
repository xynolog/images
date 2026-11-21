#!/usr/bin/env python3
"""Print the image build groups a change between two commits affects.

Usage: changed-images.py <base commit> <head commit>

An image is affected when a changed path is one of its inputs:
- its Dockerfile, and every path the Dockerfile copies from the build context
  (the repository root);
- its language's shared root, the Makefile group it belongs to naming the
  language;
- what scripts/build-session.sh stages into .local/ for it, by where that is
  built from;
- what every build reads: the Makefile, scripts/, build-tools/, upstream.lock.json,
  .dockerignore and this workflow.

With no base (a new branch, or a base this clone does not have), every image
is affected. A Dockerfile that copies a path which neither exists nor is
staged fails the run, by its path: a new input must be added here, not missed.
Whether a path exists is git's answer, so the check needs no submodule checked
out.

The output is the build matrix: a JSON list of {"name", "images"} groups, the
Rust images together, since they share one compile of the workspace.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EVERY_BUILD = ["Makefile", "scripts", "build-tools", "upstream.lock.json", ".dockerignore", ".github/workflows/ci.yml"]

SHARED_ROOT = {
    "RUST_IMAGES": ["packages/rust"],
    "PYTHON_IMAGES": ["shared/python"],
    "TYPESCRIPT_IMAGES": [],
}

# What build-session.sh stages into the build context, by what it is built from.
STAGED = {
    ".local/sdk-artifacts/": ["upstream.lock.json"],
    ".local/shared-python-packages/": ["shared/python"],
    "${BROWSER_PACKAGE_DIR}": ["browser", "brand"],
}


def group(variable: str) -> list[str]:
    output = subprocess.check_output([str(ROOT / "scripts/image-groups.sh"), variable], text=True)
    return output.split()


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *arguments], text=True)


def in_tree(path: str, tracked: list[str], submodules: list[str]) -> bool:
    """Whether git holds the path: a tracked file, a directory of them, or a path inside a submodule."""
    return (
        path in tracked or any(each.startswith(path + "/") for each in tracked) or any(path.startswith(each + "/") for each in submodules)
    )


def copied_paths(image: str, tracked: list[str], submodules: list[str]) -> list[str]:
    """The build-context paths an image's Dockerfile copies, staged ones resolved to their sources."""
    dockerfile = f"{image}/Dockerfile"
    paths = [dockerfile]
    for line in (ROOT / dockerfile).read_text().splitlines():
        words = line.split()
        if not words or words[0] not in ("COPY", "ADD"):
            continue
        if words[1].startswith("["):
            raise SystemExit(f"{dockerfile}: the JSON form of {words[0]} is not read here: {line}")
        flags = [word for word in words[1:] if word.startswith("--")]
        if any(flag.startswith("--from=") for flag in flags):
            continue
        sources = [word for word in words[1:] if not word.startswith("--")][:-1]
        for source in sources:
            staged = next((prefix for prefix in STAGED if source.startswith(prefix)), None)
            if staged is not None:
                paths.extend(STAGED[staged])
                continue
            literal = re.split(r"[*?\[$]", source, maxsplit=1)[0].rstrip("/")
            if not literal or not in_tree(literal, tracked, submodules):
                raise SystemExit(f"{dockerfile} copies {source}, which is neither in the tree nor staged by build-session.sh")
            paths.append(literal)
    return paths


def touches(changed: str, path: str) -> bool:
    """A changed file, or a changed submodule, inside or around an input path."""
    return changed == path or changed.startswith(path + "/") or path.startswith(changed + "/")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: changed-images.py <base commit> <head commit>")
    base, head = sys.argv[1], sys.argv[2]

    tracked = git("ls-files", "-z").split("\0")
    submodules = [line.split("\t", 1)[1] for line in git("ls-files", "--stage").splitlines() if line.startswith("160000 ")]
    language_of = {image: variable for variable in SHARED_ROOT for image in group(variable)}
    every = group("IMAGE_NAMES")
    if sorted(every) != sorted(language_of):
        raise SystemExit(f"IMAGE_NAMES {every} is not the union of {sorted(SHARED_ROOT)}")

    known_base = (
        bool(base.strip("0"))
        and subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{base}^{{commit}}"], capture_output=True).returncode == 0
    )
    if known_base:
        changed = git("diff", "--name-only", f"{base}...{head}").split()
    else:
        print(f"No base commit to compare with ({base or 'none'}): every image is affected", file=sys.stderr)
        changed = []

    affected: list[str] = []
    for image in every:
        inputs = copied_paths(image, tracked, submodules) + SHARED_ROOT[language_of[image]] + EVERY_BUILD
        hits = sorted({path for path in changed for each in inputs if touches(path, each)})
        if not known_base or hits:
            affected.append(image)
            print(f"{image}: {', '.join(hits[:5]) if hits else 'every image'}", file=sys.stderr)

    rust = [image for image in affected if language_of[image] == "RUST_IMAGES"]
    rest = [image for image in affected if language_of[image] != "RUST_IMAGES"]
    groups = [
        {"name": name, "images": " ".join(images)} for name, images in (("the Rust images", rust), ("the other images", rest)) if images
    ]
    print(json.dumps(groups))


if __name__ == "__main__":
    main()
