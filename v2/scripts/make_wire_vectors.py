"""Conformance vectors for the browser decoder — S3.5's "a Python round-trip cannot protect the
browser".

`locfinder/wire.py` and `spikes/g3-render/worker.js` implement the same function in two languages.
`tests/test_wire.py` proves the Python one agrees with `status.evaluate` on every published cell.
Nothing proves the **JavaScript** one agrees with either, and a browser is where the household
actually reads the answer — so this writes vectors that `worker_conformance.mjs` replays through
the real worker, and `tests/test_browser_conformance.py` runs that under pytest so it cannot be
forgotten.

Three kinds of case, and the third is the one that matters:

1. **hand-built cells**, one per distinguishable status, with the bounds that decide them;
2. **two layers**, to exercise *known failure beats unknown* — the rule the old worker inverted by
   breaking out of its layer loop on the first missing value;
3. **a window of the real published layer**, carrying every status code that occurs on it, with
   the expected verdict array hashed rather than inlined.

The window is 200 × 200 taken from the published Triangle walk surface. It is a window and not the
whole layer because the whole layer is already checked in Python; what this file has to establish
is that two *implementations* agree, and a window that contains every code establishes it at a
fortieth of the bytes. The script asserts the window really does contain every code rather than
hoping, and fails if it does not.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from locfinder import wire                                      # noqa: E402
from locfinder.status import (CATEGORY_COST_SELECTED, Criterion,  # noqa: E402
                              Reason, Surface, evaluate)

V2 = pathlib.Path(__file__).resolve().parents[1]
LAYERS = V2 / "data" / "layers"
OUT = V2 / "spikes" / "g3-render" / "fixtures" / "conformance"
WINDOW = 200
THRESHOLDS = (1, 5, 10, 15, 25, 45, 60, 120, 121)


def surface_from(seconds, reason, lower, horizon_s=7200.0) -> Surface:
    return Surface(mode="walk", engine="own-graph", target="grocery",
                   aggregation=CATEGORY_COST_SELECTED, horizon_s=horizon_s,
                   seconds=np.asarray(seconds, dtype=np.float64),
                   reason=np.asarray(reason, dtype=np.int8),
                   min_possible_s=np.asarray(lower, dtype=np.float64)).validate()


def digest(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr, dtype=np.int8).tobytes()).hexdigest()[:32]


def hand_built():
    """Five per-cell statuses and the bounds that separate them, plus the legacy minute values."""
    seconds = [300.0, 600.0, 601.0, np.inf, np.inf, np.inf, np.inf, 251 * 60.0, 254 * 60.0]
    reason = [Reason.OK, Reason.OK, Reason.OK, Reason.OFF_NETWORK, Reason.OFF_NETWORK,
              Reason.BEYOND_HORIZON, Reason.NO_PATH, Reason.OK, Reason.OK]
    # `Surface.validate` requires a BEYOND_HORIZON cell to carry the horizon **exactly** as its
    # bound, which is why that entry tracks `horizon_s` below. It also makes the value plane
    # redundant for that code -- the decoder compares against the manifest's horizon and never
    # against the stored bound, so a malformed one cannot move a verdict.
    lower = [300.0, 600.0, 601.0, 180.0, 2400.0, 254 * 60.0, np.inf, 251 * 60.0, 254 * 60.0]
    # The horizon has to be at least the largest OK time or `Surface.validate` rejects it; 254
    # minutes of travel time is not a real answer on this graph, it is here because 251-254 are
    # real answers in artifacts on disk and S3.5 forbids reinterpreting them as sentinels.
    return surface_from(seconds, reason, lower, horizon_s=254 * 60.0)


def real_window():
    """A 200 x 200 window of the published layer containing every status code it produces."""
    seconds = np.load(LAYERS / "own_triangle_grocery_walk.npy").astype(np.float64)
    reason = np.load(LAYERS / "own_triangle_grocery_walk_reason.npy")
    lower = np.load(LAYERS / "own_triangle_grocery_walk_min_possible_s.npy").astype(np.float64)
    horizon = json.loads(
        (LAYERS / "own_triangle_grocery_walk_build.json").read_text())["horizon_s"]
    wanted = set(np.unique(reason).tolist())
    best = None
    for r0 in range(0, seconds.shape[0] - WINDOW + 1, 50):
        for c0 in range(0, seconds.shape[1] - WINDOW + 1, 50):
            sl = (slice(r0, r0 + WINDOW), slice(c0, c0 + WINDOW))
            got = set(np.unique(reason[sl]).tolist())
            if got == wanted:
                best = sl
                break
        if best:
            break
    if best is None:
        raise SystemExit(
            f"no {WINDOW}x{WINDOW} window holds every status code {sorted(wanted)}; a window that "
            "misses one would check less than it claims, so this refuses rather than shrinking "
            "the claim silently")
    surf = surface_from(seconds[best], reason[best], lower[best], horizon_s=horizon)
    return surf, (best[0].start, best[1].start)


def layer_entry(name: str, surf: Surface) -> tuple[dict, np.ndarray, np.ndarray]:
    value, status = wire.encode_planes(surf)
    return ({"id": name, "horizon_s": surf.horizon_s,
             "value_file": f"{name}.value.bin", "status_file": f"{name}.status.bin"},
            value, status)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    groups = []

    # ---------------------------------------------------------------- hand-built, one layer
    surf = hand_built()
    entry, value, status = layer_entry("hand", surf)
    cases = []
    for t in (1, 3, 5, 10, 11, 39, 40, 41, 120, 251, 252, 254):
        expected = evaluate(
            Criterion(label=f"g{t}", mode="walk", target="grocery", kind="category",
                      threshold_s=float(t) * 60.0), surf)
        from_wire = wire.outcome_planes(value, status, threshold_min=t,
                                        horizon_s=surf.horizon_s)
        assert np.array_equal(expected, from_wire), f"python disagrees with itself at T={t}"
        verdict = wire.combine_planes([from_wire])
        cases.append({"name": f"hand T={t}", "thresholds": [t], "enabled": [True],
                      "verdicts": [int(v) for v in verdict]})
    groups.append({"name": "hand-built statuses", "nrows": 1, "ncols": len(value),
                   "layers": [entry], "planes": [(value, status)], "cases": cases})

    # ---------------------------------------------------------------- two layers
    # Layer A is unknown on the cell where layer B is a known failure. The combined verdict must be
    # EXCLUDED. The old worker broke out of its loop at A and reported unknown.
    a = surface_from([np.inf, 300.0], [Reason.OFF_NETWORK, Reason.OK], [60.0, 300.0])
    b = surface_from([1800.0, np.inf], [Reason.OK, Reason.OFF_NETWORK], [1800.0, 60.0])
    ea, va, sa = layer_entry("twoA", a)
    eb, vb, sb = layer_entry("twoB", b)
    oa = wire.outcome_planes(va, sa, threshold_min=10, horizon_s=a.horizon_s)
    ob = wire.outcome_planes(vb, sb, threshold_min=10, horizon_s=b.horizon_s)
    groups.append({
        "name": "known failure beats unknown", "nrows": 1, "ncols": 2,
        "layers": [ea, eb], "planes": [(va, sa), (vb, sb)],
        "cases": [
            {"name": "both layers, T=10", "thresholds": [10, 10], "enabled": [True, True],
             "verdicts": [int(v) for v in wire.combine_planes([oa, ob])]},
            {"name": "layer A only, T=10", "thresholds": [10, 10], "enabled": [True, False],
             "verdicts": [int(v) for v in wire.combine_planes([oa])]},
            {"name": "no criteria includes everything", "thresholds": [10, 10],
             "enabled": [False, False], "verdicts": [0, 0]},
        ]})

    # ---------------------------------------------------------------- the codes no surface holds
    # `Surface.validate` cannot express these beside per-cell reasons -- a layer-wide reason must
    # cover every cell, and OUTSIDE and UNKNOWN_CAUSE arise at export and at a v1 lift, not in a
    # built surface. The real-layer window below contains none of them either. So they are built
    # as planes directly, which is the only way the JavaScript decoder ever sees them tested.
    codes = np.array([wire.OK, wire.OUTSIDE, wire.UNKNOWN_CAUSE, wire.LAYER_UNKNOWN,
                      wire.OFF_NETWORK], dtype=np.uint8)
    vals = np.array([5, wire.VALUE_NONE, wire.VALUE_NONE, wire.VALUE_NONE, 40], dtype=np.uint8)
    (OUT / "codes.value.bin").write_bytes(vals.tobytes())
    (OUT / "codes.status.bin").write_bytes(codes.tobytes())
    code_cases = []
    for t in (1, 5, 10, 40, 41):
        o = wire.outcome_planes(vals, codes, threshold_min=t, horizon_s=7200.0)
        code_cases.append({"name": f"codes T={t}", "thresholds": [t], "enabled": [True],
                           "verdicts": [int(v) for v in wire.combine_planes([o])]})
    groups.append({"name": "every status code, including those no Surface can hold",
                   "nrows": 1, "ncols": len(codes),
                   "layers": [{"id": "codes", "horizon_s": 7200.0,
                               "value_file": "codes.value.bin",
                               "status_file": "codes.status.bin"}],
                   "planes": [(vals, codes)], "cases": code_cases,
                   "status_codes_present": sorted(int(c) for c in np.unique(codes))})

    # ---------------------------------------------------------------- the real window
    surf, origin = real_window()
    entry, value, status = layer_entry("real", surf)
    cases = []
    for t in THRESHOLDS:
        expected = evaluate(
            Criterion(label=f"g{t}", mode="walk", target="grocery", kind="category",
                      threshold_s=float(t) * 60.0), surf)
        from_wire = wire.outcome_planes(value, status, threshold_min=t,
                                        horizon_s=surf.horizon_s)
        assert np.array_equal(expected, from_wire), f"python disagrees with itself at T={t}"
        verdict = wire.combine_planes([from_wire])
        counts = [int((verdict == v).sum()) for v in (0, 1, 2)]
        cases.append({"name": f"real window T={t}", "thresholds": [t], "enabled": [True],
                      "counts": {"included": counts[0], "excluded": counts[1],
                                 "unknown": counts[2]},
                      "verdict_sha256_32": digest(verdict)})
    groups.append({"name": f"published layer window at {origin}", "nrows": WINDOW,
                   "ncols": WINDOW, "layers": [entry], "planes": [(value, status)],
                   "cases": cases,
                   "status_codes_present": sorted(int(c) for c in np.unique(status))})

    out = {"encoding": wire.ENCODING,
           "generated_by": "v2/scripts/make_wire_vectors.py",
           "why": ("a Python round trip cannot protect the browser; these are replayed through "
                   "the real worker by worker_conformance.mjs"),
           "status_codes": {str(k): v for k, v in wire.STATUS_CODES.items()},
           "groups": []}
    for g in groups:
        for (value, status), entry in zip(g["planes"], g["layers"]):
            (OUT / entry["value_file"]).write_bytes(np.ascontiguousarray(value).tobytes())
            (OUT / entry["status_file"]).write_bytes(np.ascontiguousarray(status).tobytes())
        out["groups"].append({k: v for k, v in g.items() if k != "planes"})
    (OUT / "vectors.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"wrote {OUT / 'vectors.json'} and {sum(len(g['layers']) * 2 for g in groups)} planes")
    for g in groups:
        print(f"  {g['name']}: {g['nrows']}x{g['ncols']}, {len(g['cases'])} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
