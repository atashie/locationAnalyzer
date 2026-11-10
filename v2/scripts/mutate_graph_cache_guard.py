"""Does `test_graph_cache_manifest.py` actually catch a graph cache that should be refused?

Codex pass 35 defeated the first version of these tests with four mutations, three of them
consequential: rejecting a missing `surface` while waving every other missing tag through; calling
`load_graphml`, swallowing the exception and *then* validating; and loading a valid graph twice. The
tests had been written by imagining how the guard would fail, which is the fourth time in this
project that has not been enough -- see
`docs/engineering-notes/feedback-verify-the-shape-of-the-risk.md`.

    python scripts/mutate_graph_cache_guard.py

Exits non-zero if any mutation survives. The source is restored in a `finally` block and
byte-identity is verified by SHA-256 before exiting.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMMON = ROOT / "spikes" / "_common.py"
TESTS = "tests/test_graph_cache_manifest.py"

LF = chr(10)
CRLF = chr(13) + chr(10)

# (label, old, new) -- `old` must appear exactly once in _common.py.
MUTATIONS: list[tuple[str, str, str]] = [
    # Pass 35's three consequential survivors.
    (
        "reject a missing `surface` and wave every other missing tag through",
        '    missing = sorted(set(want["required_way_tags"]) - set(stored.get("way_tags") or []))',
        '    missing = ["surface"] if "surface" not in (stored.get("way_tags") or []) else []',
    ),
    (
        "read the graph first, swallow the failure, then validate",
        "    why = graph_cache_complaint(read_graph_cache_manifest(path), path)\n"
        "    if why:\n"
        "        raise SystemExit(f\"{path.name} is stale: {why}.{REBUILD_HINT}\")\n"
        "    return ox.load_graphml(path)",
        "    try:\n"
        "        early = ox.load_graphml(path)\n"
        "    except Exception:\n"
        "        early = None\n"
        "    why = graph_cache_complaint(read_graph_cache_manifest(path), path)\n"
        "    if why:\n"
        "        raise SystemExit(f\"{path.name} is stale: {why}.{REBUILD_HINT}\")\n"
        "    return early if early is not None else ox.load_graphml(path)",
    ),
    (
        "read the graph twice",
        "    return ox.load_graphml(path)",
        "    ox.load_graphml(path)\n    return ox.load_graphml(path)",
    ),
    # The binding that pass 35 F1 found missing, mutated in each of its parts.
    (
        "ignore the graph's sha256",
        '    if stored.get("graphml_sha256") != digest:',
        "    if False:",
    ),
    (
        "ignore the graph's size",
        '    if stored.get("graphml_bytes") != size:',
        "    if False:",
    ),
    (
        "decide reuse with no graph file at all",
        '    if graph_path is None:\n'
        '        return "checked without a graph file, so the manifest is not bound to anything"',
        "    if graph_path is None:\n        return None",
    ),
    (
        "ignore the parse options",
        '    if stored.get("parse") != want["parse"]:',
        "    if False:",
    ),
    (
        "ignore the source file name",
        '    if stored.get("source") != want["source"]:',
        "    if False:",
    ),
    (
        "accept a cache with no manifest",
        "    if stored is None:\n"
        '        return ("no tag manifest beside it, so the way tags it was parsed with are unknown "\n'
        "                f\"(today's rules need {', '.join(want['required_way_tags'])})\")",
        "    if stored is None:\n        return None",
    ),
    (
        "require only EXTRA_WAY_TAGS, not what osmnx retains by default",
        '        "required_way_tags": sorted(set(ox.settings.useful_tags_way) | set(EXTRA_WAY_TAGS)),',
        '        "required_way_tags": sorted(EXTRA_WAY_TAGS),',
    ),
    (
        "certify a graph that does not declare a tag we added on purpose",
        "    if unconfirmed:\n        raise SystemExit(",
        "    if False:\n        raise SystemExit(",
    ),
    (
        "read node key declarations as if they were edge ones",
        '_KEY_DECL = re.compile(r\'<key[^>]*\\bfor="edge"[^>]*\\battr\\.name="([^"]+)"\')',
        '_KEY_DECL = re.compile(r\'<key[^>]*\\battr\\.name="([^"]+)"\')',
    ),
]


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: pathlib.Path) -> str:
    """Decode without newline translation, so writing it back is byte-faithful."""
    return path.read_bytes().decode("utf-8")


def write(path: pathlib.Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def localise(anchor: str, source: str) -> str:
    """Rewrite a newline-separated anchor to the line ending `source` actually uses."""
    return anchor.replace(LF, CRLF) if CRLF in source else anchor


def run_tests() -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-x", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True,
    )
    return proc.returncode == 0


def main() -> int:
    original = read(COMMON)
    before = digest(COMMON)
    survived: list[str] = []

    try:
        if not run_tests():
            print("FAIL: the unmutated tests do not pass; nothing below would mean anything")
            return 1
        print("baseline passes\n")

        for label, old, new in MUTATIONS:
            old_l, new_l = localise(old, original), localise(new, original)
            count = original.count(old_l)
            if count != 1:
                print(f"SKIP         {label}: anchor appears {count} times; the mutation needs "
                      "updating to match the current source")
                survived.append(label)
                continue
            write(COMMON, original.replace(old_l, new_l, 1))
            try:
                if run_tests():
                    print(f"NOT CAUGHT   {label}  <-- no test sees this")
                    survived.append(label)
                else:
                    print(f"caught       {label}")
            finally:
                write(COMMON, original)
    finally:
        write(COMMON, original)

    if digest(COMMON) != before:
        print(f"\nFAIL: {COMMON.name} was not restored byte-identically")
        return 1
    print("\nsource restored byte-identically")

    if survived:
        print(f"{len(survived)} of {len(MUTATIONS)} mutations survived:")
        for label in survived:
            print(f"  - {label}")
        return 1
    print(f"all {len(MUTATIONS)} mutations caught")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
