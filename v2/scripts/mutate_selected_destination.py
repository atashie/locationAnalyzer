"""Does `test_selected_destination.py` actually catch a wrong destination recovery?

The recurring failure in this project is a check that passes for the shape of defect I happened to
imagine. Writing the tests is not evidence; defeating them is. This script applies each plausible
wrong implementation in turn and requires a test to notice.

My first fixture here could not see mutation 3 at all: it hung a penalised shop off the far
endpoint, which made both endpoints select the *same* shop, so swapping `e_idx` for `s_idx`
changed nothing observable. That is the mutation this script exists to keep catchable.

    python scripts/mutate_selected_destination.py

Exits non-zero if any mutation survives. Both source files are restored in a `finally` block and
byte-identity is verified by SHA-256 before exiting.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARRIVAL = ROOT / "locfinder" / "traveltime" / "arrival.py"
SNAP = ROOT / "locfinder" / "traveltime" / "snap.py"
TESTS = "tests/test_selected_destination.py"

# Named rather than written inline: every attempt to put these through a shell heredoc so far
# has arrived as a real newline instead of an escape.
LF = chr(10)
CRLF = chr(13) + chr(10)

# (label, file, old, new) -- `old` must appear exactly once.
MUTATIONS: list[tuple[str, pathlib.Path, str, str]] = [
    (
        "return a POSITION in dest_idx instead of a node id",
        ARRIVAL,
        "    selected = np.asarray(sources, dtype=np.int64)",
        "    selected = np.searchsorted(dest, np.asarray(sources, dtype=np.int64))",
    ),
    (
        "select the destination on TIME instead of cost",
        ARRIVAL,
        "    dist, pred, sources = dijkstra(\n"
        "        cost_t, directed=True, indices=dest, min_only=True, return_predecessors=True\n"
        "    )",
        "    dist, pred, sources = dijkstra(\n"
        "        time_t, directed=True, indices=dest, min_only=True, return_predecessors=True\n"
        "    )",
    ),
    (
        "keep a destination on a node with no finite time",
        ARRIVAL,
        "    selected = np.where(np.isfinite(out), selected, -1)",
        "    selected = selected",
    ),
    (
        "take the OTHER endpoint's destination",
        SNAP,
        "    chosen = np.where(take_end, e_idx, s_idx)",
        "    chosen = np.where(take_end, s_idx, e_idx)",
    ),
    (
        "invert the time-fallback branch choice",
        SNAP,
        "        take_end = time_end <= time_start",
        "        take_end = time_start < time_end",
    ),
    (
        "keep an endpoint where no branch was available",
        SNAP,
        "    chosen = np.where(np.isfinite(network), chosen, -1)",
        "    chosen = chosen",
    ),
    (
        "let an off-network point keep a destination",
        SNAP,
        "    out = np.where(np.isfinite(total), out, -1)",
        "    out = out",
    ),
    (
        "accept a selected array from another graph",
        SNAP,
        "    if sel.shape != (T.shape[0],):",
        "    if False:",
    ),
]


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: pathlib.Path) -> str:
    """Decode without newline translation, so writing it back is byte-faithful.

    `Path.read_text` uses universal newlines and `Path.write_text` re-encodes a newline as
    `os.linesep`, so the pair silently rewrites an LF file to CRLF on Windows -- which made this
    script's own "restored byte-identically" check fail on its first run, and would make the claim
    a lie on any repository that does not normalise line endings on commit.
    """
    return path.read_bytes().decode("utf-8")


def write(path: pathlib.Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def localise(anchor: str, source: str) -> str:
    """Rewrite a newline-separated anchor to the line ending `source` actually uses.

    The anchors below are written with plain newlines, but `read` no longer translates, so
    on a CRLF checkout a multi-line anchor would simply never match -- and a mutation that
    cannot be applied reports as surviving, which looks identical to a test that cannot see
    it. Making the anchors line-ending agnostic keeps those two failures distinguishable.
    """
    if CRLF in source:
        return anchor.replace(LF, CRLF)
    return anchor


def run_tests() -> bool:
    """True if the suite passes."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-x", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True,
    )
    return proc.returncode == 0


def main() -> int:
    originals = {p: read(p) for p in (ARRIVAL, SNAP)}
    before = {p: digest(p) for p in originals}
    survived: list[str] = []

    try:
        if not run_tests():
            print("FAIL: the unmutated tests do not pass; nothing below would mean anything")
            return 1
        print(f"baseline passes\n")

        for label, path, old, new in MUTATIONS:
            source = originals[path]
            old, new = localise(old, source), localise(new, source)
            count = source.count(old)
            if count != 1:
                print(f"SKIP         {label}: anchor appears {count} times in {path.name}; "
                      "the mutation needs updating to match the current source")
                survived.append(label)
                continue
            write(path, source.replace(old, new, 1))
            try:
                if run_tests():
                    print(f"NOT CAUGHT   {label}  <-- no test sees this")
                    survived.append(label)
                else:
                    print(f"caught       {label}")
            finally:
                write(path, source)
    finally:
        for path, text in originals.items():
            write(path, text)

    for path in originals:
        if digest(path) != before[path]:
            print(f"\nFAIL: {path.name} was not restored byte-identically")
            return 1
    print("\nboth sources restored byte-identically")

    if survived:
        print(f"{len(survived)} of {len(MUTATIONS)} mutations survived:")
        for label in survived:
            print(f"  - {label}")
        return 1
    print(f"all {len(MUTATIONS)} mutations caught")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
