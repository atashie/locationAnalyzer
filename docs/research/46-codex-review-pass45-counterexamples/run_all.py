"""Codex pass 45's reproducers, re-run from our own checkout.

    v2/.venv/Scripts/python.exe -B docs/research/46-codex-review-pass45-counterexamples/run_all.py

The cheap checks run without a graph. The routed figures live in
`docs/experiments/s3-7-destination-truth.json`, written by
`v2/scripts/audit_destination_truth.py`, and are read back here rather than recomputed.
"""
from __future__ import annotations

import json
import pathlib
import sys

import geopandas as gpd
import numpy as np
from scipy.sparse import csr_matrix

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "v2"))
sys.path.insert(0, str(ROOT / "v2" / "spikes"))
sys.path.insert(0, str(ROOT / "v2" / "scripts"))

import audit_destination_truth as a                             # noqa: E402
from locfinder.places.categories import select_overture         # noqa: E402
from locfinder.traveltime.arrival import arrival_seconds_two_weight  # noqa: E402


def f3_adding_a_destination_can_lengthen_the_reported_time() -> dict:
    """HIGH, and the one that matters most: the audit asserted a monotonicity that is false
    because the search minimises COST and reports TIME."""
    cost = csr_matrix(([700.0, 650.0], ([0, 0], [1, 2])), shape=(3, 3))
    time = csr_matrix(([500.0, 650.0], ([0, 0], [1, 2])), shape=(3, 3))
    one = float(arrival_seconds_two_weight(cost, time, dest_idx=[1])[0])
    two = float(arrival_seconds_two_weight(cost, time, dest_idx=[1, 2])[0])
    return {"one_destination_seconds": one, "two_destinations_seconds": two,
            "adding_a_destination_made_it_slower": two > one,
            "a_ten_minute_verdict_flips": one <= 600 < two}


def f2_the_matcher_no_longer_admits_nonstores() -> dict:
    """HIGH. Garib-ALDI-, TARGET PharmaSolutions and Harris Teeter Fuel Center were all counted."""
    cases = [("Mariachi Garibaldi NC", "Aldi", False), ("ALDI #123", "Aldi", True),
             ("Las Carolinas Fresh Market", "Fresh Market", True)]
    out = {"brand_hit": {f"{n} vs {b}": a.brand_hit(n, b) == want
                         for n, b, want in cases}}
    out["is_the_store"] = {n: a.is_the_store(n) for n in
                           ("Harris Teeter Fuel Center", "TARGET PharmaSolutions",
                            "Weaver Street Market Administration", "Harris Teeter")}
    out["all_as_expected"] = (all(out["brand_hit"].values())
                              and not any(out["is_the_store"][k] for k in
                                           ("Harris Teeter Fuel Center", "TARGET PharmaSolutions",
                                            "Weaver Street Market Administration"))
                              and out["is_the_store"]["Harris Teeter"])
    return out


def f1_the_flagged_records_have_corroboration_against_them() -> dict:
    """HIGH. Four of the nine sit within 150 m of an OPEN destination already in our list, and the
    flag provenance is recorded per property."""
    grid = a.METRO.grid()
    ov = gpd.read_parquet(a.METRO_DIR / "overture_places_accepted.parquet").to_crs(grid.crs)
    g = select_overture(ov, "grocery")
    status = np.array([str(s) for s in g["operating_status"]])
    closed, others = g[status == "permanently_closed"], g[status != "permanently_closed"]
    ocent = others.geometry.centroid
    onames = [a.overture_name(n) for n in others["names"]]
    rows, datasets = [], {}
    for r in closed.itertuples():
        d = ocent.distance(r.geometry.centroid).to_numpy()
        j = int(d.argmin())
        src = []
        try:
            src = [s.get("dataset") for s in r.sources
                   if s.get("property") == "/properties/operating_status"]
        except TypeError:
            pass
        for s in src:
            datasets[str(s)] = datasets.get(str(s), 0) + 1
        rows.append({"name": a.overture_name(r.names), "nearest_open_of_ours": onames[j],
                     "metres": round(float(d[j]), 1), "flag_source": src})
    return {"records": rows, "flag_provenance": datasets,
            "within_150m_of_an_open_destination": sum(1 for r in rows if r["metres"] < 150)}


def routed_figures_from_the_artifact() -> dict:
    """F1, F3 and F4's numbers, as the audit now records them: both directions, both units."""
    path = ROOT / "docs" / "experiments" / "s3-7-destination-truth.json"
    if not path.exists():
        return {"note": "run v2/scripts/audit_destination_truth.py"}
    d = json.loads(path.read_text(encoding="utf-8"))
    imp = d["impact"]
    return {"destination_nodes": imp["destination_nodes"],
            "nodes_changed": imp["nodes_changed_against_published"],
            "at_ten_minutes": imp["thresholds"]["10"],
            "brand_rows_added": d["brand_coverage"][
                "store_rows_a_brand_definition_would_add"]}


def main() -> int:
    out = {}
    for fn in (f3_adding_a_destination_can_lengthen_the_reported_time,
               f2_the_matcher_no_longer_admits_nonstores,
               f1_the_flagged_records_have_corroboration_against_them,
               routed_figures_from_the_artifact):
        print(f"--- {fn.__name__}")
        out[fn.__name__] = fn()
        print(json.dumps(out[fn.__name__], indent=2, default=str))
    (pathlib.Path(__file__).parent / "results.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
