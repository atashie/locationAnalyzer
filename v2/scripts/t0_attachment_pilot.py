"""T0 — the attachment prevalence-and-impact pilot. Plan §0 step 3, stages 1 and 2.

Design §2.2's candidate universe is a **declared convention** adopted for simplicity after five
rounds of choosing it by argument. This measures how often the choice matters on the real Triangle
walk graph. The pre-registered budget and decision rule are in
`docs/experiments/t0-attachment-pilot.md`, committed **before** this ran.

The three conventions, differing only in the retention filter. Occurrence deduplication and the cap
run afterwards, identically, so a difference is attributable to the filter:

* **A** (current, design revision 10) — every per-segment minimum within `ATTACH_TIE_M` = 0.01 m of
  the **global** minimum, across all records.
* **C** (design revision 9, reverted) — per record, the positions whose **computed** residual equals
  that record's minimum computed residual, exactly; then the band across records. Implemented with
  float equality *deliberately*, because that is what revision 9 did and what pass 24 F1 showed
  discards genuine geometric ties. Measuring the rule that was reverted is the point.
* **D** — the **exact rational** global minimum, no band. "Exact minima globally" is what the plan
  calls it, so the minimum is taken in exact arithmetic rather than in binary64.

**B is not implemented.** Stage 2 instead computes exact rational squared distances over the local
segment sets, which separates a genuine geometric tie from a merely close computed residual. That is
a diagnostic, not an implementation of B, and nothing here may call it one.

**The enumeration is indexed and complete, not nearest-record-only.** A segment's distance is never
less than its parent record's, so every segment within `global_min + band` belongs to a record
within `global_min + band`: taking every record whose bounding box meets the disc of that radius and
then every segment of those records cannot miss a candidate. `STRtree.query_nearest` supplies the
global minimum and `STRtree.query` the window.

**A record is an edge record in the DESIGN's sense.** `snap.EdgeIndex` keys by
`(node pair, canonical geometry)` and keeps the cost-minimal parallel edge. That is right for
production — it is what the CSR does — but it collapses parallel records carrying *different
weights*, and design §2.4 fixes identity and grouping separately from ranking precisely so that
grouping cannot answer a ranking question. Codex pass 36 F4 measured the cost of conflating them:
11 multiple-candidate points on frozen frame B become **16** when the weight-variants are kept
apart, across 5,239 affected geometry groups.

So this attaches to `Records(kind="design")`, keyed by
`(node pair, canonical geometry, travel_time, cost)`. `symmetrise` copies the data dict exactly, so
a walk graph's forward/reverse pair carries identical weights and collapses into one bidirectional
record — as `toy.ToyEdge` models it — while a parallel edge with different weights is a second
record. The production count is reported beside it. **The first run of this pilot attached to the
production grouping, and its prevalence counts are superseded.**

Run from v2/:  uv run python scripts/t0_attachment_pilot.py [--subdivision-sample 100]
Writes docs/experiments/t0-attachment-pilot.json -- a TRACKED path, deliberately. Nothing
under v2/data/ travels with a clone, and the rendered figures in the write-up beside it have
to be reproducible from the artifact they were rendered from.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import platform
import sys
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmnx as ox
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spikes"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import (ACCEPTED_PLACES, GRID, METRO, METRO_DIR,  # noqa: E402
                     load_roads_graph, read_graph_cache_manifest, stamp)
from locfinder import profile  # noqa: E402
from locfinder.measure.frames import (file_digest, read_frame,  # noqa: E402
                                      structure_population)
from locfinder.measure.exact import (exact_position,  # noqa: E402
                                     exact_projection, exact_segment_sq,
                                     prefix_arclength, rational_sqrt,
                                     segment_lengths)
from locfinder.measure.toy import ATTACH_TIE_M, MIN_SEGMENT_M, _segment_nearest  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.speeds import (access_speed_mps, add_travel_times,  # noqa: E402
                                         symmetrise)

MAX_ACCESS_M = 200.0        # origin cap, design §2.2
POI_SNAP_MAX_M = 300.0      # destination cap, design §2.2
FRAMES = Path(__file__).resolve().parents[1] / "data" / "frames" / "development"
ARTIFACT = (Path(__file__).resolve().parents[2] / "docs" / "experiments"
            / "t0-attachment-pilot.json")
ACCEPTED_BUILDINGS = METRO_DIR / "overture_buildings_accepted.parquet"


# --------------------------------------------------------------------------- exact arithmetic
# `exact_segment_sq` is imported from `locfinder.measure.exact`, which phase 4a.1 built and design
# revision 13 made normative as section 2.4 item 7. This file carried its own copy of it until
# 2026-11-12. The copy clamped with `t < 0` / `t > 1` and the module clamps with `t <= 0` /
# `t >= 1`; at t exactly 0 or 1 both return the same Fraction, and the two were checked to agree on
# 10 named cases -- the pass-30 and pass-37 witnesses, a degenerate segment, both clamp boundaries,
# subnormal and 1e300 coordinates -- and 200,000 random segments across five coordinate scales,
# a quarter of them placed on the segment so the clamp decides. Exact rational arithmetic on both
# sides, so that is bit-exact agreement. **This replacement changes no measured quantity**, which is
# the point: the adoption of the module's other primitives is a separate, labelled change, because
# it CAN move them.
#
# What the module adds beyond the copy: 38 fixtures and a mutation harness. The copy had neither.

# --------------------------------------------------------------------------- the candidate sets
class Pos:
    """One per-segment minimum, before any retention filter."""

    __slots__ = ("record", "seg", "t", "residual", "arclength", "x", "y", "occurrence", "exact_sq")

    def __init__(self, record, seg, t, residual, arclength, x, y, occurrence):
        self.record, self.seg, self.t = record, seg, t
        self.residual, self.arclength = residual, arclength
        self.x, self.y, self.occurrence = x, y, occurrence
        self.exact_sq: Fraction | None = None


class Records:
    """The record set the pilot attaches to, with its own STRtree. See the module docstring.

    Exposes exactly what the measurement needs — `geoms`, `tree`, `fwd_time`, `rev_time` — so the
    two definitions are interchangeable and the difference between them is measured rather than
    assumed.
    """

    __slots__ = ("kind", "geoms", "tree", "fwd_time", "rev_time", "graph_edges")

    def __init__(self, G, index, *, kind: str) -> None:
        from locfinder.traveltime.snap import _canonical_geometry_key, _edge_geometry

        if kind not in ("design", "production"):
            raise ValueError(f"unknown record kind {kind!r}")
        geoms: list = []
        starts: list[int] = []
        fwd_t: list[float] = []
        rev_t: list[float] = []
        fwd_c: list[float] = []
        rev_c: list[float] = []
        seen: dict[tuple, int] = {}
        edges = 0
        for u, v, _k, data in G.edges(keys=True, data=True):
            edges += 1
            t = float(data["travel_time"])
            c = float(data.get("cost", t))
            geom = _edge_geometry(G, u, v, data)
            iu, iv = index[u], index[v]
            key = (min(iu, iv), max(iu, iv), _canonical_geometry_key(geom))
            if kind == "design":
                key = key + (t, c)
            if key not in seen:
                g0 = geom.coords[0]
                near_u = abs(g0[0] - G.nodes[u]["x"]) + abs(g0[1] - G.nodes[u]["y"]) < 1e-6
                starts.append(iu if near_u else iv)
                seen[key] = len(geoms)
                geoms.append(geom)
                fwd_t.append(math.inf)
                rev_t.append(math.inf)
                fwd_c.append(math.inf)
                rev_c.append(math.inf)
            i = seen[key]
            if iu == starts[i]:
                if c < fwd_c[i]:
                    fwd_c[i], fwd_t[i] = c, t
            elif c < rev_c[i]:
                rev_c[i], rev_t[i] = c, t
        arr = np.empty(len(geoms), dtype=object)
        arr[:] = geoms
        self.kind = kind
        self.geoms = arr
        self.tree = shapely.STRtree(geoms)
        self.fwd_time = np.asarray(fwd_t, dtype=np.float64)
        self.rev_time = np.asarray(rev_t, dtype=np.float64)
        self.graph_edges = edges

    def __len__(self) -> int:
        return len(self.geoms)


def _occurrence_key(r: int, seg: int, t) -> tuple:
    """§2.2's occurrence label. A parameter at an endpoint is the VERTEX, shared between segments."""
    if t == 0:
        return (r, "v", seg)
    if t == 1:
        return (r, "v", seg + 1)
    return (r, "s", seg, t)


