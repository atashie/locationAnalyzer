"""Did a change to the T0 pilot move any measured quantity?

A re-run of `t0_attachment_pilot.py` is never byte-identical: it stamps a build time, the runtime
versions, and a wall-clock figure for every stage. Those paths are stripped here and everything else
is compared **structurally** — container shapes, key sets, list lengths and typed leaves — so
"behaviour preserving" is a checked claim rather than an impression.

    python scripts/compare_t0_artifacts.py BEFORE.json AFTER.json
    python scripts/compare_t0_artifacts.py --self-test

Exits non-zero if anything outside the volatile paths differs.

**Why structural rather than flattened.** The first version flattened the document to dotted paths
and compared the leaves. Codex pass 38 F7 showed what that misses: `{"x": []}` and `{"x": [{}]}`
produce no leaves under `x` and so compared equal, `{"x": {}}` matched `{}`, and a literal key
`"a.b"` collided with a nested `{"a": {"b": ...}}`. Leaves are also compared with their **types**,
because `False == 0` and `-0.0 == 0.0` in Python and neither pair is the same artifact value.

Floats are compared by exact identity of their `repr`, deliberately: this tool exists to detect a
changed arithmetic, so a tolerance would hide the thing it is looking for, and `repr` separates
`0.0` from `-0.0` while still treating two NaNs as the same absence.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

#: Dotted paths dropped before comparison, with `*` matching one path element. Everything else is
#: compared, including counts, histograms, digests and the figures rendered into the write-up.
VOLATILE: tuple[str, ...] = (
    "built",
    "pinned.runtime",          # python/numpy/shapely/platform: pinned provenance, not measured
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


def _volatile(path: tuple[str, ...], volatile: tuple[str, ...]) -> bool:
    return any(_matches(path, p) for p in volatile)


def _show(path: tuple[str, ...]) -> str:
    """A path for display only. Comparison never joins the elements, so no collision is possible."""
    return "".join(f"[{p[1:]}]" if p.startswith("#") else (f".{p}" if i else p)
                   for i, p in enumerate(path)) or "<root>"


def _leaf(value) -> tuple[str, str]:
    """A leaf as (type name, exact text). The type is carried so `False` and `0` stay distinct."""
    return (type(value).__name__, repr(value))


def diff(a, b, volatile: tuple[str, ...], path: tuple[str, ...] = ()) -> list[str]:
    """Every structural difference between two JSON values, volatile paths skipped."""
    if _volatile(path, volatile):
        return []
    out: list[str] = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) - set(b)):
            if not _volatile(path + (str(k),), volatile):
                out.append(f"REMOVED   {_show(path + (str(k),))}")
        for k in sorted(set(b) - set(a)):
            if not _volatile(path + (str(k),), volatile):
                out.append(f"ADDED     {_show(path + (str(k),))}")
        for k in sorted(set(a) & set(b), key=str):
            out.extend(diff(a[k], b[k], volatile, path + (str(k),)))
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"LENGTH    {_show(path)}: {len(a)} -> {len(b)}")
        for i in range(min(len(a), len(b))):
            out.extend(diff(a[i], b[i], volatile, path + (f"#{i}",)))
        return out
    if type(a) is not type(b) and not (isinstance(a, bool) or isinstance(b, bool)):
        # int against float is still a type change in a JSON document, and worth seeing.
        out.append(f"TYPE      {_show(path)}: {_leaf(a)} -> {_leaf(b)}")
        return out
    if _leaf(a) != _leaf(b):
        out.append(f"CHANGED   {_show(path)}: {_leaf(a)[1]} -> {_leaf(b)[1]}")
    return out


def self_test() -> int:
    """Can this tool fail? Planted differences it must catch, and volatile ones it must ignore.

    A comparison tool that always says "same" is worse than no tool, and this one is the whole
    evidence for the phrase "nothing moved". The structural cases are Codex pass 38 F7's.
    """
    cases: list[tuple[str, object, object, bool]] = [
        ("identical documents", {"a": {"b": [1, 2]}}, {"a": {"b": [1, 2]}}, False),
        ("a changed count", {"a": 1}, {"a": 2}, True),
        ("a one-ulp float nested in a list", {"a": [{"b": 1.0}]}, {"a": [{"b": 1.0000000000000002}]},
         True),
        ("an added key", {"a": 1}, {"a": 1, "b": 2}, True),
        ("a removed key", {"a": 1, "b": 2}, {"a": 1}, True),
        # F7's four: each pair used to compare equal.
        ("an empty list against a list holding an empty dict", {"x": []}, {"x": [{}]}, True),
        ("an empty dict against a missing key", {"x": {}}, {}, True),
        ("a literal dotted key against a nested one", {"a.b": 1}, {"a": {"b": 1}}, True),
        ("False against 0", {"x": False}, {"x": 0}, True),
        ("negative zero against zero", {"x": -0.0}, {"x": 0.0}, True),
        # volatile paths, which must be ignored however much they change
        ("a tampered build stamp", {"built": "x", "a": 1}, {"built": "y", "a": 1}, False),
        ("a different numpy version", {"pinned": {"runtime": {"numpy": "1"}}, "a": 1},
         {"pinned": {"runtime": {"numpy": "2"}}, "a": 1}, False),
        ("a different stage duration", {"sets": {"s": {"seconds": 1.0, "eligible": 3}}},
         {"sets": {"s": {"seconds": 9.0, "eligible": 3}}}, False),
    ]
    failures = 0
    for label, before, after, must_differ in cases:
        found = diff(before, after, VOLATILE)
        ok = bool(found) == must_differ
        want = "a difference" if must_differ else "no difference"
        print(f"{'ok  ' if ok else 'FAIL'} {label}: expected {want}, found {len(found)}"
              + (f" ({found[0]})" if found else ""))
        if not ok:
            failures += 1
    print(f"\n{len(cases) - failures} of {len(cases)} self-tests behaved")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("before", type=pathlib.Path, nargs="?")
    ap.add_argument("after", type=pathlib.Path, nargs="?")
    ap.add_argument("--self-test", action="store_true",
                    help="check that this tool can detect a difference at all, and still ignores "
                         "the volatile fields")
    ap.add_argument("--max-print", type=int, default=40,
                    help="how many differences to print in full (default 40)")
    ap.add_argument("--ignore", action="append", default=[], metavar="PATH",
                    help="an extra dotted path to drop, repeatable. Use it to add a new SECTION to "
                         "an artifact and still check that nothing already measured moved, e.g. "
                         "--ignore adoption. Naming a path that holds a measured figure hides "
                         "exactly what this tool is for, so name only what you added")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.before is None or args.after is None:
        ap.error("give two artifacts, or --self-test")

    volatile = VOLATILE + tuple(args.ignore)
    found = diff(json.loads(args.before.read_text(encoding="utf-8")),
                 json.loads(args.after.read_text(encoding="utf-8")), volatile)

    for line in found[:args.max_print]:
        print(line)
    if len(found) > args.max_print:
        print(f"... and {len(found) - args.max_print} more")

    if found:
        # Plain ASCII: this prints to a Windows console whose code page mangles an em dash.
        print(f"\nFAIL: {len(found)} differences - this change is NOT behaviour preserving")
        return 1
    print(f"\nno difference outside the {len(volatile)} volatile path patterns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
