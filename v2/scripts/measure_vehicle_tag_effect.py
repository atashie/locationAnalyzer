"""What the `vehicle` tag changes, now that it is extracted.

`access.classify_access` consults OSM's access hierarchy narrowest-first,
`access` < `vehicle` < `motor_vehicle` < `motorcar`, and `_MODE_TAG_ORDER` lists `vehicle` for the
drive and bike modes. `vehicle` was never in `EXTRA_WAY_TAGS` and is not in osmnx's default
`useful_tags_way`, so the extracted graph never carried it and that branch could not fire. Adding it
is therefore a defect fix, not a tuning choice -- and the size of the defect is a measurement, not
something to assert.

This counts, per mode, the edges whose access class changes when `vehicle` is consulted. The
counterfactual is produced by removing `vehicle` from `_MODE_TAG_ORDER`, which is exactly the
behaviour every layer built before 2026-11-10 had, rather than by deleting the tag from the graph:
the question is what the *rule* does with evidence it now has.

A second number matters more than the edge count. An edge whose class changes only matters if that
edge is reachable and used, so this also reports how many of the changed edges carry a `highway`
value the mode is allowed on at all -- an edge removed for drive that drive could never use is not
a change to any answer.

Run from v2/:  uv run python scripts/measure_vehicle_tag_effect.py
Writes data/vehicle_tag_effect.json.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spikes"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import DATA, load_roads_graph, stamp  # noqa: E402
from locfinder.traveltime import access  # noqa: E402
from locfinder.traveltime.speeds import highway_allowed  # noqa: E402

MODES = ("drive", "bike", "walk")


def main() -> None:
    t = time.perf_counter()
    G = load_roads_graph()
    print(f"graph loaded in {time.perf_counter() - t:.0f} s: "
          f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges", flush=True)

    with_vehicle = {m: tuple(keys) for m, keys in access._MODE_TAG_ORDER.items()}
    without = {m: tuple(k for k in keys if k != "vehicle") for m, keys in with_vehicle.items()}

    out: dict = {"built": stamp(), "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
                 "modes": {}}

    tagged = 0
    values: Counter = Counter()
    for _, _, d in G.edges(data=True):
        vals = access._values(d, "vehicle")
        if vals:
            tagged += 1
            values[",".join(sorted(vals))] += 1
    out["edges_tagged_vehicle"] = tagged
    out["vehicle_values"] = dict(values.most_common())
    print(f"edges carrying `vehicle`: {tagged}  {dict(values.most_common())}", flush=True)

    for mode in MODES:
        transitions: Counter = Counter()
        usable_transitions: Counter = Counter()
        for _, _, d in G.edges(data=True):
            if not access._values(d, "vehicle"):
                continue              # the tag is the only thing that can differ
            access._MODE_TAG_ORDER = without
            before = access.classify_access(d, mode)
            access._MODE_TAG_ORDER = with_vehicle
            after = access.classify_access(d, mode)
            if before == after:
                continue
            transitions[f"{before} -> {after}"] += 1
            if highway_allowed(d, mode):
                usable_transitions[f"{before} -> {after}"] += 1
        out["modes"][mode] = {
            "edges_changing_class": int(sum(transitions.values())),
            "transitions": dict(transitions.most_common()),
            "edges_changing_class_on_a_highway_this_mode_may_use": int(sum(usable_transitions.values())),
            "transitions_where_usable": dict(usable_transitions.most_common()),
        }
        print(f"{mode:>5}: {sum(transitions.values())} edges change class "
              f"({sum(usable_transitions.values())} of them on a highway this mode may use) "
              f"{dict(transitions.most_common())}", flush=True)

    assert access._MODE_TAG_ORDER == with_vehicle, "the counterfactual must be restored"
    path = DATA / "vehicle_tag_effect.json"
    path.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"\nwrote {path}", flush=True)


if __name__ == "__main__":
    main()
