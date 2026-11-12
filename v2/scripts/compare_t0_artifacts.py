"""Did a change to the T0 pilot move any measured quantity?

A re-run of `t0_attachment_pilot.py` is never byte-identical: it stamps a build time, the runtime
versions, and a wall-clock figure for every stage. Those fields are stripped here and everything
else is compared exactly, so "behaviour preserving" is a checked claim rather than an impression.

    python scripts/compare_t0_artifacts.py BEFORE.json AFTER.json

Exits non-zero if any non-volatile value differs, and prints every difference with its JSON path.
Floats are compared by **exact equality**, deliberately: this tool exists to detect a changed
arithmetic, and a tolerance would hide exactly what it is looking for.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

#: Dotted paths dropped before comparison, with `*` matching one path element. Everything else is
#: compared, including counts, histograms, digests and the figures rendered into the write-up.
VOLATILE = (
    "built",
    "pinned.runtime",          # python/numpy/shapely/platform: pinned, not measured
    "graph.prepare_s",
    "sets.*.seconds",
    "sets.*.ms_per_point",
    "subdivision.sets.*.seconds",
    "subdivision.sets.*.ms_per_point",
    "adoption.sets.*.seconds",
)


def _matches(path: tuple[str, ...], pattern: str) -> bool:
    parts = pattern.split(".")
    if len(parts) > len(path):
        return False
    return all(p == "*" or p == q for p, q in zip(parts, path[:len(parts)]))


def _volatile(path: tuple[str, ...]) -> bool:
    return any(_matches(path, p) for p in VOLATILE)


def flatten(value, path: tuple[str, ...] = ()) -> dict[str, object]:
    """Every leaf of a JSON value, keyed by its dotted path, volatile paths omitted."""
    if _volatile(path):
        return {}
    if isinstance(value, dict):
        out: dict[str, object] = {}
        for k, v in value.items():
            out.update(flatten(v, path + (str(k),)))
        return out
    if isinstance(value, list):
        out = {}
        for i, v in enumerate(value):
            out.update(flatten(v, path + (f"[{i}]",)))
        return out
    return {".".join(path): value}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("before", type=pathlib.Path)
    ap.add_argument("after", type=pathlib.Path)
    ap.add_argument("--max-print", type=int, default=40,
                    help="how many differences to print in full (default 40)")
    ap.add_argument("--ignore", action="append", default=[], metavar="PATH",
                    help="an extra dotted path to drop, repeatable. Use it to add a new SECTION "
                         "to an artifact and still check that nothing already measured moved, "
                         "e.g. --ignore adoption. Naming a path that holds a measured figure "
                         "hides exactly what this tool is for, so name only what you added")
    args = ap.parse_args(argv)
    global VOLATILE
    VOLATILE = VOLATILE + tuple(args.ignore)

    a = flatten(json.loads(args.before.read_text(encoding="utf-8")))
    b = flatten(json.loads(args.after.read_text(encoding="utf-8")))

    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    changed = sorted(k for k in set(a) & set(b) if a[k] != b[k])

    for label, keys in (("only in BEFORE", only_a), ("only in AFTER", only_b)):
        for k in keys[:args.max_print]:
            print(f"{label:16s} {k}")
        if len(keys) > args.max_print:
            print(f"{label:16s} ... and {len(keys) - args.max_print} more")

    for k in changed[:args.max_print]:
        print(f"CHANGED          {k}: {a[k]!r} -> {b[k]!r}")
    if len(changed) > args.max_print:
        print(f"CHANGED          ... and {len(changed) - args.max_print} more")

    total = len(only_a) + len(only_b) + len(changed)
    print(f"\n{len(a)} leaves compared after stripping {len(VOLATILE)} volatile path patterns")
    if total:
        # Plain ASCII: this prints to a Windows console whose code page mangles an em dash.
        print(f"FAIL: {total} differences - this change is NOT behaviour preserving")
        return 1
    print("no difference outside the volatile fields")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
