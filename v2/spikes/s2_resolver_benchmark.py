"""The expanded graded resolver benchmark. Phase 1 S2.1.

Four consecutive Codex passes found over-corrections in `resolve.py`: pass 10 required equal
categories and broke de-duplication, pass 11 repeated it for stations and fuel, pass 12 replaced it
with a subsidiary boolean that merged a car park with its airport, pass 13 found three more. Each
fix closed the case in the review and opened an adjacent one nobody had written down.

The only thing that caught every one of those regressions was a graded real-data benchmark — and it
had **five** graded queries. So the response to pass 13 is not another round of point fixes: it is to
stop fixing against review findings and start fixing against a benchmark big enough to notice.

`benchmarks/resolver_queries.json` holds the queries with their intended answers **written down
first**. Two kinds of assertion, because most of what keeps breaking is not location:

- **location**, against the twelve hand-chosen spot-check reference points. Those are justified
  independently of this resolver and are not POI centroids, so the threshold is deliberately coarse:
  it separates "the same place" from "somewhere else entirely". I did not invent further reference
  coordinates from memory; that is a stated gap, and filling it needs an independent source.
- **property**: the outcome kind, the role of the leading candidate, whether a typed locality was
  matched, whether two spellings of one query agree. These encode the *rules* that keep breaking —
  a platform must not win over the place it is named after, a car park is not an airport, an
  ambiguous chain must stay ambiguous — and they are gradeable without knowing a coordinate.

Every assertion names the pass that motivated it, so a failure points at the regression it is
guarding rather than at an abstraction.

Run from v2/:  uv run python spikes/s2_resolver_benchmark.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ACCEPTED_PLACES, METRO, OSM_POIS, V2, append_results, stamp  # noqa: E402
from locfinder.places.resolve import build_metro_index, role_of  # noqa: E402

BENCHMARK = V2 / "benchmarks" / "resolver_queries.json"


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Equirectangular distance. Adequate at this scale for an 800 m threshold."""
    (lat1, lon1), (lat2, lon2) = a, b
    mlat = math.radians((lat1 + lat2) / 2.0)
    dx = math.radians(lon2 - lon1) * math.cos(mlat) * 6371008.8
    dy = math.radians(lat2 - lat1) * 6371008.8
    return math.hypot(dx, dy)


