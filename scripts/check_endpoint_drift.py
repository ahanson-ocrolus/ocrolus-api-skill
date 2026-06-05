#!/usr/bin/env python3
"""Endpoint drift guard.

`references/endpoints.md` is the canonical, live-validated inventory of Ocrolus
API paths (the official OpenAPI spec is incomplete, so it is not the source of
truth). This script extracts every API path referenced elsewhere in the skill —
SKILL.md, the other references/*.md files, and scripts/*.py — and asserts each
one appears in endpoints.md. It exists because the same path used to be restated
in several places and drifted.

Validate endpoints.md itself against the live API with scripts/health_check.py;
this guard only enforces that everything else stays consistent with it.

Run it as a pre-commit / CI gate:

    python scripts/check_endpoint_drift.py        # exit 1 on drift
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "references/endpoints.md"

# Paths referenced in the skill that are intentionally absent from endpoints.md:
# a different host, or cited only as "do not use" negative examples.
ALLOWED_EXTRA = {
    "/v1/widget/{}/token",  # widget.ocrolus.com host, not the API host
    "/v1/book/create",      # negative example ("the endpoint is /add, not /create")
    "/v1/book",             # negative example (Things People Miss)
}

# Files whose path references must stay consistent with endpoints.md.
SCAN_GLOBS = ["SKILL.md", "references/*.md", "scripts/*.py"]
# ...except these (the canonical file itself, this guard, and the vendored spec).
SKIP_NAMES = {CANONICAL.name, Path(__file__).name}

# A path candidate: starts with /oauth or /v<n>, separated by '/' segments.
PATH_RE = re.compile(r"(?:\{\{BASE_URL\}\})?(/(?:oauth|v\d+)(?:/[A-Za-z0-9_.:${}\-]+)*)")
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-")


def normalize(path: str) -> str:
    """Collapse path/template params to '{}' so refs and canonical compare equal."""
    path = path.split("?")[0].rstrip("/.,)`'\"")
    out = []
    for seg in path.split("/"):
        if seg and (
            seg.startswith(("{", ":", "$")) or seg.isdigit() or _UUID_RE.match(seg)
        ):
            out.append("{}")
        else:
            out.append(seg)
    return "/".join(out)


def extract(text: str):
    """Yield (lineno, raw, normalized) for each API path candidate in text."""
    for lineno, line in enumerate(text.splitlines(), 1):
        for raw in PATH_RE.findall(line):
            if "..." in raw:  # prose ellipsis, e.g. /v2/.../signals
                continue
            norm = normalize(raw)
            if norm and norm not in ("/oauth", *(f"/v{n}" for n in range(3))):
                yield lineno, raw, norm


def canonical_paths() -> set[str]:
    return {norm for _, _, norm in extract(CANONICAL.read_text())}


def main() -> int:
    valid = canonical_paths() | {normalize(p) for p in ALLOWED_EXTRA}
    misses: list[tuple[str, int, str]] = []

    for pattern in SCAN_GLOBS:
        for f in sorted(ROOT.glob(pattern)):
            if not f.is_file() or f.name in SKIP_NAMES:
                continue
            for lineno, raw, norm in extract(f.read_text()):
                if norm not in valid:
                    misses.append((str(f.relative_to(ROOT)), lineno, raw))

    if not misses:
        print(f"OK — every referenced path is in {CANONICAL.name} ({len(valid)} known paths).")
        return 0

    print(f"DRIFT — {len(misses)} path reference(s) not found in {CANONICAL.name}:\n")
    for path, lineno, raw in misses:
        print(f"  {path}:{lineno}  ->  {raw}")
    print(f"\nFix the reference, add the endpoint to {CANONICAL.name}, "
          "or list it in ALLOWED_EXTRA if intentional.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