def raw_positions(geoms, window, px, py, *, arithmetic: str = "float") -> list[Pos]:
    """Every segment's nearest position, over every record in the window.

    **`arithmetic="float"` is what this pilot published** (`docs/experiments/t0-attachment-pilot.md`,
    stages 1-2): `toy._segment_nearest` for the projection, `math.hypot` for a segment length, and
    the prefix accumulated with `run += seg_len`. It is kept exactly as it ran, because the figures
    in the write-up were measured with it.

    **`arithmetic="exact"` is design revision 13's §2.4 item 7**, via `locfinder.measure.exact`:
    an exact rational projection parameter with the clamp decided on the exact value, a position and
    squared distance that are exact rationals, a residual that is one correct rounding of the exact
    root, and a prefix arclength that is `fsum` over correctly-rounded lengths with the partial
    segment rounded once. The occurrence label is then taken from the EXACT parameter, which is what
    pass 30's two witnesses need: both are cases where the float parameter lands on an endpoint and
    the exact one does not.

    The two are not interchangeable and the difference is **measured, not assumed** — see
    `adoption_stats`. The float path's `t` is a float and the exact path's is a `Fraction`, so an
    interior occurrence label is a different object on the two sides even where it denotes the same
    position; comparisons across the two therefore use the coarse label and the positions, never the
    raw label.
    """
    if arithmetic not in ("float", "exact"):
        raise ValueError(f"unknown arithmetic {arithmetic!r}")
    out: list[Pos] = []
    for r in window:
        coords = shapely.get_coordinates(geoms[r])
        if arithmetic == "float":
            run = 0.0
            for seg, ((ax, ay), (bx, by)) in enumerate(itertools.pairwise(coords)):
                ax, ay, bx, by = float(ax), float(ay), float(bx), float(by)
                seg_len = math.hypot(bx - ax, by - ay)
                d, t = _segment_nearest(px, py, ax, ay, bx, by)
                out.append(Pos(r, seg, t, d, run + t * seg_len,
                               ax + t * (bx - ax), ay + t * (by - ay),
                               _occurrence_key(r, seg, t)))
                run += seg_len
            continue
        pts = [(float(x), float(y)) for x, y in coords]
        PX, PY = Fraction(px), Fraction(py)
        # Once per record, not once per segment: `prefix_arclength` is quadratic in the segment
        # count without this, and the cache is proved not to change an answer by
        # `test_prefix_arclength_is_unchanged_by_passing_the_lengths_in`.
        lens = segment_lengths(pts)
        for seg, ((ax, ay), (bx, by)) in enumerate(itertools.pairwise(pts)):
            t = exact_projection(px, py, ax, ay, bx, by)
            qx, qy = exact_position(ax, ay, bx, by, t)
            ex, ey = PX - qx, PY - qy
            sq = ex * ex + ey * ey
            p = Pos(r, seg, t, rational_sqrt(sq), prefix_arclength(pts, seg, t, lens),
                    float(qx), float(qy), _occurrence_key(r, seg, t))
            p.exact_sq = sq
            out.append(p)
    return out


def dedup_and_cap(kept: list[Pos], cap_m: float) -> list[Pos]:
    """Design §2.2 steps 3 and 4, shared by every convention and applied in this order.

    The representative of a merged occurrence is the smallest residual then the smallest arclength;
    the cap is applied per candidate, after the merge.
    """
    merged: dict[tuple, Pos] = {}
    for p in kept:
        cur = merged.get(p.occurrence)
        if cur is None or (p.residual, p.arclength) < (cur.residual, cur.arclength):
            merged[p.occurrence] = p
    ordered = sorted(merged.values(), key=lambda p: (p.record, p.arclength))
    return [p for p in ordered if p.residual <= cap_m]


def convention_a(raw: list[Pos], global_min: float) -> list[Pos]:
    return [p for p in raw if p.residual <= global_min + ATTACH_TIE_M]


def convention_c(raw: list[Pos], global_min: float) -> list[Pos]:
    """Revision 9: exact equality on **computed** residuals, per record, then the band."""
    by_record: dict[int, list[Pos]] = {}
    for p in raw:
        by_record.setdefault(p.record, []).append(p)
    kept: list[Pos] = []
    for positions in by_record.values():
        best = min(p.residual for p in positions)
        if best <= global_min + ATTACH_TIE_M:
            kept.extend(p for p in positions if p.residual == best)
    return kept


def convention_d(raw: list[Pos]) -> list[Pos]:
    """Exact rational global minimum, no band. `exact_sq` must already be filled in."""
    best = min(p.exact_sq for p in raw)
    return [p for p in raw if p.exact_sq == best]


def signature(cands: list[Pos]) -> tuple:
    """Identity of a candidate set for comparison: the occurrences retained, in order."""
    return tuple(p.occurrence for p in cands)


#: How close two positions must be to count as the same location. A micrometre is far below
#: anything physical and far above the ~2.3e-10 m spacing of binary64 at UTM magnitudes, so this
#: separates "re-expressed" from "moved" without being sensitive to which order the arithmetic ran.
POSITION_TOL_M = 1e-6


def positions_differ(before: list[Pos], after: list[Pos]) -> bool:
    """Whether two candidate sets occupy different LOCATIONS, not merely different descriptions.

    A record split un-merges a shared-vertex occurrence into two, which raises the count while both
    candidates stay at one place -- and a set of candidates at the same places minimises to the same
    journey under every objective. Deduplicating by position before comparing is what makes this a
    question about the answer rather than about the bookkeeping.

    **Matching is spatial, not lexicographic (Codex pass 36 F7).** The first version sorted both
    sets by `(x, y)` and compared them pairwise, which breaks the correspondence under a coordinate
    perturbation smaller than the tolerance: `{(0,0), (0,10)}` against
    `{(-1e-7, 10), (1e-7, 0)}` sorts into crossed order and was reported as a change. Each position
    is now matched to its nearest unmatched counterpart, so a set is "the same places" exactly when
    a one-to-one correspondence within tolerance exists.

    **Where this UNDER-reports, stated rather than discovered later.** It compares locations, so it
    merges the two passes of a self-crossing road at one XY -- which design §2.2 insists are "one
    place and two decisions", because one leaves 500 m of road ahead and the other 100 m. Pass 36
    quantified it: removing one such occurrence is invisible here even where the remaining journey
    times differ by 666.667 s. A complete test compares each candidate's remaining-route options,
    which is routing and therefore stage 3.
    """
    def places(cands: list[Pos]) -> list[tuple[float, float]]:
        """Distinct locations. Pairwise against everything kept, not just the last one."""
        out: list[tuple[float, float]] = []
        for p in cands:
            if not any(math.hypot(p.x - qx, p.y - qy) <= POSITION_TOL_M for qx, qy in out):
                out.append((p.x, p.y))
        return out

    a, b = places(before), places(after)
    if len(a) != len(b):
        return True
    unmatched = list(b)
    for x1, y1 in a:
        best, best_d = None, None
        for j, (x2, y2) in enumerate(unmatched):
            d = math.hypot(x1 - x2, y1 - y2)
            if best_d is None or d < best_d:
                best, best_d = j, d
        if best is None or best_d > POSITION_TOL_M:
            return True
        unmatched.pop(best)
    return bool(unmatched)


