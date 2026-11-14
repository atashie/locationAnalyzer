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
                              Reason, Surface, Verdict, evaluate)

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


def layer_entry(name: str, surf: Surface, flagged=None, destinations=None, dest_table=None):
    """`(manifest entry, value, status, flag or None, dest or None)`.

    A layer carries an optional plane only when one is supplied, and the entry declares its file
    only then -- because an absent plane means "this layer does not say", which a decoder has to
    keep distinct from a plane of sentinels.
    """
    value, status = wire.encode_planes(surf)
    entry = {"id": name, "horizon_s": surf.horizon_s,
             "value_file": f"{name}.value.bin", "status_file": f"{name}.status.bin"}
    flag = None
    if flagged is not None:
        flag = wire.encode_route_flag(flagged, status)
        entry["flag_file"] = f"{name}.flag.bin"
    dest = None
    if destinations is not None:
        dest = wire.encode_selected_destination(destinations, status)
        entry["dest_file"] = f"{name}.dest.bin"
        entry["dest_table"] = f"{name}.destinations.json"
        entry["dest_byte_order"] = wire.DEST_BYTE_ORDER
        entry["dest_none"] = int(wire.DEST_NONE)
        if dest_table is None:
            raise ValueError(f"{name} ships destination ordinals and no side table")
    return entry, value, status, flag, dest


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    groups = []

    # ---------------------------------------------------------------- hand-built, one layer
    surf = hand_built()
    # Flag the first OK cell, so the group exercises a disclosure alongside every status code.
    hand_flags = np.zeros(len(surf.seconds), dtype=bool)
    hand_flags[0] = True
    entry, value, status, flag, _dest = layer_entry("hand", surf, flagged=hand_flags)
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
                   "layers": [entry], "planes": [(value, status, flag, None)], "cases": cases,
                   "expect_discloses_routes": True})

    # ---------------------------------------------------------------- two layers
    # Layer A is unknown on the cell where layer B is a known failure. The combined verdict must be
    # EXCLUDED. The old worker broke out of its loop at A and reported unknown.
    a = surface_from([np.inf, 300.0], [Reason.OFF_NETWORK, Reason.OK], [60.0, 300.0])
    b = surface_from([1800.0, np.inf], [Reason.OK, Reason.OFF_NETWORK], [1800.0, 60.0])
    ea, va, sa, _fa, _da = layer_entry("twoA", a)
    eb, vb, sb, _fb, _db = layer_entry("twoB", b)
    oa = wire.outcome_planes(va, sa, threshold_min=10, horizon_s=a.horizon_s)
    ob = wire.outcome_planes(vb, sb, threshold_min=10, horizon_s=b.horizon_s)
    groups.append({
        "name": "known failure beats unknown", "nrows": 1, "ncols": 2,
        "layers": [ea, eb], "planes": [(va, sa, None, None), (vb, sb, None, None)],
        "expect_discloses_routes": False,
        "cases": [
            {"name": "both layers, T=10", "thresholds": [10, 10], "enabled": [True, True],
             "verdicts": [int(v) for v in wire.combine_planes([oa, ob])]},
            {"name": "layer A only, T=10", "thresholds": [10, 10], "enabled": [True, False],
             "verdicts": [int(v) for v in wire.combine_planes([oa])]},
            {"name": "no criteria includes everything", "thresholds": [10, 10],
             "enabled": [False, False], "verdicts": [0, 0]},
        ]})

    # ------------------------------------------------- two layers that BOTH disclose
    # Pass 48: every disclosing fixture had one disclosing layer, so three real mutations passed
    # all fifty checks -- a flag read from layer 0 instead of layer k, a cell counted once per
    # flagged layer instead of once, and a flag used as an exclusion only when two layers are
    # enabled. Four cells, arranged so each of those moves a number:
    #
    #   cell 0  both layers flagged, both include   -> counted ONCE
    #   cell 1  only layer A flagged, both include  -> counted
    #   cell 2  only layer B flagged, both include  -> counted (a layer-0 index misses this)
    #   cell 3  layer A flagged, layer B EXCLUDES   -> not counted, the cell is not included
    da = surface_from([120.0, 120.0, 120.0, 120.0], [Reason.OK] * 4, [120.0] * 4)
    db = surface_from([180.0, 180.0, 180.0, 1800.0],
                      [Reason.OK, Reason.OK, Reason.OK, Reason.OK], [180.0, 180.0, 180.0, 1800.0])
    fa = np.array([True, True, False, True])
    fb = np.array([True, False, True, False])
    eda, vda, sda, flda, _xa = layer_entry("discA", da, flagged=fa)
    edb, vdb, sdb, fldb, _xb = layer_entry("discB", db, flagged=fb)
    oda = wire.outcome_planes(vda, sda, threshold_min=10, horizon_s=da.horizon_s)
    odb = wire.outcome_planes(vdb, sdb, threshold_min=10, horizon_s=db.horizon_s)
    both = wire.combine_planes([oda, odb])
    # The disclosure over both enabled layers: a cell counts once if ANY enabled disclosing layer
    # flags it AND the combined verdict includes it.
    inc_both = np.asarray(both) == int(Verdict.INCLUDED)
    disc_both = int((inc_both & (fa | fb)).sum())
    a_only = wire.combine_planes([oda])
    disc_a_only = int(((np.asarray(a_only) == int(Verdict.INCLUDED)) & fa).sum())
    groups.append({
        "name": "two layers that both disclose", "nrows": 1, "ncols": 4,
        "layers": [eda, edb], "planes": [(vda, sda, flda, None), (vdb, sdb, fldb, None)],
        "expect_discloses_routes": True,
        "cases": [
            {"name": "both disclosing layers, T=10", "thresholds": [10, 10],
             "enabled": [True, True], "restricted_included": disc_both,
             "verdicts": [int(v) for v in both]},
            {"name": "layer A only, T=10", "thresholds": [10, 10], "enabled": [True, False],
             "restricted_included": disc_a_only,
             "verdicts": [int(v) for v in a_only]},
        ]})

    # ------------------------------------- one layer discloses and the other does not
    # The ordinary shape the moment a household states a second criterion, and the one that
    # crashed the worker: the app sends a null slot for the plain layer and `plane()` read
    # `null.byteLength`. A null slot is legal exactly where the manifest declares no plane.
    ma = surface_from([120.0, 120.0], [Reason.OK, Reason.OK], [120.0, 120.0])
    mb = surface_from([240.0, 240.0], [Reason.OK, Reason.OK], [240.0, 240.0])
    ema, vma, sma, flma, _xc = layer_entry(
        "mixedDiscloses", ma, flagged=np.array([True, False]))
    emb, vmb, smb, _flmb, _xd = layer_entry("mixedSilent", mb)
    oma = wire.outcome_planes(vma, sma, threshold_min=10, horizon_s=ma.horizon_s)
    omb = wire.outcome_planes(vmb, smb, threshold_min=10, horizon_s=mb.horizon_s)
    mixed = wire.combine_planes([oma, omb])
    groups.append({
        "name": "one layer discloses and one does not", "nrows": 1, "ncols": 2,
        "layers": [ema, emb], "planes": [(vma, sma, flma, None), (vmb, smb, None, None)],
        "expect_discloses_routes": True,
        "cases": [
            {"name": "both layers, T=10", "thresholds": [10, 10], "enabled": [True, True],
             "restricted_included": 1, "verdicts": [int(v) for v in mixed]},
            # With only the SILENT layer enabled, nothing enabled discloses, so the count must be
            # null rather than 0 -- the bundle discloses and this selection does not.
            {"name": "only the silent layer, T=10", "thresholds": [10, 10],
             "enabled": [False, True], "restricted_included": None,
             "verdicts": [int(v) for v in wire.combine_planes([omb])]},
        ]})

    # -------------------------------------------- two layers that BOTH name destinations
    # Two naming layers from the START. Pass 48's twenty-seventh instance was that every
    # disclosing fixture had ONE disclosing layer, so a flag read from layer 0 was correct by
    # accident and three real mutations passed all fifty checks.
    def table(n, prefix):
        return {"what_this_is": f"side table for {prefix}",
                "licence": {"this_table": ["CC0-1.0"], "source": "synthetic"},
                "destinations": [
                    {"ordinal": i, "node_index": 1000 + i, "place_count": 1 + (i % 2),
                     "places": ([{"gers_id": f"{prefix}-{i}-a", "name": f"{prefix} Shop {i}",
                                  "brand": None, "category": "grocery",
                                  "operating_status": "open", "licence": "CC0-1.0"}]
                                + ([{"gers_id": f"{prefix}-{i}-b", "name": f"{prefix} Annex {i}",
                                     "brand": None, "category": "grocery",
                                     "operating_status": "open", "licence": "CC0-1.0"}]
                                   if i % 2 else []))}
                    for i in range(n)],
                }

    na = surface_from([120.0, 120.0, 120.0, 120.0], [Reason.OK] * 4, [120.0] * 4)
    # Layer B is OFF_NETWORK at the last cell where layer A has an answer. That is what
    # makes the per-layer indexing inside the init invariant loop load-bearing: a plane read
    # from layer 0 names a destination there, where B publishes no journey at all.
    nb = surface_from([180.0, 180.0, 180.0, np.inf],
                      [Reason.OK, Reason.OK, Reason.OK, Reason.OFF_NETWORK],
                      [180.0, 180.0, 180.0, 60.0])
    ta, tb = table(4, "A"), table(4, "B")
    # Different ordinals per layer at the same cell, so a plane read from layer 0 names the
    # wrong shop rather than coincidentally the right one.
    ena, vna, sna, _f, dna = layer_entry("destA", na, destinations=np.array([0, 1, 2, 3]),
                                         dest_table=ta)
    enb, vnb, snb, _g, dnb = layer_entry(
        "destB", nb, destinations=np.array([3, 2, 1, wire.DEST_NONE]), dest_table=tb)
    ona = wire.outcome_planes(vna, sna, threshold_min=10, horizon_s=na.horizon_s)
    onb = wire.outcome_planes(vnb, snb, threshold_min=10, horizon_s=nb.horizon_s)
    both_v = wire.combine_planes([ona, onb])
    groups.append({
        "name": "two layers that both name destinations", "nrows": 1, "ncols": 4,
        "layers": [ena, enb], "planes": [(vna, sna, None, dna), (vnb, snb, None, dnb)],
        "dest_tables": [ta, tb], "expect_names_destinations": True,
        "cases": [
            {"name": "both naming layers, T=10", "thresholds": [10, 10], "enabled": [True, True],
             "verdicts": [int(v) for v in both_v],
             # Cell 0 is included in both layers, so BOTH name a destination and the card is owed
             # both -- one per criterion, not one for the household.
             "destination_at": [
                 {"row": 0, "col": 0, "included": True,
                  "names": [{"layer": "destA", "ordinal": 0, "place_count": 1,
                             "first_place_name": "A Shop 0"},
                            {"layer": "destB", "ordinal": 3, "place_count": 2,
                             "first_place_name": "B Shop 3"}]},
                 # Cell 3: layer B excludes it, so the combined verdict excludes it and no
                 # destination is applicable at all.
                 {"row": 0, "col": 3, "included": False, "names": None},
             ]},
            {"name": "layer A only, T=10", "thresholds": [10, 10], "enabled": [True, False],
             "verdicts": [int(v) for v in wire.combine_planes([ona])],
             "destination_at": [
                 {"row": 0, "col": 3, "included": True,
                  "names": [{"layer": "destA", "ordinal": 3, "place_count": 2,
                             "first_place_name": "A Shop 3"}]},
             ]},
        ]})

    # ------------------------------- one layer names a destination and the other does not
    sa = surface_from([120.0, 120.0], [Reason.OK, Reason.OK], [120.0, 120.0])
    sb = surface_from([240.0, 240.0], [Reason.OK, Reason.OK], [240.0, 240.0])
    tn = table(2, "N")
    ema, vma, sma, _h, dma = layer_entry("namesDest", sa, destinations=np.array([1, 0]),
                                         dest_table=tn)
    emb, vmb, smb, _i, _j = layer_entry("silentDest", sb)
    oma = wire.outcome_planes(vma, sma, threshold_min=10, horizon_s=sa.horizon_s)
    omb = wire.outcome_planes(vmb, smb, threshold_min=10, horizon_s=sb.horizon_s)
    groups.append({
        "name": "one layer names a destination and one does not", "nrows": 1, "ncols": 2,
        "layers": [ema, emb], "planes": [(vma, sma, None, dma), (vmb, smb, None, None)],
        "dest_tables": [tn, None], "expect_names_destinations": True,
        "cases": [
            {"name": "both layers, T=10", "thresholds": [10, 10], "enabled": [True, True],
             "verdicts": [int(v) for v in wire.combine_planes([oma, omb])],
             "destination_at": [
                 {"row": 0, "col": 0, "included": True,
                  "names": [{"layer": "namesDest", "ordinal": 1, "place_count": 2,
                             "first_place_name": "N Shop 1"}]}]},
            # With only the SILENT layer enabled nothing names anything, so the answer is null
            # rather than an empty list: "this bundle does not say" is not "there is none".
            {"name": "only the silent layer, T=10", "thresholds": [10, 10],
             "enabled": [False, True],
             "verdicts": [int(v) for v in wire.combine_planes([omb])],
             "destination_at": [{"row": 0, "col": 0, "included": True, "names": None}]},
        ]})

    # ------------------------------------------------------- ordinals that survive a byte swap
    # The destination plane is the only uint16 plane, so it is the only one with a byte order, and
    # its failure mode is a VALID wrong answer. With small ordinals a swap lands out of range and
    # the bounds check catches it -- which hides the real hazard. 1 and 256 swap into each other,
    # both in range for a 300-entry table, so nothing but the NAME can notice.
    bs = surface_from([120.0, 120.0], [Reason.OK, Reason.OK], [120.0, 120.0])
    tbs = table(300, "S")
    ebs, vbs, sbs, _k, dbs = layer_entry("byteSwap", bs, destinations=np.array([1, 256]),
                                         dest_table=tbs)
    obs = wire.outcome_planes(vbs, sbs, threshold_min=10, horizon_s=bs.horizon_s)
    groups.append({
        "name": "destination ordinals that survive a byte swap", "nrows": 1, "ncols": 2,
        "layers": [ebs], "planes": [(vbs, sbs, None, dbs)], "dest_tables": [tbs],
        "expect_names_destinations": True,
        "why_this_group_exists": (
            "ordinals 1 and 256 are byte-swaps of each other and both index a real destination in "
            "a 300-entry table, so a big-endian read passes every structural check and returns "
            "the wrong shop. Only comparing the name catches it"),
        "cases": [
            {"name": "byte-swap survivors, T=10", "thresholds": [10], "enabled": [True],
             "verdicts": [int(v) for v in wire.combine_planes([obs])],
             "destination_at": [
                 {"row": 0, "col": 0, "included": True,
                  "names": [{"layer": "byteSwap", "ordinal": 1, "place_count": 2,
                             "first_place_name": "S Shop 1"}]},
                 {"row": 0, "col": 1, "included": True,
                  "names": [{"layer": "byteSwap", "ordinal": 256, "place_count": 1,
                             "first_place_name": "S Shop 256"}]},
             ]},
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
                   "planes": [(vals, codes, None, None)], "cases": code_cases,
                   "expect_discloses_routes": False,
                   "status_codes_present": sorted(int(c) for c in np.unique(codes))})

    # ---------------------------------------------------------------- the real window
    surf, origin = real_window()
    # A deterministic sixth of the OK cells flagged: enough to make the count meaningful, and
    # shaped so an off-by-one in the loop would move it.
    ok = np.asarray(surf.reason) == int(Reason.OK)
    idxs = np.flatnonzero(ok.ravel())
    real_flags = np.zeros(ok.size, dtype=bool)
    real_flags[idxs[::6]] = True
    real_flags = real_flags.reshape(ok.shape)
    entry, value, status, flag, _dreal = layer_entry("real", surf, flagged=real_flags)
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
        disclosed = wire.disclosed_restricted(flag, from_wire)
        cases.append({"name": f"real window T={t}", "thresholds": [t], "enabled": [True],
                      "counts": {"included": counts[0], "excluded": counts[1],
                                 "unknown": counts[2]},
                      "restricted_included": int(disclosed.sum()),
                      "verdict_sha256_32": digest(verdict)})
        # The plane must not move a verdict. Same planes, same thresholds, flags withheld: the
        # verdict digest has to be identical, and the harness checks both cases against it.
        cases.append({"name": f"real window T={t}, flags withheld", "thresholds": [t],
                      "enabled": [True], "withhold_flags": True,
                      "counts": {"included": counts[0], "excluded": counts[1],
                                 "unknown": counts[2]},
                      "restricted_included": None,
                      "verdict_sha256_32": digest(verdict)})
    groups.append({"name": f"published layer window at {origin}", "nrows": WINDOW,
                   "ncols": WINDOW, "layers": [entry], "planes": [(value, status, flag, None)],
                   "cases": cases, "expect_discloses_routes": True,
                   "status_codes_present": sorted(int(c) for c in np.unique(status))})

    out = {"encoding": wire.ENCODING,
           "route_flag_codes": {str(k): v for k, v in wire.ROUTE_FLAG_CODES.items()},
           "dest_none": int(wire.DEST_NONE),
           "destination_plane_byte_order": wire.DEST_BYTE_ORDER,
           "generated_by": "v2/scripts/make_wire_vectors.py",
           "why": ("a Python round trip cannot protect the browser; these are replayed through "
                   "the real worker by worker_conformance.mjs"),
           "status_codes": {str(k): v for k, v in wire.STATUS_CODES.items()},
           "groups": []}
    for g in groups:
        for (value, status, flag, dest), entry in zip(g["planes"], g["layers"]):
            (OUT / entry["value_file"]).write_bytes(np.ascontiguousarray(value).tobytes())
            (OUT / entry["status_file"]).write_bytes(np.ascontiguousarray(status).tobytes())
            if flag is not None:
                (OUT / entry["flag_file"]).write_bytes(np.ascontiguousarray(flag).tobytes())
            if dest is not None:
                (OUT / entry["dest_file"]).write_bytes(wire.destination_plane_bytes(dest))
                tables = g.get("dest_tables") or []
                i = g["layers"].index(entry)
                (OUT / entry["dest_table"]).write_text(
                    json.dumps(tables[i], indent=2), encoding="utf-8")
        out["groups"].append({k: v for k, v in g.items() if k != "planes"})
    (OUT / "vectors.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"wrote {OUT / 'vectors.json'} and {sum(len(g['layers']) * 2 for g in groups)} planes")
    for g in groups:
        print(f"  {g['name']}: {g['nrows']}x{g['ncols']}, {len(g['cases'])} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