def grade(spec: dict, res, refs: dict, same_m: float, far_m: float,
          previous: dict) -> tuple[str, str]:
    """`(verdict, detail)`. Verdict is `pass`, `FAIL` or `ungraded`.

    `ungraded` is reserved for an assertion this benchmark cannot evaluate, never for a query whose
    answer is merely inconvenient.
    """
    want = spec["expect"]
    cands = list(res.candidates)
    lead = cands[0] if cands else None
    notes: list[str] = []

    if "outcome" in want:
        if res.outcome not in want["outcome"]:
            return "FAIL", f"outcome {res.outcome!r}, wanted one of {want['outcome']}"
        notes.append(f"outcome {res.outcome}")

    if "lead_role_not" in want:
        if lead is None:
            return "FAIL", "no candidate, so the leading role cannot be checked"
        r = role_of(lead.place.category)
        if r in want["lead_role_not"]:
            return "FAIL", (f"leader {lead.place.name!r} has role {r!r}, which is excluded "
                            f"({lead.place.category!r})")
        notes.append(f"lead role {r}")

    if "lead_role_in" in want:
        if lead is None:
            return "FAIL", "no candidate"
        r = role_of(lead.place.category)
        if r not in want["lead_role_in"]:
            return "FAIL", f"leader role {r!r} not in {want['lead_role_in']}"
        notes.append(f"lead role {r}")

    if want.get("locality_match"):
        if lead is None or not lead.locality_match:
            return "FAIL", "the typed locality did not rank the leading candidate"
        notes.append("locality matched")

    if "offered_near" in want:
        ref = refs[want["offered_near"]]
        near = [c for c in cands if metres((c.place.lat, c.place.lon), ref) <= same_m]
        if not near:
            best = min((metres((c.place.lat, c.place.lon), ref) for c in cands), default=None)
            return "FAIL", (f"nothing within {same_m:.0f} m of {want['offered_near']}"
                            + (f"; nearest candidate {best:.0f} m" if best else ""))
        notes.append(f"offered within {same_m:.0f} m")

    if "lead_near" in want:
        # The same candidate must satisfy location AND role. `offered_near` is satisfied by *any*
        # candidate, which let a bus platform 56 m from a hospital pass an assertion written to
        # exclude it, and let a Raleigh bus stop lead while a Durham one supplied the proximity
        # (Codex pass-13 and pass-14 M1).
        ref = refs[want["lead_near"]]
        if lead is None:
            return "FAIL", "no candidate"
        d = metres((lead.place.lat, lead.place.lon), ref)
        if d > same_m:
            return "FAIL", (f"the LEADER {lead.place.name!r} is {d:.0f} m from "
                            f"{want['lead_near']}, beyond {same_m:.0f} m")
        notes.append(f"leader within {d:.0f} m")

    if "offered_named_near" in want:
        # A *named* candidate must be near the reference. Plain `offered_near` is satisfied by any
        # candidate, which is how a bus platform 56 m from a hospital passed an assertion written to
        # exclude it (pass-13) — and plain `lead_name_contains` cannot be required of an
        # `ambiguous` outcome, whose contract is to *offer* the right place rather than to lead with
        # it. This pins both halves to one candidate without demanding it lead.
        spec_words = [w.lower() for w in want["offered_named_near"]["name_contains"]]
        ref = refs[want["offered_named_near"]["near"]]
        named = [c for c in cands if all(w in c.place.name.lower() for w in spec_words)]
        if not named:
            return "FAIL", f"no candidate whose name contains all of {spec_words}"
        best = min(metres((c.place.lat, c.place.lon), ref) for c in named)
        if best > same_m:
            return "FAIL", (f"the nearest candidate named {spec_words} is {best:.0f} m from "
                            f"{want['offered_named_near']['near']}, beyond {same_m:.0f} m")
        notes.append(f"a candidate named {spec_words} is {best:.0f} m away")

    if "lead_name_contains" in want:
        # Identity, not proximity. A dessert shop 731 m from the mall reference passed a 5 km
        # distance check for "Southpoint" without being the mall (pass-14 M1).
        need = [w.lower() for w in want["lead_name_contains"]]
        if lead is None:
            return "FAIL", "no candidate"
        got = lead.place.name.lower()
        if not all(w in got for w in need):
            return "FAIL", f"leader {lead.place.name!r} does not contain all of {need}"
        notes.append("leader name matches")

    if want.get("no_candidates"):
        if cands:
            return "FAIL", (f"{len(cands)} candidate(s) returned with outcome {res.outcome!r}; "
                            "a not-found answer must carry none")
        notes.append("no candidates, as required")

    if "min_corroborated" in want:
        # A merge tripwire on the real index: if a merge rule regresses, cross-source clusters come
        # apart and this count drops. Guards the rules the unit tests cover, on real data
        # (pass-14 M2).
        n = sum(1 for c in cands if c.corroborated_by)
        if n < want["min_corroborated"]:
            return "FAIL", (f"{n} corroborated candidate(s), expected at least "
                            f"{want['min_corroborated']} — a merge rule may have regressed")
        notes.append(f"{n} corroborated")

    if "not_far_from" in want:
        ref = refs[want["not_far_from"]]
        if lead is None:
            return "FAIL", "no candidate"
        d = metres((lead.place.lat, lead.place.lon), ref)
        if d > far_m:
            return "FAIL", f"leader is {d / 1000:.1f} km from {want['not_far_from']}"
        notes.append(f"leader {d:.0f} m away")

    if "not_confidently_far_from" in want:
        ref = refs[want["not_confidently_far_from"]]
        if res.outcome == "resolved" and lead is not None:
            d = metres((lead.place.lat, lead.place.lon), ref)
            if d > far_m:
                return "FAIL", (f"resolved CONFIDENTLY to {lead.place.name!r}, {d / 1000:.1f} km "
                                f"from {want['not_confidently_far_from']}")
            notes.append(f"confident, {d:.0f} m away")
        else:
            notes.append(f"{res.outcome}, so no confident claim was made")

    if want.get("non_reference_offered"):
        from locfinder.places.resolve import is_reference_feature
        if not any(not is_reference_feature(c.place) for c in cands):
            return "FAIL", "every candidate is a feature that merely refers to a place"
        notes.append("a real place is among the options")

    if "same_lead_as" in want:
        other = previous.get(want["same_lead_as"])
        if other is None:
            return "ungraded", f"{want['same_lead_as']!r} has not been run yet"
        a = lead.place.source_id if lead else None
        b = other[0].place.source_id if other else None
        if a != b:
            return "FAIL", f"leader {a} differs from {want['same_lead_as']!r}'s {b}"
        notes.append("same leader as its pair")

    return "pass", "; ".join(notes) or "no assertion"


