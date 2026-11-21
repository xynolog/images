"""
The containers a ``--containers`` list names, for the e2e log scripts.

Each entry is a full container name (``xynolog-…``), used as is, or a bare
product (``gateway``): the one container that ``container list --all`` shows
as ``xynolog-<product>`` (the machine's, such as the worker) or
``xynolog-<kb>-<product>`` (a knowledge base's, such as the gateway and the
smelter). With several knowledge bases running, a bare product matches
several and is skipped: name those containers in full.
"""

import subprocess


def resolve_containers(entries: list[str]) -> tuple[list[str], list[str]]:
    """The containers ``entries`` name, and why each entry that names none, or several, was skipped."""
    listed: list[str] = []
    if any(not e.startswith("xynolog-") for e in entries):
        try:
            result = subprocess.run(["container", "list", "--all"], capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return [], ["`container` CLI not on PATH — is Apple Container installed?"]
        if result.returncode != 0:
            return [], [f"container list --all failed: {result.stderr.strip() or f'(exit {result.returncode})'}"]
        listed = [f[0] for f in (line.split() for line in result.stdout.splitlines()) if f and f[0].startswith("xynolog-")]
    names: list[str] = []
    skipped: list[str] = []
    for entry in entries:
        matches = [entry] if entry.startswith("xynolog-") else [n for n in listed if n.endswith(f"-{entry}")]
        if len(matches) == 1:
            names.append(matches[0])
        elif matches:
            skipped.append(f"{entry} matches several containers ({', '.join(matches)}) — skipped; pass full names with --containers")
        else:
            skipped.append(f"no container xynolog-{entry} or xynolog-<kb>-{entry} — skipped")
    return names, skipped
