"""Render T0's measured figures into the experiment write-up, from the artifact.

Every figure in the generated block is a function of
`docs/experiments/t0-attachment-pilot.json`, which is tracked so the two travel together. Nothing is
transcribed, because transcription is how this project has produced wrong figures: a swapped table
row, a count of descriptions reported as a count of candidates, an element-blind `grep -c` quoted as
a way count. The prose around the block is written by hand; the numbers inside it are not.

Rewrites only the text between the two markers in
`docs/experiments/t0-attachment-pilot.md`, so the pre-registration and the interpretation are never
touched by a re-render.

Run from v2/:  uv run python scripts/render_t0_results.py [--check]
`--check` re-renders and fails if the document is out of date, writing nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ART = (Path(__file__).resolve().parents[2] / "docs" / "experiments"
       / "t0-attachment-pilot.json")
DOC = (Path(__file__).resolve().parents[2] / "docs" / "experiments"
       / "t0-attachment-pilot.md")
BEGIN = "<!-- BEGIN GENERATED: scripts/render_t0_results.py -->"
END = "<!-- END GENERATED -->"

LABELS = {
    "frame_B_structures": "frame B sample",
    "frame_C_area": "frame C sample",
    "grocery_destinations": "groceries (census)",
    "census_all_structures": "**all structures (census)**",
    "census_all_cell_centres": "**all cell centres (census)**",
}
ORDER = list(LABELS)


def pct(k: int, n: int) -> str:
    return f"{100.0 * k / n:.4f}%" if n else "—"


def render(d: dict) -> str:
    sets = d["sets"]
    present = [k for k in ORDER if k in sets]
    out: list[str] = []

    g = d["graph"]
    out.append("**The graph and the record set.** "
               f"{g['nodes']:,} nodes, {g['graph_edges']:,} directed graph edges, "
               f"**{g['design_records']:,} design records** against "
               f"{g['production_records']:,} production ones — "
               f"{g['records_production_collapses']:,} records that `snap.EdgeIndex`'s grouping "
               "collapses, being parallel roads with different weights. The measurement attaches "
               "to the design's records; the first run attached to production's and its "
               "prevalence counts are superseded.")
    p = d["pinned"]
    out.append("")
    out.append(f"**Pinned.** graph `{str(p['graphml_sha256'])[:12]}…`, profile "
               f"`{p['profile_version']}`, grid `{p['grid_version']}`, places "
               f"`{p['places']['sha256'][:12]}…`, `attach_tie_m` {p['attach_tie_m']}, caps "
               f"{p['max_access_m']:g} m / {p['poi_snap_max_m']:g} m, shapely "
               f"{p['runtime']['shapely']}, numpy {p['runtime']['numpy']}.")

    # ---- prevalence
    out.append("")
    out.append("### How often a point has more than one candidate")
    out.append("")
    out.append("| set | points | A | C | D | on >1 record (A) | >1 occurrence on one record (A) |")
    out.append("|---|---:|---:|---:|---:|---:|---:|")
    for k in present:
        v = sets[k]
        n = v["points"]
        out.append(
            f"| {LABELS[k]} | {n:,} | {v['A']['points_with_multiple_candidates']:,} "
            f"({pct(v['A']['points_with_multiple_candidates'], n)}) "
            f"| {v['C']['points_with_multiple_candidates']:,} "
            f"({pct(v['C']['points_with_multiple_candidates'], n)}) "
            f"| {v['D']['points_with_multiple_candidates']:,} "
            f"({pct(v['D']['points_with_multiple_candidates'], n)}) "
            f"| {v['A']['points_with_candidates_on_multiple_records']:,} "
            f"| {v['A']['points_with_multiple_occurrences_on_one_record']:,} |")

    # ---- disagreement and eligibility
    out.append("")
    out.append("### Where the conventions disagree, and whether it changes an answer")
    out.append("")
    out.append("| set | points | A≠C candidates | A≠C **positions** | A≠D candidates "
               "| A≠D **positions** | A≠C eligibility | A≠D eligibility |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    tot_n = tot_ec = tot_ed = 0
    for k in present:
        v = sets[k]
        n = v["points"]
        out.append(f"| {LABELS[k]} | {n:,} | {v['A_vs_C_set_differs']:,} "
                   f"({pct(v['A_vs_C_set_differs'], n)}) "
                   f"| **{v['A_vs_C_places_differ']:,}** ({pct(v['A_vs_C_places_differ'], n)}) "
                   f"| {v['A_vs_D_set_differs']:,} ({pct(v['A_vs_D_set_differs'], n)}) "
                   f"| **{v['A_vs_D_places_differ']:,}** ({pct(v['A_vs_D_places_differ'], n)}) "
                   f"| {v['A_vs_C_eligibility_differs']:,} "
                   f"| {v['A_vs_D_eligibility_differs']:,} |")
        if k.startswith("census"):
            tot_n += n
            tot_ec += v["A_vs_C_eligibility_differs"]
            tot_ed += v["A_vs_D_eligibility_differs"]
    out.append("")
    out.append(f"Over both censuses — **{tot_n:,} points** — eligibility differs on "
               f"**{tot_ec}** points for A against C and **{tot_ed}** for A against D.")

    # ---- the exact diagnostic
    out.append("")
    out.append("### The exact rational diagnostic")
    out.append("")
    out.append("A *tie* needs two occurrences at the same exact distance. A candidate that is "
               "simply its record's **unique** exact minimum is not one, and C dropping it is a "
               "float/exact **inversion** — C keeps a position that is exactly farther. The two "
               "were conflated in the first run (Codex pass 36 F1). And under the design's record "
               "definition, coincident parallel roads give several candidates at one *position*, "
               "which is a tie in the design's sense and a duplicate geometrically, so the "
               "distinct-position count is reported separately.")
    out.append("")
    out.append("| set | points | A cand. C drops | …genuine exact ties | …unique exact minimum "
               "(inversions) | ≥2 candidates at exact min | ≥2 **distinct positions** at exact min |")
    out.append("|---|---:|---:|---:|---:|---:|---:|")
    for k in present:
        v, n = sets[k], sets[k]["points"]
        e = v["exact"]
        out.append(f"| {LABELS[k]} | {n:,} | {e['A_candidates_C_drops']:,} "
                   f"| **{e['A_candidates_C_drops_that_are_genuine_exact_ties']}** "
                   f"| **{e.get('A_candidates_C_drops_that_are_the_unique_exact_minimum', 0)}** "
                   f"| {e['points_with_two_or_more_candidates_at_the_exact_minimum']:,} "
                   f"({pct(e['points_with_two_or_more_candidates_at_the_exact_minimum'], n)}) "
                   f"| {e.get('points_with_two_or_more_DISTINCT_POSITIONS_at_the_exact_minimum', 0):,} "
                   f"({pct(e.get('points_with_two_or_more_DISTINCT_POSITIONS_at_the_exact_minimum', 0), n)}) |")

    # ---- the impact bound
    out.append("")
    out.append("### The objective-1 impact bound, with no routing")
    out.append("")
    out.append("`|Δarclength| / L × T` plus the band's connector difference. It bounds **objective "
               "1** — `min over eligible destinations of total travel time`, which is the "
               "objective E1 is defined against (design §2.1). It does **not** bound objective 2, "
               "the time along the *cost*-minimising path: selection by cost and reporting by time "
               "means a 0.013 s cost change can switch the route and move the reported time by "
               "120 s (Codex pass 36 F2). Nor does it bound route **availability**, so points "
               "whose disputed record is one-way are excluded and counted — on a one-way record a "
               "finite journey can become none, which no difference in seconds describes.")
    out.append("")
    out.append("| set | pair | differing | bounded | one-way (excl.) | cross record (unbounded) "
               "| median | max | >1 s | >30 s | >60 s |")
    out.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for k in present:
        for pair in ("A_vs_C", "A_vs_D"):
            b = sets[k]["impact_bound"][pair]
            s_ = b["bound_s"]
            cells = (f"{s_['median']:.4f} s | {s_['max']:.2f} s | {s_['over_1s']:,} "
                     f"| {s_['over_30s']:,} | {s_['over_60s']:,}") if s_ else "— | — | — | — | —"
            out.append(f"| {LABELS[k]} | {pair.replace('_', ' ')} | {b['points_differing']:,} "
                       f"| {b.get('same_record_bidirectional_bounded', 0):,} "
                       f"| {b.get('one_way_unbounded', 0):,} "
                       f"| {b['cross_record_unbounded']:,} | {cells} |")

    # ---- representation sensitivity
    sub = d["subdivision"]
    out.append("")
    out.append("### Representation sensitivity: three lawful re-expressions")
    out.append("")
    out.append(f"Drawn at random, seed `{sub['seed']}`, at most {sub['sample_per_set']:,} points "
               "per set. Kept out of the population estimates above. **The three transformations "
               "are not of equal strength** — `subdivide` adds one clamped endpoint per segment, "
               "`split_midpoint` one record boundary per record, `split_every_segment` one per "
               "segment — so these rates are not a ranking of sensitivity between conventions.")
    out.append("")
    out.append("Two columns per convention, and the difference between them is the whole point: "
               "a count can change while every retained candidate stays at the same **place**, and "
               "a set of candidates at the same places minimises to the same journey. Only a "
               "position change can move a reported time.")
    out.append("")
    out.append("| set | points | transformation | A count | A **pos** | C count | C **pos** "
               "| D count | D **pos** | eligibility |")
    out.append("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|")
    for k in [x for x in ORDER if x in sub["sets"]]:
        v = sub["sets"][k]
        n = v["points"]
        for t, got in v["candidate_count_changed"].items():
            mv = v["candidate_positions_changed"][t]
            el = v["eligibility_changed"][t]
            cells = " | ".join(
                f"{got[c]:,} | **{mv[c]:,}** ({pct(mv[c], n)})" for c in ("A", "C", "D"))
            out.append(f"| {LABELS[k]} | {n:,} | `{t}` | {cells} | {sum(el.values())} |")

    # ---- cost
    out.append("")
    out.append("### Cost")
    out.append("")
    out.append("| set | points | seconds | ms/point |")
    out.append("|---|---:|---:|---:|")
    for k in present:
        v = sets[k]
        out.append(f"| {LABELS[k]} | {v['points']:,} | {v['seconds']:.1f} | "
                   f"{v['ms_per_point']:.3f} |")
    out.append("")
    out.append(f"Graph preparation {g['prepare_s']:.0f} s, once. The attachment stage is cheap "
               "enough that the time box's \"census it if benchmarking supports it\" applies, "
               "which is why both censuses are here rather than a 500-point bound.")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="fail if the document is out of date; write nothing")
    args = ap.parse_args()
    if not ART.exists():
        raise SystemExit(f"no artifact at {ART}; run scripts/t0_attachment_pilot.py --census")
    body = render(json.loads(ART.read_text(encoding="utf-8")))
    text = DOC.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        raise SystemExit(f"{DOC.name} has no generated block; add the markers first")
    head, _, tail = text.partition(BEGIN)
    _, _, tail = tail.partition(END)
    new = f"{head}{BEGIN}\n\n{body}\n\n{END}{tail}"
    if args.check:
        if new != text:
            print(f"{DOC.name} is out of date; re-run without --check")
            return 1
        print(f"{DOC.name} matches the artifact")
        return 0
    if new == text:
        print(f"{DOC.name} already matches the artifact")
        return 0
    DOC.write_text(new, encoding="utf-8", newline="\n")
    print(f"rendered {len(body.splitlines())} lines into {DOC.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
