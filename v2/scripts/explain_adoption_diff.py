"""Why did convention C retain a different candidate under exact arithmetic?

The T0 adoption census (step 4 plan task 5) found that design revision 13's primitives change no
candidate set under conventions A or D over 844,685 points, and change `C_exact` on exactly **2**
of the 512,633 structure centroids. Both kept two candidates either way, so the count did not move
and the *places* did. This prints the per-segment positions behind one such point under both
arithmetics, so the mechanism is read off the numbers rather than inferred from the rule.

    python scripts/explain_adoption_diff.py                      # both points from the census
    python scripts/explain_adoption_diff.py --x 699485.6282859619 --y 3963460.7648411603

Takes about two minutes, almost all of it preparing the graph.
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The two structure centroids the census reported, from the artifact's `adoption` examples.
CENSUS_POINTS = (
    (699485.6282859619, 3963460.7648411603, 280349),
    (665635.9142146338, 3983718.636862272, 461149),
)


def load_pilot():
    """Import the pilot as a module, so this cannot drift from the code that measured."""
    sys.path.insert(0, str(ROOT / "spikes"))
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("t0_pilot", ROOT / "scripts"
                                                  / "t0_attachment_pilot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def describe(t0, geoms, tree, px: float, py: float, label: str) -> None:
    print(f"\n{'=' * 100}\n{label}: ({px!r}, {py!r})\n{'=' * 100}")
    both = {}
    for arithmetic in ("float", "exact"):
        m = t0.measure_point(geoms, tree, px, py, t0.MAX_ACCESS_M, arithmetic=arithmetic)
        both[arithmetic] = m
        kept = m["_sets"]["C"]
        print(f"\n-- {arithmetic}: window {m['window_records']} records, {m['n_raw']} raw "
              f"positions, computed minimum {m['global_min_m']!r}")
        print(f"   convention C retained {len(kept)}:")
        for p in kept:
            print(f"     record {p.record} seg {p.seg} occurrence {p.occurrence[:3]} "
                  f"residual {p.residual!r} at ({p.x!r}, {p.y!r})")

    # The per-record minimum is what C filters on, so that is where the disagreement has to be.
    print("\n-- the record whose minimum moved, position by position")
    f_raw, x_raw = both["float"]["_raw"], both["exact"]["_raw"]
    f_kept = {p.occurrence[:3] for p in both["float"]["_sets"]["C"]}
    x_kept = {p.occurrence[:3] for p in both["exact"]["_sets"]["C"]}
    moved = {k[0] for k in (f_kept ^ x_kept)}
    for record in sorted(moved):
        fs = [p for p in f_raw if p.record == record]
        xs = [p for p in x_raw if p.record == record]
        f_min, x_min = min(p.residual for p in fs), min(p.residual for p in xs)
        print(f"\n   record {record}: float minimum {f_min!r}, exact minimum {x_min!r}")
        for pf, px_ in zip(fs, xs):
            flag_f = " <- float min" if pf.residual == f_min else ""
            flag_x = " <- exact min" if px_.residual == x_min else ""
            print(f"     seg {pf.seg}: float {pf.residual!r}{flag_f}")
            print(f"              exact {px_.residual!r}{flag_x}")
            if pf.residual != px_.residual:
                gap = Fraction(pf.residual) - Fraction(px_.residual)
                print(f"              the two differ by {float(gap):.6e} m")
    if not moved:
        print("   none: this point's C sets agree, so it is not one of the two")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--x", type=float, default=None)
    ap.add_argument("--y", type=float, default=None)
    args = ap.parse_args(argv)

    t0 = load_pilot()
    print("preparing the graph (about 100 s) ...", flush=True)
    # The pilot prepares its graph inline in `main`, so these six lines are a second copy of it.
    # Extracting a shared function would be the better fix and would need the 50-minute census
    # re-run to show it behaviour preserving, so instead the copy is guarded: the design record
    # count it produces must equal the one the artifact was measured with, or this exits. A silent
    # drift between the two copies is the failure that guard exists for.
    G = t0.load_roads_graph()
    G = t0.ox.project_graph(G, to_crs=t0.GRID.crs)
    G = t0.add_travel_times(G, mode="walk")
    G = t0.symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, _comp = t0.largest_component(G)
    index = {n: i for i, n in enumerate(G.nodes())}
    records = t0.Records(G, index, kind="design")
    geoms, tree = records.geoms, records.tree

    import hashlib
    import json
    import shapely as _sh
    artifact = json.loads((ROOT.parent / "docs" / "experiments"
                           / "t0-attachment-pilot.json").read_text(encoding="utf-8"))

    # Codex pass 38 F6: the first version of this guard compared only the design record COUNT, and
    # two record sets can hold the artifact's 808,433 records with different geometry in the one
    # being queried -- the reproducer moved a measured residual from 1.0 m to 95.005 m without the
    # count changing. The guard is now a fingerprint over the records in their constructed order:
    # every coordinate of every geometry, plus the forward and reverse times. That binds the thing
    # the measurement actually reads.
    g = artifact["graph"]
    expected_count = g["design_records"]
    h = hashlib.sha256()
    for i, geom in enumerate(records.geoms):
        h.update(_sh.to_wkb(geom, flavor="iso"))
        h.update(repr((float(records.fwd_time[i]), float(records.rev_time[i]))).encode())
    fingerprint = h.hexdigest()
    print(f"ready: {len(records):,} design records, fingerprint {fingerprint[:16]}", flush=True)
    if len(records) != expected_count:
        raise SystemExit(f"this script prepared {len(records):,} design records and the artifact "
                         f"was measured with {expected_count:,}. The preparation here has drifted "
                         "from the pilot's, so nothing below would describe the measured run")
    recorded = g.get("design_records_fingerprint")
    if recorded is None:
        print("  NOTE: this artifact predates the record fingerprint, so only the count and the "
              "graph digest are checked. Re-run the pilot to record one.", flush=True)
    elif recorded != fingerprint:
        raise SystemExit(f"the record fingerprint is {fingerprint} and the artifact was measured "
                         f"with {recorded}. Same count, different records: exactly what the count "
                         "alone cannot detect.")
    else:
        print("  fingerprint matches the artifact", flush=True)

    if args.x is not None and args.y is not None:
        describe(t0, geoms, tree, args.x, args.y, "requested point")
    else:
        for px, py, idx in CENSUS_POINTS:
            describe(t0, geoms, tree, px, py, f"census structure index {idx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