def main() -> None:
    spec = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    refs = {k: (v[0], v[1]) for k, v in spec["references"].items()}
    same_m = float(spec["grading"]["same_place_m"])
    far_m = float(spec["grading"]["far_away_m"])

    idx = build_metro_index(gpd.read_parquet(ACCEPTED_PLACES), gpd.read_parquet(OSM_POIS),
                            bbox=METRO.routing)
    print(f"index: {len(idx):,} places, {len(idx.localities):,} localities", flush=True)

    previous: dict[str, list] = {}
    rows = []
    for q in spec["queries"]:
        res = idx.resolve(q["query"])
        previous[q["query"]] = list(res.candidates)
        verdict, detail = grade(q, res, refs, same_m, far_m, previous)
        rows.append({"query": q["query"], "intent": q["intent"], "outcome": res.outcome,
                     "n_matched": res.n_matched,
                     "lead": res.candidates[0].place.name if res.candidates else None,
                     "lead_category": res.candidates[0].place.category if res.candidates else None,
                     "verdict": verdict, "detail": detail, "basis": q["basis"]})
        mark = {"pass": "ok  ", "FAIL": "FAIL", "ungraded": "----"}[verdict]
        print(f"  {mark} {q['query']!r:42s} {res.outcome:<10s} "
              f"{(rows[-1]['lead'] or '-')[:34]:34s} {detail}", flush=True)

    graded = [r for r in rows if r["verdict"] != "ungraded"]
    passed = [r for r in graded if r["verdict"] == "pass"]
    print(f"\n{len(passed)} of {len(graded)} graded assertions pass "
          f"({len(rows) - len(graded)} ungraded)", flush=True)
    for r in graded:
        if r["verdict"] == "FAIL":
            print(f"  FAILED {r['query']!r}: {r['detail']}", flush=True)

    append_results("geocoding.md", render(rows, graded, passed, idx))
    print("\nappended to docs/experiments/geocoding.md", flush=True)


def render(rows, graded, passed, idx) -> str:
    lines = [f"### S2.1 expanded graded benchmark ({stamp()})", "",
             f"**{len(passed)} of {len(graded)} graded assertions pass.** "
             f"{len(rows)} queries, {len(rows) - len(graded)} ungraded. Index "
             f"{len(idx):,} places, {len(idx.localities):,} localities.", "",
             "Written because four consecutive Codex passes found over-corrections in "
             "`resolve.py`, each closing the reviewed case and breaking an adjacent one, and the "
             "five-query benchmark could not see them. Intended answers are recorded in "
             "`v2/benchmarks/resolver_queries.json` **before** the run. Location grading uses only "
             "the twelve independently justified spot-check reference points; everything else is a "
             "property assertion, because most of what keeps breaking is identity and confidence "
             "rather than position.", "",
             "| query | outcome | leading candidate | category | verdict | detail |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        v = {"pass": "pass", "FAIL": "**FAIL**", "ungraded": "*ungraded*"}[r["verdict"]]
        lines.append(f"| `{r['query']}` | {r['outcome']} | {r['lead'] or '—'} | "
                     f"{r['lead_category'] or '—'} | {v} | {r['detail']} |")
    fails = [r for r in graded if r["verdict"] == "FAIL"]
    if fails:
        lines += ["", "**Failures, with the assertion each one guards:**", ""]
        for r in fails:
            lines.append(f"- `{r['query']}` — {r['detail']}. *{r['basis']}*")
    else:
        lines += ["", "No graded assertion failed."]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