class Accum:
    """Streaming aggregation, so a census need not hold a result per point.

    Every counter here is over **points** except the three named `..._candidates`, which are over
    candidates. The distinction is in the names on purpose: the first version of the exact block
    mixed a count of raw descriptions with a count of candidates and reported seven tied points on
    a set where no point had two candidates.
    """

    KEYS = ("A", "C", "D")

    def __init__(self) -> None:
        self.n = 0
        self.no_geometry = 0
        self.tree_disagrees = 0
        self.eligible = {k: 0 for k in self.KEYS}
        self.multi = {k: 0 for k in self.KEYS}
        self.multi_record = {k: 0 for k in self.KEYS}
        self.multi_occ_one_record = {k: 0 for k in self.KEYS}
        self.hist = {k: Counter() for k in self.KEYS}
        self.set_differs = {"A_vs_C": 0, "A_vs_D": 0}
        self.place_differs = {"A_vs_C": 0, "A_vs_D": 0}
        self.elig_differs = {"A_vs_C": 0, "A_vs_D": 0}
        self.c_drop_points = 0
        self.c_drop_candidates = 0
        self.c_drop_genuine_ties = 0
        self.c_drop_unique_minima = 0
        self.tie_points = 0
        self.distinct_tie_points = 0
        self.above_points = 0
        self.above_candidates = 0
        self.key_disagree_points = 0
        self.gmin: list[float] = []
        self.over_cap = 0
        self.window_max = 0
        self.window_sum = 0
        self.bounds = {pair: {"points_differing": 0, "same_record": 0,
                              "cross_record_unbounded": 0, "one_way_unbounded": 0,
                              "bounds_s": []}
                       for pair in ("A_vs_C", "A_vs_D")}

    def add(self, r: dict, eidx=None) -> None:
        self.n += 1
        if r.get("no_geometry"):
            self.no_geometry += 1
            return
        if eidx is not None:
            for pair, other in (("A_vs_C", "C"), ("A_vs_D", "D")):
                b = impact_bound(eidx, r["_sets"]["A"], r["_sets"][other])
                if b is None:
                    continue
                acc = self.bounds[pair]
                acc["points_differing"] += 1
                if b["scope"] == "same_record_bidirectional":
                    acc["same_record"] += 1
                    acc["bounds_s"].append(b["bound_s"])
                elif b["scope"] == "one_way":
                    acc["one_way_unbounded"] += 1
                else:
                    acc["cross_record_unbounded"] += 1
        self.tree_disagrees += bool(r.get("tree_disagrees"))
        for k in self.KEYS:
            self.eligible[k] += bool(r["eligible"][k])
            c = r["counts"][k]
            self.hist[k][c] += 1
            self.multi[k] += c > 1
            self.multi_record[k] += r["records"][k] > 1
            self.multi_occ_one_record[k] += r["max_occ_on_one_record"][k] > 1
        for pair, other in (("A_vs_C", "C"), ("A_vs_D", "D")):
            self.set_differs[pair] += not r["same_set"][pair]
            self.place_differs[pair] += not r["same_places"][pair]
            self.elig_differs[pair] += r["eligible"]["A"] != r["eligible"][other]
        self.c_drop_points += bool(r.get("c_drops", 0))
        self.c_drop_candidates += r.get("c_drops", 0)
        self.c_drop_genuine_ties += r.get("c_drops_a_genuine_exact_tie", 0)
        self.c_drop_unique_minima += r.get("c_drops_the_unique_exact_minimum", 0)
        self.tie_points += r.get("candidates_at_exact_min", 0) > 1
        self.distinct_tie_points += r.get("distinct_positions_at_exact_min", 0) > 1
        self.above_points += r.get("candidates_above_exact_min", 0) > 0
        self.above_candidates += r.get("candidates_above_exact_min", 0)
        self.key_disagree_points += r.get("occurrences_whose_descriptions_disagree_exactly", 0) > 0
        if r["global_min_m"] is not None:
            self.gmin.append(r["global_min_m"])
        self.window_max = max(self.window_max, r["window_records"])
        self.window_sum += r["window_records"]

    def summary(self, *, cap_m: float, meta: dict, seconds: float) -> dict:
        n = self.n
        agg: dict = dict(meta)
        agg["cap_m"] = cap_m
        agg["points"] = n
        agg["seconds"] = round(seconds, 2)
        agg["ms_per_point"] = round(1000.0 * seconds / max(n, 1), 4)
        agg["no_geometry"] = self.no_geometry
        agg["tree_and_recomputed_minimum_disagree"] = self.tree_disagrees
        for k in self.KEYS:
            agg[k] = {
                "eligible": self.eligible[k],
                "ineligible": n - self.eligible[k],
                "candidate_count_histogram": dict(sorted(self.hist[k].items())),
                "points_with_multiple_candidates": self.multi[k],
                "points_with_candidates_on_multiple_records": self.multi_record[k],
                "points_with_multiple_occurrences_on_one_record": self.multi_occ_one_record[k],
            }
        agg["A_vs_C_set_differs"] = self.set_differs["A_vs_C"]
        agg["A_vs_D_set_differs"] = self.set_differs["A_vs_D"]
        agg["A_vs_C_places_differ"] = self.place_differs["A_vs_C"]
        agg["A_vs_D_places_differ"] = self.place_differs["A_vs_D"]
        agg["A_vs_C_eligibility_differs"] = self.elig_differs["A_vs_C"]
        agg["A_vs_D_eligibility_differs"] = self.elig_differs["A_vs_D"]
        agg["exact"] = {
            "note": "point counts except the three named `..._candidates`",
            "points_where_C_drops_an_A_candidate": self.c_drop_points,
            "A_candidates_C_drops": self.c_drop_candidates,
            "A_candidates_C_drops_that_are_genuine_exact_ties": self.c_drop_genuine_ties,
            "A_candidates_C_drops_that_are_the_unique_exact_minimum": self.c_drop_unique_minima,
            "points_with_two_or_more_candidates_at_the_exact_minimum": self.tie_points,
            "points_with_two_or_more_DISTINCT_POSITIONS_at_the_exact_minimum":
                self.distinct_tie_points,
            "points_with_a_candidate_above_the_exact_minimum": self.above_points,
            "A_candidates_above_the_exact_minimum": self.above_candidates,
            "points_where_two_descriptions_of_one_occurrence_disagree_exactly":
                self.key_disagree_points,
        }
        if self.gmin:
            g = np.asarray(self.gmin)
            agg["nearest_distance_m"] = {
                "min": round(float(g.min()), 4), "median": round(float(np.median(g)), 4),
                "p90": round(float(np.percentile(g, 90)), 4), "max": round(float(g.max()), 4),
                "over_cap": int((g > cap_m).sum()),
            }
        agg["window_records"] = {"max": self.window_max,
                                 "mean": round(self.window_sum / max(n, 1), 4)}
        agg["impact_bound"] = {
            "bounds": "OBJECTIVE 1 only -- min over options of total travel time, which is the "
                      "objective E1 is defined against (design §2.1). Moving an attachment along "
                      "one record trades one endpoint's partial traversal against the other's by "
                      "|delta arc| / L * T, so the minimum moves by no more than that.",
            "does_not_bound": "OBJECTIVE 2, the time along the COST-minimising path: selection by "
                              "cost and reporting by time means a 0.013 s cost change can switch "
                              "the route and move the reported time by 120 s (Codex pass 36 F2). "
                              "Nor does it bound route AVAILABILITY, so one-way records are "
                              "excluded and counted.",
            "access_speed_mps": ACCESS_MPS,
        }
        for pair, acc in self.bounds.items():
            b = sorted(acc["bounds_s"])
            agg["impact_bound"][pair] = {
                "points_differing": acc["points_differing"],
                "same_record_bidirectional_bounded": acc["same_record"],
                "one_way_unbounded": acc["one_way_unbounded"],
                "cross_record_unbounded": acc["cross_record_unbounded"],
                "bound_s": ({"max": round(b[-1], 6), "median": round(b[len(b) // 2], 6),
                             "over_1s": sum(1 for x in b if x > 1.0),
                             "over_30s": sum(1 for x in b if x > 30.0),
                             "over_60s": sum(1 for x in b if x > 60.0)} if b else None),
            }
        return agg


# --------------------------------------------------------------------------- the labelled adoption
def coarse_occurrence(key: tuple) -> tuple:
    """An occurrence label with the interior parameter dropped.

    The float and exact paths describe the same interior position with different numbers — a float
    `0.3333333333333333` against a `Fraction(1, 3)` — so comparing raw labels across the two would
    report nearly every interior attachment as changed, which is noise. What is NOT noise is a
    position moving between a vertex and a segment interior, or onto a different segment: that is
    what pass 30's two witnesses do, and it is what this label keeps.
    """
    return key[:3]


def adoption_sentinel() -> list[dict]:
    """Prove the exact path is not quietly the float path, before any zero below is believed.

    Every figure `adoption_stats` reports is a **count of differences**, so an exact path that
    silently behaved like the float one would report a clean zero everywhere and read as good news.
    That is the failure mode pass 22 found in the invariant harness, and the fix there was the same:
    a sentinel that must fire.

    These are Codex pass 30's two witnesses, which exist because the float projection lands on an
    endpoint where the exact one does not. If either stops differing, the axis is broken and the run
    stops rather than publishing zeros.
    """
    cases = (
        ("W2 dot-product cancellation",
         [(0.0, 0.0), (1e-6, 1e-6)], (122.09, -122.08999999999999)),
        ("W3 subtraction near the coordinate bound",
         [(-1e7, 0.0), (1e7, 0.0)], (math.nextafter(1e7, 0.0), 0.0)),
    )
    checks: list[dict] = []
    for name, coords, (px, py) in cases:
        arr = np.empty(1, dtype=object)
        arr[:] = [shapely.LineString(coords)]
        f = raw_positions(arr, [0], px, py, arithmetic="float")[0]
        x = raw_positions(arr, [0], px, py, arithmetic="exact")[0]
        checks.append({
            "witness": name,
            "float_t": repr(f.t), "exact_t": str(x.t),
            "float_occurrence": str(f.occurrence[:3]), "exact_occurrence": str(x.occurrence[:3]),
            "float_lands_on_a_vertex": f.occurrence[1] == "v",
            "exact_lands_on_a_vertex": x.occurrence[1] == "v",
            "differs": f.occurrence[:3] != x.occurrence[:3],
        })
    if not all(c["differs"] for c in checks):
        raise SystemExit(
            "adoption sentinel FAILED: the exact path agrees with the float path on a witness "
            "built to separate them, so every zero it reports would be meaningless. "
            f"{checks}")
    return checks


def adoption_stats(geoms, tree, points, cap_m: float, *, want_exact: bool = True) -> dict:
    """Design revision 13's primitives against the arithmetic this pilot published.

    **Conventions A and D are the same rule measured two ways.** Neither is defined in terms of a
    computed value: A is "within `ATTACH_TIE_M` of the global minimum" and D is "the exact rational
    global minimum", so running them on better arithmetic implements the same declared rule.

    **Convention C is not.** Its rule is *equality of the COMPUTED residual*, chosen deliberately
    because that is what design revision 9 did and what pass 24 F1 showed discards genuine
    geometric ties. Exact arithmetic therefore produces a **different rule**, reported here as
    `C_exact` and never merged with `C`'s figures. It does not inherit this pilot's evidence.

    **An exact band PREDICATE is not implemented here, and would be convention B.** Deciding
    `sqrt(q) <= sqrt(q_min) + 0.01` exactly is possible over the rationals — squaring twice removes
    both roots — but convention B is a declared alternative in design §2.2 with its own evidence
    requirements, and smuggling it in as an arithmetic change would be exactly the mislabelling
    this phase exists to avoid. The exact path's residual is a correctly-rounded distance and the
    band is still a binary64 comparison of it.
    """
    #: internal convention key -> the name this comparison is reported under. `C` is renamed
    #: because exact arithmetic turns its rule into a different one.
    OUT = {"A": "A_exact_vs_A", "C": "C_exact_vs_C", "D": "D_exact_vs_D"}
    keys = ("A", "C", "D")
    agg = {
        "note": ("float is the arithmetic this pilot published; exact is design revision 13's "
                 "§2.4 item 7 primitives. A and D are one rule measured two ways; C under exact "
                 "arithmetic is a DIFFERENT rule, which is why it is named C_exact_vs_C"),
        "points": 0,
        "eligibility_changed": {v: 0 for v in OUT.values()},
        "count_changed": {v: 0 for v in OUT.values()},
        "occurrences_changed": {v: 0 for v in OUT.values()},
        "places_changed": {v: 0 for v in OUT.values()},
        "points_with_any_change": 0,
        # Did the arithmetic move a number at all? Without this, every zero above could mean the
        # exact path is a no-op on real geometry, and nothing would distinguish the two readings.
        "raw": {
            "positions_compared": 0,
            "residual_differs": 0,
            "arclength_differs": 0,
            "parameter_differs": 0,
            "vertex_or_interior_differs": 0,
            "max_abs_residual_diff_m": 0.0,
            "max_abs_arclength_diff_m": 0.0,
            "max_abs_parameter_diff": 0.0,
            # How far the attachment POSITION moved, in metres. The most interpretable figure here
            # and not derivable from the others: a parameter difference is dimensionless, and a
            # residual difference measures the distance to the point rather than the displacement
            # along the road, which a shift in the parameter changes by more.
            "position_differs": 0,
            "max_position_shift_m": 0.0,
        },
        "examples": [],
    }
    started = time.perf_counter()
    for i, (px, py) in enumerate(points):
        # A census here runs for about 25 minutes. The main loop reports every 100,000 points and
        # this one reported nothing, so the first census run looked indistinguishable from a hang.
        if i and i % 100_000 == 0:
            print(f"    adoption: {i:,} of {len(points):,} "
                  f"({time.perf_counter() - started:.0f}s)", flush=True)
        f = measure_point(geoms, tree, float(px), float(py), cap_m,
                          want_exact=want_exact, arithmetic="float")
        x = measure_point(geoms, tree, float(px), float(py), cap_m,
                          want_exact=want_exact, arithmetic="exact")
        if f.get("no_geometry") or x.get("no_geometry"):
            continue
        agg["points"] += 1
        fr, xr = f["_raw"], x["_raw"]
        if len(fr) != len(xr):
            raise SystemExit("the two arithmetics enumerated different numbers of raw positions "
                             f"at point {i}: {len(fr)} against {len(xr)}. They are given the same "
                             "window and the same segments, so this is a bug, not a measurement")
        r = agg["raw"]
        r["positions_compared"] += len(fr)
        for pf, pxx in zip(fr, xr):
            tf, tx = float(pf.t), float(pxx.t)
            if pf.residual != pxx.residual:
                r["residual_differs"] += 1
                r["max_abs_residual_diff_m"] = max(r["max_abs_residual_diff_m"],
                                                   abs(pf.residual - pxx.residual))
            if pf.arclength != pxx.arclength:
                r["arclength_differs"] += 1
                r["max_abs_arclength_diff_m"] = max(r["max_abs_arclength_diff_m"],
                                                    abs(pf.arclength - pxx.arclength))
            if tf != tx:
                r["parameter_differs"] += 1
                r["max_abs_parameter_diff"] = max(r["max_abs_parameter_diff"], abs(tf - tx))
            if (pf.x, pf.y) != (pxx.x, pxx.y):
                r["position_differs"] += 1
                r["max_position_shift_m"] = max(r["max_position_shift_m"],
                                                math.hypot(pf.x - pxx.x, pf.y - pxx.y))
            if (pf.occurrence[1], pf.occurrence[2]) != (pxx.occurrence[1], pxx.occurrence[2]):
                r["vertex_or_interior_differs"] += 1
        moved = False
        for k in keys:
            name = OUT[k]
            fs, xs = f["_sets"][k], x["_sets"][k]
            changed = []
            if bool(fs) != bool(xs):
                agg["eligibility_changed"][name] += 1
                changed.append("eligibility")
            if len(fs) != len(xs):
                agg["count_changed"][name] += 1
                changed.append("count")
            if ({coarse_occurrence(p.occurrence) for p in fs}
                    != {coarse_occurrence(p.occurrence) for p in xs}):
                agg["occurrences_changed"][name] += 1
                changed.append("occurrences")
            if positions_differ(fs, xs):
                agg["places_changed"][name] += 1
                changed.append("places")
            if changed:
                moved = True
                if len(agg["examples"]) < 25:
                    agg["examples"].append({
                        "point_index": i, "x": float(px), "y": float(py),
                        "comparison": name, "changed": changed,
                        "float_count": len(fs), "exact_count": len(xs),
                        "float_min_m": f["global_min_m"], "exact_min_m": x["global_min_m"],
                    })
        if moved:
            agg["points_with_any_change"] += 1
    return agg


# --------------------------------------------------------------------------- one point
def measure_point(geoms, tree, px, py, cap_m, *, want_exact: bool = True,
                  arithmetic: str = "float") -> dict:
    nearest = tree.query_nearest(shapely.points([px], [py])[0], return_distance=True,
                                 all_matches=True)
    idx, dist = nearest
    idx = np.atleast_1d(idx)
    if idx.size == 0:
        return {"eligible": {}, "global_min_m": None, "no_geometry": True}
    global_min = float(np.atleast_1d(dist)[0])
    # A hair of slack on the window radius. `STRtree` computes the record distance and this file
    # recomputes it from the segments, and the two need not agree to the last bit; without slack a
    # segment at exactly the band edge could fall outside a window sized from the other number.
    # Every filter below then uses the recomputed minimum, so the band itself is not widened.
    radius = global_min + ATTACH_TIE_M + 1e-6
    window = np.atleast_1d(tree.query(shapely.points([px], [py])[0].buffer(radius)))
    raw = raw_positions(geoms, window, px, py, arithmetic=arithmetic)
    computed_min = min(p.residual for p in raw)
    if want_exact and arithmetic == "float":
        # The exact path already filled `exact_sq` for every position, as a by-product of its own
        # projection. The float path fills it only inside the band, which is where convention D
        # needs it, and which is what keeps stage 2 affordable over an 843,000-point census.
        for p in raw:
            if p.residual <= computed_min + ATTACH_TIE_M:
                p.exact_sq = exact_segment_sq(px, py, *_seg_ends(geoms, p))

    a = dedup_and_cap(convention_a(raw, computed_min), cap_m)
    c = dedup_and_cap(convention_c(raw, computed_min), cap_m)
    banded = [p for p in raw if p.residual <= computed_min + ATTACH_TIE_M]
    d = dedup_and_cap(convention_d(banded), cap_m) if want_exact else []

    out = {
        "global_min_m": computed_min,
        "tree_min_m": global_min,
        "tree_disagrees": abs(global_min - computed_min) > 1e-9,
        "window_records": int(window.size),
        "n_raw": len(raw),
        "counts": {"A": len(a), "C": len(c), "D": len(d)},
        "records": {k: len({p.record for p in v}) for k, v in (("A", a), ("C", c), ("D", d))},
        "max_occ_on_one_record": {
            k: (max(Counter(p.record for p in v).values()) if v else 0)
            for k, v in (("A", a), ("C", c), ("D", d))},
        "eligible": {k: bool(v) for k, v in (("A", a), ("C", c), ("D", d))},
        "same_set": {"A_vs_C": signature(a) == signature(c),
                     "A_vs_D": signature(a) == signature(d)},
        "same_places": {"A_vs_C": not positions_differ(a, c),
                        "A_vs_D": not positions_differ(a, d)},
        "_sets": {"A": a, "C": c, "D": d},
        # The window this point was measured over, so a transformation check uses the SAME one on
        # both sides. The first version recomputed a narrower window without `measure_point`'s
        # numerical slack, and a record sitting at the computed band edge then vanished between the
        # baseline and the transformed set with the geometry unchanged -- two A candidates became
        # one before any transformation was applied (Codex pass 36 F6).
        "_window": window,
        # The per-segment positions before any retention filter, so the adoption check can
        # ask whether the arithmetic moved a NUMBER as well as whether it moved a decision.
        "_raw": raw,
    }
    if want_exact:
        exact_min = min(p.exact_sq for p in banded)
        # Every count below is over **deduplicated candidates**, never over raw per-segment
        # descriptions. One occurrence is described twice wherever a position sits on a shared
        # vertex (t = 1 on segment k, t = 0 on segment k+1), and the first version of this counted
        # those as two tied positions -- reporting 7 of 25 frame C points with "an exact tie" on a
        # set where no point had more than one candidate. A count of descriptions is not a count of
        # candidates.
        a_keys = {p.occurrence for p in a}
        c_keys = {p.occurrence for p in c}
        dropped = [p for p in a if p.occurrence in a_keys - c_keys]
        by_record_exact: dict[int, Fraction] = {}
        for p in banded:
            cur = by_record_exact.get(p.record)
            if cur is None or p.exact_sq < cur:
                by_record_exact[p.record] = p.exact_sq
        out["c_drops"] = len(dropped)
        # A **tie** needs two occurrences at the same exact distance. The first version asked only
        # whether the dropped candidate equalled its record's exact minimum, which is a different
        # question, and it labelled two float/exact INVERSIONS as ties (Codex pass 36 F1): at both
        # points the exact minimum was unique, and C kept a position that is exactly FARTHER while
        # dropping the exactly nearest one. Both are now counted, separately.
        exact_counts: dict[tuple[int, Fraction], int] = {}
        for q in banded:
            exact_counts[(q.record, q.exact_sq)] = exact_counts.get((q.record, q.exact_sq), 0) + 1
        out["c_drops_a_genuine_exact_tie"] = sum(
            1 for p in dropped
            if p.exact_sq == by_record_exact[p.record] and exact_counts[(p.record, p.exact_sq)] > 1)
        out["c_drops_the_unique_exact_minimum"] = sum(
            1 for p in dropped
            if p.exact_sq == by_record_exact[p.record]
            and exact_counts[(p.record, p.exact_sq)] == 1)
        # Among A's retained candidates: how many sit at the exact minimum **of that set** (a
        # genuine tie the band preserved) and how many above it (a near-miss the band admitted).
        # Taken over the retained set rather than over raw positions, so the two numbers describe
        # the same population -- the smoke run produced "2 candidates, both above the minimum",
        # which is impossible for any set that contains its own minimum.
        if a:
            exact_min_a = min(p.exact_sq for p in a)
            at_min = [p for p in a if p.exact_sq == exact_min_a]
            out["candidates_at_exact_min"] = len(at_min)
            out["candidates_above_exact_min"] = sum(1 for p in a if p.exact_sq > exact_min_a)
            # Two kinds of exact tie, and conflating them would be the familiar error. Under the
            # design's record definition, coincident PARALLEL records carrying different weights
            # are separate records with the same geometry, so a point near them has several
            # candidates at the same POSITION and the same exact distance. That is a tie in the
            # design's sense and a duplicate in the geometric sense. A tie between candidates at
            # DISTINCT positions is the thing §2.2's band exists to preserve -- two arms of a road
            # genuinely equidistant -- and only that one is a geometric tie.
            distinct = []
            for p in at_min:
                if not any(math.hypot(p.x - qx, p.y - qy) <= POSITION_TOL_M for qx, qy in distinct):
                    distinct.append((p.x, p.y))
            out["distinct_positions_at_exact_min"] = len(distinct)
        else:
            out["candidates_at_exact_min"] = 0
            out["candidates_above_exact_min"] = 0
            out["distinct_positions_at_exact_min"] = 0
        # Why that was possible, and it is a real property worth counting rather than smoothing
        # over: the occurrence key is built from the **float** clamp, so two descriptions of one
        # shared vertex collapse into one candidate -- but `exact_segment_sq` clamps in exact
        # arithmetic, and where the two clamps disagree the merged descriptions carry different
        # exact squared distances. The representative is chosen by residual and arclength, not by
        # exact distance, so it need not be the nearer of the two.
        buckets: dict[tuple, list[Fraction]] = {}
        for p in banded:
            buckets.setdefault(p.occurrence, []).append(p.exact_sq)
        out["occurrences_whose_descriptions_disagree_exactly"] = sum(
            1 for v in buckets.values() if len(set(v)) > 1)
    return out


def _seg_ends(geoms, p: Pos) -> tuple[float, float, float, float]:
    coords = shapely.get_coordinates(geoms[p.record])
    (ax, ay), (bx, by) = coords[p.seg], coords[p.seg + 1]
    return float(ax), float(ay), float(bx), float(by)


# --------------------------------------------------------------------------- impact, bounded
#: Walk access speed for the connector, taken from `speeds.access_speed_mps` rather than retyped
#: as 1.40 * 0.9 -- a second copy of a rule is a second thing that can drift from it.
ACCESS_MPS = access_speed_mps("walk")


def impact_bound(eidx, a: list[Pos], other: list[Pos]) -> dict | None:
    """Bounds the **objective 1** time difference between two candidate sets, with no routing.

    `|delta arclength| / L * T` plus the band's connector difference. The argument: objective 1 is
    `min over options of (time to an endpoint + partial traversal)`, and moving along a record
    trades one endpoint's partial term against the other's by exactly that amount, so the minimum
    moves by no more than it, whatever lies beyond. Design §2.1 defines objective 1 as
    `min over eligible destinations of total travel time`, and **E1 is defined against objective
    1**, so this is the objective the impact question actually feeds.

    **What it does NOT bound, and the first version claimed it did (Codex pass 36 F2).**

    * **Objective 2** -- `time along the path minimising total COST`. Selection by cost and
      reporting by time means an arbitrarily small cost change can switch the selected route and
      move the reported time without limit. Pass 36's counterexample: a bound of **0.0129365 s**
      against an objective-2 move from **249.995 s to 129.983968 s**, a 120.011 s change produced
      by an apportioned 120 s restricted penalty. No local quantity can bound this; the
      objective-2-minus-objective-1 gap is the pass-8 H2 selection gap, reported inside E1 as its
      own signed distribution.
    * **Route availability.** On a one-way record, moving the attachment can leave no legal journey
      at all -- a finite time becomes none, which no difference in seconds describes. The bound is
      therefore reported **only** where every record in dispute is traversable in both directions,
      and the excluded cases are counted rather than absorbed.

    Returns None when the two sets agree. Otherwise the symmetric difference is partitioned:

    * **same record, both directions legal** -- the bound applies;
    * **same record, one-way** -- excluded, availability can change;
    * **cross record** -- unbounded here. Two candidates on different records enter different
      networks and only routing can say what that costs.
    """
    a_keys = {p.occurrence: p for p in a}
    o_keys = {p.occurrence: p for p in other}
    only_a = [a_keys[k] for k in a_keys.keys() - o_keys.keys()]
    only_o = [o_keys[k] for k in o_keys.keys() - a_keys.keys()]
    if not only_a and not only_o:
        return None
    differing = only_a + only_o
    shared_records = {p.record for p in only_a} | {p.record for p in only_o}
    # Is every differing candidate on a record the other set also attaches to? If so the dispute is
    # about WHERE on a shared record, and the bound applies.
    records_a = {p.record for p in a}
    records_o = {p.record for p in other}
    same_record_only = shared_records <= (records_a & records_o)
    if not same_record_only:
        return {"scope": "cross_record", "bound_s": None,
                "records_in_dispute": len(shared_records)}
    # Availability: a one-way record can lose its journey entirely when the attachment moves, and
    # no bound in seconds covers that (pass 36 F2). Excluded and counted, not absorbed.
    if any(not (np.isfinite(eidx.fwd_time[r]) and np.isfinite(eidx.rev_time[r]))
           for r in shared_records):
        return {"scope": "one_way", "bound_s": None,
                "records_in_dispute": len(shared_records)}
    worst = 0.0
    for record in shared_records:
        arcs = [p.arclength for p in a if p.record == record]
        arcs += [p.arclength for p in other if p.record == record]
        length = float(shapely.length(eidx.geoms[record]))
        times = [t for t in (eidx.fwd_time[record], eidx.rev_time[record]) if np.isfinite(t)]
        if not times or length <= 0.0:
            continue
        spread = max(arcs) - min(arcs)
        worst = max(worst, spread / length * max(times))
    return {"scope": "same_record_bidirectional",
            "bound_s": worst + ATTACH_TIE_M / ACCESS_MPS,
            "arclength_spread_m": max(
                (max(p.arclength for p in differing) - min(p.arclength for p in differing)), 0.0)}


# --------------------------------------------------------------------------- subdivision
def subdivide(geom):
    """Insert each segment's midpoint: a lawful re-expression of the same road.

    Segments shorter than twice `MIN_SEGMENT_M` are left alone -- halving one would produce
    inadmissible segments, and the toy domain is explicit that it is not closed under subdivision at
    its own boundary. The count of skipped segments is reported rather than hidden.
    """
    coords = shapely.get_coordinates(geom)
    out = [tuple(coords[0])]
    skipped = 0
    for (ax, ay), (bx, by) in itertools.pairwise(coords):
        if math.hypot(bx - ax, by - ay) >= 2.0 * MIN_SEGMENT_M:
            out.append(((ax + bx) / 2.0, (ay + by) / 2.0))
        else:
            skipped += 1
        out.append((float(bx), float(by)))
    return shapely.LineString(out), skipped


def split_record(geom, next_id: int) -> tuple[dict, int]:
    """Express one record as two, cut at its arclength midpoint: a degree-two record split.

Lawful in the sense design §2.2 uses -- the road, its legal traversals and (now) its length
    are unchanged, the weights apportion, and the cut introduces a degree-two node where there was
    none. `A` is supposed to agree across the two forms and `C` is not; that is pass 24 F2.

    **It does not preserve EXACT geometry.** An interior cut introduces `(a + t*(b - a))` rounded
    to binary64, which is not exactly on the original line, so a convention defined by exact
    arithmetic can move under it for a reason that is arithmetic rather than representational
    (pass 36 F5). `split_every_segment` cuts only at existing vertices and is the transformation
    that preserves exact geometry.

    Returns `{record id: geometry}` for the halves and the next free id. A record too short to cut
    into two admissible pieces is returned unsplit, and the caller counts that.
    """
    coords = [tuple(map(float, c)) for c in shapely.get_coordinates(geom)]
    total = float(shapely.length(geom))
    if total < 4.0 * MIN_SEGMENT_M:
        return {next_id: shapely.LineString(coords)}, next_id + 1
    half = total / 2.0
    run = 0.0
    for i, ((ax, ay), (bx, by)) in enumerate(itertools.pairwise(coords)):
        seg = math.hypot(bx - ax, by - ay)
        if run + seg >= half and seg > 0.0:
            t = (half - run) / seg
            mid = (ax + t * (bx - ax), ay + t * (by - ay))
            # The two pieces must SHARE the cut vertex, or the pair is not the same road. The first
            # version built the second piece from the segment's start where the cut landed on its
            # end, which turned (0,0),(1,0),(2,0) into pieces of length 1 and 2 -- total 3 against
            # an original 2 (Codex pass 36 F5). Where the cut lands within MIN_SEGMENT_M of an
            # existing vertex it is snapped to that vertex, which keeps both pieces admissible and
            # introduces no new coordinate at all.
            if math.hypot(mid[0] - ax, mid[1] - ay) < MIN_SEGMENT_M:
                first, rest = coords[:i + 1], coords[i:]
            elif math.hypot(mid[0] - bx, mid[1] - by) < MIN_SEGMENT_M:
                first, rest = coords[:i + 2], coords[i + 1:]
            else:
                first, rest = coords[:i + 1] + [mid], [mid] + coords[i + 1:]
            if len(first) < 2 or len(rest) < 2:
                return {next_id: shapely.LineString(coords)}, next_id + 1
            return ({next_id: shapely.LineString(first),
                     next_id + 1: shapely.LineString(rest)}, next_id + 2)
        run += seg
    return {next_id: shapely.LineString(coords)}, next_id + 1


def split_every_segment(geom, next_id: int) -> tuple[dict, int]:
    """Express one record as one record per segment: the strongest lawful record segmentation.

    This is the fair counterpart to `subdivide`. Subdividing every segment introduces one new
    clamped endpoint per segment and so gives A many chances to gain a candidate; splitting a
    record only at its midpoint introduces one new record boundary and so gives C exactly one.
    Rates from transformations of such different size are **not** a ranking of sensitivity, which
    is why this exists: it makes every segment endpoint a record boundary, so C must keep each
    segment's own minimum, and the two conventions are then tested at comparable strength.

    Still lawful: the road, its length and its legal traversals are unchanged, the weights
    apportion, and every cut is at an existing vertex and so a degree-two node.
    """
    coords = [tuple(map(float, c)) for c in shapely.get_coordinates(geom)]
    out: dict = {}
    for (ax, ay), (bx, by) in itertools.pairwise(coords):
        if math.hypot(bx - ax, by - ay) == 0.0:
            continue                       # a zero-length segment is not a record
        out[next_id] = shapely.LineString([(ax, ay), (bx, by)])
        next_id += 1
    if not out:
        out[next_id] = shapely.LineString(coords)
        next_id += 1
    return out, next_id


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subdivision-sample", type=int, default=5000,
                    help="points per set for the representation-sensitivity check, drawn at "
                         "random with --subdivision-seed")
    ap.add_argument("--subdivision-seed", type=int, default=20261110,
                    help="seed for the subdivision draw, so the rate is reproducible")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap each point set, for the benchmark the time box asks for before "
                         "committing to a larger sample or a census")
    ap.add_argument("--adoption-sample", type=int, default=5000,
                    help="how many points of each set to measure under BOTH arithmetics "
                         "(step 4 plan task 5). 0 skips it")
    ap.add_argument("--adoption-seed", type=int, default=20261112,
                    help="seed for the adoption subsample of a set larger than the sample size")
    ap.add_argument("--adoption-census", action="store_true",
                    help="run the adoption check over EVERY point of every set rather than a "
                         "subsample. About 3-4 ms a point, so roughly 90 minutes with --census")
    ap.add_argument("--census", action="store_true",
                    help="also run the attachment stage over both whole populations: every "
                         "structure centroid and every cell centre")
    args = ap.parse_args()

    t0 = time.perf_counter()
    G = load_roads_graph()
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode="walk")
    G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, comp = largest_component(G)
    index = {n: i for i, n in enumerate(G.nodes())}
    # The DESIGN's edge records, not production's geometry groups. T0 measures the design's
    # convention, so it has to attach to the design's record set; `snap.EdgeIndex`'s grouping is
    # what production routes on and belongs to E1, not to this question. The production count is
    # reported beside it so the size of the difference is visible (Codex pass 36 F4).
    eidx = Records(G, index, kind="design")
    production = Records(G, index, kind="production")
    geoms = eidx.geoms
    tree = eidx.tree
    prep_s = time.perf_counter() - t0
    graph_edges = G.number_of_edges()
    print(f"prepared in {prep_s:.0f}s: {G.number_of_nodes():,} nodes, {graph_edges:,} graph edges "
          f"-> {len(geoms):,} design records, {len(production):,} production records", flush=True)

    manifest = read_graph_cache_manifest() or {}
    out: dict = {
        "built": stamp(),
        "pinned": {
            "metro": METRO.name,
            "graphml_sha256": manifest.get("graphml_sha256"),
            "way_tags": manifest.get("way_tags"),
            "profile_version": profile.profile_version(),
            "grid_version": profile.grid_version(GRID),
            "places": {"path": str(ACCEPTED_PLACES.relative_to(ACCEPTED_PLACES.parents[2])),
                       "sha256": file_digest(ACCEPTED_PLACES)},
            "attach_tie_m": ATTACH_TIE_M,
            "max_access_m": MAX_ACCESS_M,
            "poi_snap_max_m": POI_SNAP_MAX_M,
            "runtime": {"python": sys.version.split()[0], "numpy": np.__version__,
                        "shapely": shapely.__version__, "platform": platform.platform()},
        },
        "graph": {
            "nodes": G.number_of_nodes(), "graph_edges": graph_edges,
            "record_definition": "design: (node pair, canonical geometry, travel_time, cost)",
            "design_records": len(geoms),
            "production_records": len(production),
            "records_production_collapses": len(geoms) - len(production),
            "merge_note": "`symmetrise` copies the data dict exactly, so a walk graph's "
                          "forward/reverse pair has identical weights and collapses into one "
                          "bidirectional record under BOTH definitions. The difference between "
                          "the two counts is therefore parallel roads carrying DIFFERENT weights, "
                          "which design §2.4 requires be kept apart because grouping must not "
                          "answer a ranking question. The first run of this pilot attached to the "
                          "production grouping and its prevalence counts are superseded "
                          "(Codex pass 36 F4).",
            "components": comp.summary,
            "prepare_s": round(prep_s, 1),
        },
        "sets": {},
    }

    # ---- the three point sets ----------------------------------------------------------------
    point_sets = []
    for stem, label in (("frame_b_51a59463", "frame_B_structures"),
                        ("frame_c_7914e80a", "frame_C_area")):
        frame = read_frame(FRAMES / f"{stem}.json")
        if frame.crs != GRID.crs:
            raise SystemExit(f"{stem} is in {frame.crs}, the graph is in {GRID.crs}")
        point_sets.append((label, np.array(frame.points, dtype=np.float64), MAX_ACCESS_M,
                           {"frame_digest": frame.digest, "kind": frame.kind, "n": frame.n,
                            "population_n": frame.population_n, "seed": frame.seed,
                            "is_a_sample": True}))
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_overture(places, "grocery")
    cent = sel.geometry.centroid
    point_sets.append(("grocery_destinations",
                       np.column_stack([cent.x.to_numpy(), cent.y.to_numpy()]),
                       POI_SNAP_MAX_M,
                       {"n": int(len(sel)), "is_a_sample": False,
                        "note": "a census of the accepted grocery coordinates, not a sample"}))

    if args.census:
        ids, pop_pts, pop_n = structure_population(ACCEPTED_BUILDINGS, GRID)
        point_sets.append(("census_all_structures", np.asarray(pop_pts, dtype=np.float64),
                           MAX_ACCESS_M,
                           {"n": int(pop_n), "is_a_sample": False,
                            "note": "a census of frame B's population: every structure centroid "
                                    "inside the grid. No sampling uncertainty."}))
        cx, cy = GRID.cell_centers_xy()
        point_sets.append(("census_all_cell_centres",
                           np.column_stack([cx.ravel(), cy.ravel()]), MAX_ACCESS_M,
                           {"n": int(cx.size), "is_a_sample": False,
                            "note": "every cell CENTRE. This is NOT a census of frame C, which "
                                    "draws independent points within each cell: a centre census "
                                    "does not count every affected location inside a cell, and "
                                    "the two must not be compared as if it did."}))

    # Applied AFTER the census sets are appended. It used to be applied before them, so
    # `--limit 3000 --census` recorded `limited_to: 3000` while running both 500,000-point
    # censuses in full -- a shakedown flag that silently did nothing to the only sets large enough
    # to need it, and said otherwise in the artifact.
    if args.limit:
        point_sets = [(lbl, pts[:args.limit], cap, dict(meta, limited_to=args.limit))
                      for lbl, pts, cap, meta in point_sets]
        out["limited_to"] = args.limit

    for label, pts, cap, meta in point_sets:
        t = time.perf_counter()
        acc = Accum()
        for i, (x, y) in enumerate(pts):
            acc.add(measure_point(geoms, tree, float(x), float(y), cap), eidx)
            if label.startswith("census") and i and i % 100_000 == 0:
                print(f"  {label}: {i:,} of {len(pts):,} "
                      f"({time.perf_counter() - t:.0f}s)", flush=True)
        elapsed = time.perf_counter() - t
        n = acc.n
        agg = acc.summary(cap_m=cap, meta=meta, seconds=elapsed)
        out["sets"][label] = agg
        print(f"\n{label}: {n} points in {elapsed:.1f}s ({agg['ms_per_point']:.2f} ms/point)",
              flush=True)
        for k in ("A", "C", "D"):
            v = agg[k]
            print(f"  {k}: eligible {v['eligible']}/{n}, >1 candidate "
                  f"{v['points_with_multiple_candidates']}, on >1 record "
                  f"{v['points_with_candidates_on_multiple_records']}, >1 occurrence on one record "
                  f"{v['points_with_multiple_occurrences_on_one_record']}", flush=True)
        print(f"  A vs C: {agg['A_vs_C_set_differs']} sets differ, "
              f"{agg['A_vs_C_eligibility_differs']} eligibility differ", flush=True)
        print(f"  A vs D: {agg['A_vs_D_set_differs']} sets differ, "
              f"{agg['A_vs_D_eligibility_differs']} eligibility differ", flush=True)
        print(f"  exact: {agg['exact']}", flush=True)

    # ---- the labelled adoption of design revision 13's primitives ---------------------------
    if args.adoption_sample:
        print(f"\nadoption check: both arithmetics on up to {args.adoption_sample:,} points "
              f"of each set", flush=True)
        ad: dict = {
            "note": ("Step 4 plan task 5. Design revision 13's §2.4 item 7 primitives against the "
                     "arithmetic this pilot published, on the SAME points and the same windows. "
                     "A and D are one rule measured two ways; C under exact arithmetic is a "
                     "DIFFERENT rule and is reported as C_exact, inheriting none of this pilot's "
                     "evidence. An exact band PREDICATE is convention B and is not implemented."),
            "sample_per_set": ("census" if args.adoption_census else args.adoption_sample),
            "seed": args.adoption_seed,
            "sentinel": adoption_sentinel(),
            "sets": {},
        }
        for c in ad["sentinel"]:
            print(f"  sentinel {c['witness']}: float {c['float_occurrence']} "
                  f"vs exact {c['exact_occurrence']}", flush=True)
        rng_ad = np.random.default_rng(args.adoption_seed)
        for label, pts, cap, _meta in point_sets:
            if args.adoption_census or len(pts) <= args.adoption_sample:
                taken, how = pts, "every point in the set"
            else:
                taken = pts[rng_ad.choice(len(pts), size=args.adoption_sample, replace=False)]
                how = f"a {args.adoption_sample:,}-point subsample, seed {args.adoption_seed}"
            t = time.perf_counter()
            stats = adoption_stats(geoms, tree, taken, cap)
            stats["sampling"] = how
            stats["seconds"] = round(time.perf_counter() - t, 2)
            ad["sets"][label] = stats
            print(f"  {label}: {stats['points']:,} points, {how}", flush=True)
            for name in ("A_exact_vs_A", "C_exact_vs_C", "D_exact_vs_D"):
                print(f"    {name:14s} eligibility {stats['eligibility_changed'][name]}, "
                      f"count {stats['count_changed'][name]}, "
                      f"occurrences {stats['occurrences_changed'][name]}, "
                      f"PLACES {stats['places_changed'][name]}", flush=True)
            r = stats['raw']
            print(f"    raw: {r['positions_compared']:,} positions, residual differs "
                  f"{r['residual_differs']:,} (max {r['max_abs_residual_diff_m']:.3e} m), "
                  f"arclength differs {r['arclength_differs']:,} "
                  f"(max {r['max_abs_arclength_diff_m']:.3e} m), parameter differs "
                  f"{r['parameter_differs']:,}, POSITION moved "
                  f"{r['position_differs']:,} (max {r['max_position_shift_m']:.3e} m), "
                  f"vertex/interior flips {r['vertex_or_interior_differs']:,}", flush=True)
        out["adoption"] = ad

    # ---- representation sensitivity, kept out of the population estimates --------------------
    print(f"\nsubdivision check on the first {args.subdivision_sample} of each set", flush=True)
    sub: dict = {"note": "TWO lawful re-expressions of every record in the point's band window, "
                         "neither moving the road, changing its length or altering which "
                         "traversals are legal: `subdivide` inserts every segment's midpoint, and "
                         "`split_midpoint` expresses each record as two cut at its arclength "
                         "midpoint, and `split_every_segment` makes every segment its own record. All three "
                         "are reported because they penalise different "
                         "conventions -- reporting only the first would be choosing the "
                         "transformation that makes the incumbent look worst. Drawn at RANDOM "
                         "with the seed below; the first version took a prefix, which on the two "
                         "censuses is id or row order and so a spatial bias, and a rate from a "
                         "biased slice is not a rate. Kept out of the population estimates above: "
                         "this is a transformation diagnostic on its own sample.",
                 "sample_per_set": args.subdivision_sample,
                 "seed": args.subdivision_seed, "sets": {}}
    rng = np.random.default_rng(args.subdivision_seed)

    def recompute(shadow: dict, window, px: float, py: float, cap: float) -> dict:
        after_raw = raw_positions(shadow, window, px, py)
        cmin = min(p.residual for p in after_raw)
        for p in after_raw:
            if p.residual <= cmin + ATTACH_TIE_M:
                p.exact_sq = exact_segment_sq(px, py, *_seg_ends(shadow, p))
        banded = [p for p in after_raw if p.residual <= cmin + ATTACH_TIE_M]
        return {"A": dedup_and_cap(convention_a(after_raw, cmin), cap),
                "C": dedup_and_cap(convention_c(after_raw, cmin), cap),
                "D": dedup_and_cap(convention_d(banded), cap)}

    for label, pts, cap, _meta in point_sets:
        kinds = ("subdivide", "split_midpoint", "split_every_segment")
        changed = {t: {"A": 0, "C": 0, "D": 0} for t in kinds}
        moved = {t: {"A": 0, "C": 0, "D": 0} for t in kinds}
        elig_changed = {t: {"A": 0, "C": 0, "D": 0} for t in kinds}
        skipped_segments = 0
        unsplittable = 0
        if len(pts) <= args.subdivision_sample:
            taken = pts
        else:
            taken = pts[rng.choice(len(pts), size=args.subdivision_sample, replace=False)]
        for x, y in taken:
            px, py = float(x), float(y)
            before = measure_point(geoms, tree, px, py, cap)
            window = before["_window"]

            # (1) insert every segment's midpoint. Penalises A; C and D are blind to it.
            # Only the window records are needed, and `raw_positions` touches nothing else, so
            # this is a dict of a handful of entries rather than a copy of 713,000.
            shadow = {}
            for r in window:
                g2, sk = subdivide(geoms[r])
                shadow[int(r)] = g2
                skipped_segments += sk
            after = recompute(shadow, window, px, py, cap)

            # (2) express each record as two, cut at its arclength midpoint. This is the case A is
            # supposed to win and C to lose (pass 24 F2), and measuring only (1) would be choosing
            # the transformation that makes the incumbent look worst.
            results = {"subdivide": after}
            for kind, fn in (("split_midpoint", split_record),
                             ("split_every_segment", split_every_segment)):
                shadow2: dict = {}
                window2: list[int] = []
                next_id = 0
                for r in window:
                    pieces, next_id = fn(geoms[r], next_id)
                    if kind == "split_midpoint" and len(pieces) == 1:
                        unsplittable += 1
                    shadow2.update(pieces)
                    window2.extend(pieces)
                results[kind] = recompute(shadow2, np.asarray(window2), px, py, cap)

            for kind, got in results.items():
                for k in ("A", "C", "D"):
                    if len(got[k]) != before["counts"][k]:
                        changed[kind][k] += 1
                    if positions_differ(before["_sets"][k], got[k]):
                        moved[kind][k] += 1
                    if bool(got[k]) != before["eligible"][k]:
                        elig_changed[kind][k] += 1
        sub["sets"][label] = {"points": len(taken), "candidate_count_changed": changed,
                              "candidate_positions_changed": moved,
                              "eligibility_changed": elig_changed,
                              "segments_too_short_to_halve": skipped_segments,
                              "records_too_short_to_split": unsplittable}
        print(f"  {label} ({len(taken)} points):", flush=True)
        for t in kinds:
            print(f"    {t:<20} count {changed[t]}  POSITIONS {moved[t]}  elig "
                  f"{elig_changed[t]}", flush=True)
    out["subdivision"] = sub

    path = ARTIFACT
    path.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8", newline="\n")
    print(f"\nwrote {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
