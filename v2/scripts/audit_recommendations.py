"""S3 plan section 0, step 0: pick recommendations worth walking, and write the sheet to record them on.

Run from `v2/`:  `uv run python scripts/audit_recommendations.py grocery walk`

**Why this exists, and why it is first.** Codex pass 25 judged the S3 effort to be elaborating the
wrong axis: eleven adversarial passes went into the instrument, while the estimand carrying nearly
all of that rigour (E1) compares our pipeline to **our own engine**. E1 and E2 both draw their
destinations from the same list, so a grocery that closed last year passes both. Nothing built so
far can detect that the product is confidently wrong about the world, because nothing built so far
consults the world. A walked journey does, and only the owner can walk one. This script's whole job
is to make that cheap: a short list of journeys where being wrong would change a decision, and a
sheet with the product's answer already filled in and the owner's columns blank.

**What it does not know, which is the finding to carry forward.** The committed layer's
aggregation is `CATEGORY_COST_SELECTED` — **the travel time of the journey our cost model selected,
which is an upper bound, not the minimum time over qualifying destinations** (`status.py:210`; the
trap is recorded in `docs/engineering-notes/project-h2-upper-bound-trap.md` and this file walked
into it). The identity of the selected destination is not stored either. So the sheet cannot say
"we routed you to this grocery"; it can only ask which one the owner used. The audit therefore
establishes that *some* qualifying destination was open and reachable, never that *ours* was.
Recovering the selected destination needs one bounded graph load over the sampled cells, keeping the
POI-to-node association — the builder deduplicates destination nodes, so a node id alone can be
ambiguous. That is the decisive version of this audit, and it is not what step 0 built.

## The lower bound is reconstructed, and that is only safe under an assertion

`status.Surface` needs three arrays and only two are on disk: `seconds` and `reason`,
`min_possible_s` was not saved. Loading it properly means rebuilding from the 670 MB
`roads.graphml`, which costs minutes and would make the owner's loop slow enough to skip.

A caveat on all of it: **the stored seconds are float32**, and casting them to float64 here recovers
nothing. A model value of 600.00001 s is stored as 600.0 and so passes a 600 s threshold that the
model fails. This audit evaluates the *stored artifact*, which is the thing the product ships, and
that is the right object to audit — but it is not the model's own answer to the last bit.

The reconstruction is *seconds* where `OK`, *the horizon* where `BEYOND_HORIZON` (which
`Surface.validate` requires exactly and which `evaluate` reads from `horizon_s` anyway), and **`0`
where `OFF_NETWORK`**.

**The `0` is sound but lossy, and an earlier version of this file claimed it was exact. It is not.**
A cell is `OFF_NETWORK` precisely *because* `snapped.access_m > max_access_m`
(`traveltime/snap.py:265`), so **200 m is the floor of the OFF_NETWORK access distances, not their
ceiling** — the real bound `access_m / max_speed_mps` is therefore always *above* 143 s and has no
upper limit at all. Codex pass 26 built a two-node graph with origins 201 m, 1 km and 2 km
off-network and measured real bounds of 143.6 s, 714.3 s and 1,428.6 s; at a 600 s threshold the
real surface says UNKNOWN, FAIL, FAIL where the reconstruction says UNKNOWN three times.

What the reconstruction guarantees over the whole surface is therefore one-sided: `0` never exceeds
the real bound, so it **can never manufacture an exclusion**. The error is only ever `UNKNOWN` where
the pipeline would say `FAIL` — it loses information and never invents it. For a product that must
not wrongly rule a household out, that is the right direction, and it is all that is claimed.

**For the rows this script emits it is exact**, by a bound the selection supplies rather than the
format: every emitted `OFF_NETWORK` row is adjacent to an `OK` cell, whose own access is at most
`max_access_m`, so the emitted cell's centre lies within `cell_m * sqrt(2)` of that cell's centre
and its own access is at most `max_access_m + cell_m * sqrt(2)` — 341.4 m here, a bound of 243.9 s,
well under the 600 s threshold. That is the condition the script checks, and it re-asserts the
adjacency on every emitted row rather than trusting the stratum definition to have held.

The other refusal is `reason.max() <= Reason.BEYOND_HORIZON`. **It is a fail-fast with a legible
message, not a correctness barrier** — an earlier version of this file claimed a `NO_PATH` cell
would "silently read as `UNKNOWN`", and that is false twice over: `Surface.validate` rejects a
`NO_PATH` cell whose bound is not `+inf` (`status.py:325`), and `evaluate` fails `NO_PATH`
unconditionally regardless of its bound (`status.py:380`). The guard earns its place by failing
where the cause is readable instead of as an invariant error three frames later.

When a layer is rebuilt with `min_possible_s` saved beside it, that file is preferred and neither
refusal applies. The builder now writes it.

## The sheet uses no footprint geometry

Journeys are restricted to cells containing at least one building, from the already-admitted count
raster `own_<metro>_buildings_per_cell.npy` — a cell with no structure has no door to walk from, so
it is unwalkable whatever its travel time says. The *individual* Overture footprints are not read.
`data/<metro>/overture_buildings_report.json` records their admitted use as "rasterised to counts,
never republished", and this sheet is committed to the repository; putting a building coordinate per row
into it would be a wider use than the one recorded, for a convenience the owner does not need. The
owner picks a real starting point inside the cell and records it, and the centre-to-door offset the
product must answer for is bounded in advance at `cell_m * sqrt(2) / 2`.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

from locfinder import profile
from locfinder.grid import NODATA, GridSpec, encode_minutes
from locfinder.measure.frames import file_digest
from locfinder.metros import get_metro
from locfinder.status import (CATEGORY_COST_SELECTED, Criterion, Outcome, Reason, Surface,
                              evaluate)
from locfinder.traveltime.speeds import access_speed_mps, max_speed_mps

REPO = Path(__file__).resolve().parents[2]
V2 = REPO / "v2"

#: The horizon and access rule the committed layers were built to, used only when the layer carries
#: no sidecar of its own. Both are **assumptions about someone else's build**, which is the shape of
#: error this stage exists to catch, so neither is trusted silently:
#:
#: * `Surface.validate` only checks `max finite <= horizon`, so assuming a horizon *larger* than the
#:   build's passes silently — measured: a 60-minute layer read as 120 minutes raises nothing.
#:   `corroborate_horizon` only makes that *implausible*, never impossible: it is a heuristic. The
#:   builder now writes the sidecar, which is the actual fix, and `--horizon-min` is the escape.
#: * `MAX_ACCESS_M` enters the exactness check for the emitted rows. Rather than depend on it being
#:   exactly right, the check is restated as the widest build it tolerates:
#:   `max_access_m <= min(threshold) * max_speed_mps - cell_m * sqrt(2)` — **698.6 m** for a
#:   10-minute walk on a 100 m grid, a **3.49x** margin on the 200 m this project uses. An earlier
#:   version of this comment said 840 m and 4.2x, which omits the cell diagonal that the whole
#:   adjacency argument rests on (Codex pass 27).
CUTOFF_MIN = 120.0
MAX_ACCESS_M = 200.0

#: A **heuristic** scale for the gap between a claimed horizon and the largest finite time, used
#: only to catch a grossly wrong assumed horizon. It is not a proof and the first version of it
#: was a false refusal: a flat 60 s rejected a legitimate `build_layer_surface` output whose
#: frontier happened to fall 64.3 s short of the horizon (Codex pass 27, on a straight 11 km edge
#: with cells at 9,990 m and 10,090 m). There is **no sound upper bound** on that gap — the frontier
#: can be arbitrarily sparse — so the scale is derived from the largest per-cell contribution that
#: is not network distance, `(max_access_m + cell_m) / access_speed_mps`, which is 238 s for a
#: 100 m walk grid. A 60-minute layer read as 120 leaves a gap of 3,600 s and is still caught;
#: pass 27's 64.3 s is not. Anything that needs certainty passes `--horizon-min` or rebuilds the
#: sidecar.
def horizon_gap_scale_s(mode: str, cell_m: float) -> float:
    return (MAX_ACCESS_M + cell_m) / access_speed_mps(mode)

#: Journeys are drawn from seven strata: a near-threshold pair per threshold, the cells where the
#: product declines to answer next door to a pass, and two deep controls so a systematic offset
#: shows up as a shifted control rather than being inferred from the bands.
#:
#: **Each band is split by the answer the product gives**, not left symmetric about the threshold.
#: An unsplit band drew six journeys that all happened to sit above 15 minutes, so every row asked
#: the same question and the audit could not have seen which direction an offset ran. The split also
#: separates the two error costs: a displayed PASS that fails when walked is the one a household is
#: harmed by, and it is the numerator of the conditional pass 25 found missing.
BAND_S = 90.0

#: Controls are defined by their **margin** past a threshold, not by an absolute time. The first
#: version asked for cells at least 1,800 s out and drew three journeys of 108, 50 and 56 minutes
#: one way — 3.57 hours of the sheet's 6.22, to confirm that a place an hour and three quarters from
#: a grocery is indeed more than fifteen minutes from one. A margin of five minutes past a
#: fifteen-minute threshold is already ten to twenty times any offset the bands could plausibly
#: reveal, and it is walkable.
CONTROL_MARGIN_S = 300.0

#: Per-stratum caps on the draw, applied under `--per-stratum`. The deep FAIL control is the
#: lowest-information stratum per hour walked: it is the longest journey on the sheet by
#: construction, and a thirty-second systematic offset would leave it comfortably failing either
#: way. One is enough to notice a gross error; three is three times the walking for the same claim.
STRATUM_DRAW_CAP = {"deep_fail_control": 1}

#: No row may ask for a walk longer than this. The predicted seconds *are* the walking time, which
#: the first version of this script did not account for anywhere.
DEFAULT_MAX_WALK_MIN = 25.0

#: Columns the owner fills in while walking. Blank in every emitted row.
#:
#: There is no single `agrees` column, and the first version's was a mistake: it conflated
#: destination validity, route validity, time error, which threshold was being tested, and the
#: strength of the available evidence. Four counterexamples, all of which a lone `agrees` records
#: identically (Codex pass 26):
#:
#: * the product picked a closed shop at 8 minutes; the owner walks 9 minutes to a different open
#:   one and records agreement — the stale destination goes undetected;
#: * the product says PASS; the owner walks 18 minutes to a *preferred* supermarket, ignoring a
#:   qualifying shop at 8 minutes, and records disagreement — which refutes nothing;
#: * the product says FAIL; one 18-minute walk does not establish that *every* qualifying grocery
#:   exceeds fifteen minutes;
#: * the product says UNKNOWN, which is an admission; no walk confirms or refutes it.
#:
#: So the observations are recorded separately and the finding is derived. The asymmetry is the
#: point: the product's claim is **existential** — "some qualifying destination within T" — so a
#: qualifying walk inside T is a **witness** that settles the cell, while a slow walk is evidence
#: about one destination and never a proof of universal absence.
OWNER_COLUMNS = [
    "walked_date",
    "start_lon",
    "start_lat",
    "door_offset_m",
    "destination_used",
    "destination_qualifies",     # yes / no  - is it a grocery by our own category rule?
    "destination_open",          # yes / no  - open, in business and usable on arrival
    "route_usable",              # yes / no  - no locked gate, fence, missing crossing
    "walked_seconds",
    "witness_within_10min",      # yes / no / untested - a qualifying walk inside 10 min
    "witness_within_15min",
    "unresolved",                # what this walk could not settle
    "notes",
]


#: Where the committed layers live. A parameter rather than a constant so the refusal paths below
#: can be exercised against a fabricated layer: an assertion that has never been seen to fire has
#: not been shown to protect anything (pass-19 F5).
LAYERS = V2 / "data" / "layers"


def layer_path(kind: str, category: str, mode: str, suffix: str, metro: str,
               layers: Path = LAYERS) -> Path:
    """Mirrors `spikes/_common.layer_path`, kept local so `scripts/` does not import from
    `spikes/`. The metro name is in the filename unless it is the Phase 0 slice."""
    stem = f"{kind}_{category}_{mode}" if metro == "slice" else f"{kind}_{metro}_{category}_{mode}"
    return layers / f"{stem}{suffix}"


class Refused(SystemExit):
    """Raised instead of producing a sheet whose answers cannot be trusted."""


def _rel(p: Path) -> str:
    """Repo-relative, forward-slashed, so the provenance record reads the same on either machine.
    Absolute for a path outside the tree, as in a test or an explicit `--out`."""
    try:
        return p.relative_to(REPO).as_posix()
    except ValueError:
        return str(p)


def read_sidecar(path: Path) -> dict | None:
    """Build parameters recorded beside the layer, if the build that wrote it recorded them."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def corroborate_horizon(seconds: np.ndarray, reason: np.ndarray, horizon_s: float, *,
                        mode: str, cell_m: float) -> dict:
    """Sanity-check an *assumed* horizon against the arrays. **A heuristic, not a proof.**

    The arrays can **falsify** a horizon claim and cannot **verify** one: `max finite <= horizon` is
    required, but nothing in them rules out a larger horizon than the build used. The gap below the
    horizon is weak evidence in the same direction and nothing more — a sparse frontier leaves a
    real gap, which is why a flat 60 s threshold here rejected a legitimate build. The scale is
    `horizon_gap_scale_s` and the result says it is a heuristic, so no caller can read `plausible`
    as provenance.
    """
    finite = np.isfinite(seconds)
    max_finite = float(seconds[finite].max()) if finite.any() else float("nan")
    cut_off = int((reason == Reason.BEYOND_HORIZON).sum())
    gap = horizon_s - max_finite if finite.any() else float("inf")
    scale = horizon_gap_scale_s(mode, cell_m)
    plausible = (not cut_off) or (0.0 <= gap <= scale)
    return {
        "max_finite_s": None if not finite.any() else round(max_finite, 3),
        "gap_to_horizon_s": None if not finite.any() else round(gap, 6),
        "gap_scale_s": round(scale, 1),
        "cells_cut_off": cut_off,
        "plausible": bool(plausible),
        "is_a_heuristic": True,
        "basis": ("the gap below a horizon that visibly bound is weak evidence the horizon is "
                  "right; the arrays can falsify a horizon claim and cannot verify one, and a "
                  "sparse frontier leaves a real gap, so this is not provenance"),
    }


def load_surface(
    grid: GridSpec, *, category: str, mode: str, metro: str, thresholds_s: tuple[float, ...],
    layers: Path = LAYERS, declared_horizon_s: float | None = None,
) -> tuple[Surface, dict]:
    """The committed layer as a validated `Surface`, with the provenance of every array.

    Refuses rather than guessing when the reconstruction described in the module docstring is not
    justified for the artifact actually on disk.
    """
    sec_path = layer_path("own", category, mode, ".npy", metro, layers)
    reason_path = layer_path("own", category, mode, "_reason.npy", metro, layers)
    bound_path = layer_path("own", category, mode, "_min_possible_s.npy", metro, layers)
    for p in (sec_path, reason_path):
        if not p.exists():
            raise Refused(f"missing layer artifact {p}\nbuild it with: "
                          f"uv run python spikes/s2_building_weighted_coverage.py {category} {mode}")

    seconds = np.load(sec_path).astype(np.float64)
    reason = np.load(reason_path)
    if seconds.shape != (grid.nrows, grid.ncols):
        raise Refused(f"{sec_path.name} is {seconds.shape}, grid is {(grid.nrows, grid.ncols)}")
    if reason.shape != seconds.shape:
        raise Refused(f"{reason_path.name} is {reason.shape}, seconds are {seconds.shape}")

    sidecar = read_sidecar(layer_path("own", category, mode, "_build.json", metro, layers))
    if sidecar:
        horizon_s = float(sidecar["horizon_s"])
        max_access_m = float(sidecar["max_access_m"])
        build = {"origin": "sidecar", "horizon_s": horizon_s, "max_access_m": max_access_m}
        # The sidecar binds the arrays into one build only to the extent that it records their
        # digests; without them it is a note about parameters, not provenance.
        recorded = sidecar.get("arrays") or {}
        checked = {}
        for name, path in (("seconds", sec_path), ("reason", reason_path)):
            want = recorded.get(name)
            if want:
                got = file_digest(path)
                if got != want:
                    raise Refused(
                        f"{path.name} does not match the digest its build sidecar recorded "
                        f"({got[:12]}... vs {want[:12]}...), so the two were not written by the "
                        "same run. Rebuild every array and the sidecar together: uv run python "
                        f"spikes/s2_building_weighted_coverage.py {category} {mode}")
                checked[name] = "digest matched"
            else:
                checked[name] = "no digest recorded; parameters only, not provenance"
        build["arrays"] = checked
    elif declared_horizon_s is not None:
        horizon_s = float(declared_horizon_s)
        max_access_m = MAX_ACCESS_M
        build = {"origin": "declared by the operator", "horizon_s": horizon_s,
                 "max_access_m": max_access_m,
                 "note": "--horizon-min was passed; no heuristic was applied"}
    else:
        horizon_s = CUTOFF_MIN * 60.0
        max_access_m = MAX_ACCESS_M
        build = {"origin": "assumed", "horizon_s": horizon_s, "max_access_m": max_access_m,
                 "assumed_from": "the constants in spikes/s2_building_weighted_coverage.py",
                 "horizon": corroborate_horizon(seconds, reason, horizon_s, mode=mode,
                                                cell_m=grid.cell_m)}
        if not build["horizon"]["plausible"]:
            raise Refused(
                f"the assumed horizon of {horizon_s:g}s looks wrong for {sec_path.name}: "
                f"{build['horizon']['cells_cut_off']:,} cells were cut off by a horizon, yet the "
                f"largest finite time is {build['horizon']['gap_to_horizon_s']:g}s below it, "
                f"against a gap scale of {build['horizon']['gap_scale_s']:g}s. **This is a "
                f"heuristic, not a proof** -- a sparse frontier can leave a real gap. If the "
                f"horizon really is {horizon_s:g}s, pass --horizon-min {horizon_s / 60:g} to "
                f"declare it; otherwise rebuild, which writes the parameters and digests beside "
                f"the layer."
            )
    prov = {
        "build": build,
        "seconds": {"path": _rel(sec_path), "sha256": file_digest(sec_path)},
        "reason": {"path": _rel(reason_path), "sha256": file_digest(reason_path)},
        "reason_max": int(reason.max()),
        "reason_max_name": Reason(int(reason.max())).name,
    }

    if bound_path.exists():
        min_possible = np.load(bound_path).astype(np.float64)
        if min_possible.shape != seconds.shape:
            raise Refused(f"{bound_path.name} is {min_possible.shape}, seconds are {seconds.shape}")
        prov["min_possible_s"] = {
            "origin": "stored",
            "path": _rel(bound_path),
            "sha256": file_digest(bound_path),
        }
    else:
        # Refusal 1, a fail-fast rather than a correctness barrier: `Surface.validate` would reject
        # a NO_PATH cell carrying a 0 bound and `evaluate` fails NO_PATH whatever its bound, so
        # nothing is silently wrong without this -- it just fails somewhere less legible.
        if int(reason.max()) > int(Reason.BEYOND_HORIZON):
            raise Refused(
                f"{reason_path.name} contains {Reason(int(reason.max())).name}, which this "
                "reconstruction does not cover. For NO_PATH the real bound is +inf and "
                "Surface.validate rejects a 0; for a layer-wide reason the bound really is 0, but "
                "then every cell is unknown and the layer must not be published at all (S4.4).\n"
                "Rebuild the surface with "
                "locfinder.traveltime.layer.build_layer_surface, which computes the real bound, and "
                "save it beside the layer:\n  uv run python "
                f"spikes/s2_building_weighted_coverage.py {category} {mode}"
            )
        # Refusal 2. The 0 bound is sound everywhere and lossy where the real bound exceeds the
        # threshold -- it can only turn a FAIL into an UNKNOWN, never produce an exclusion. What
        # makes it *exact* is a property of the selection, not of the surface: an OFF_NETWORK cell
        # adjacent to an OK cell has access at most `max_access_m + cell_m * sqrt(2)`, because the
        # OK neighbour's own access is at most `max_access_m` and the two centres are at most one
        # cell diagonal apart. Only such cells are emitted, and `main` re-asserts the adjacency per
        # row. 200 m is the FLOOR of the OFF_NETWORK distances (`snap.py:265`), so a check against
        # `max_access_m` alone -- which this script used to make -- bounds nothing.
        adjacent_access_m = max_access_m + grid.cell_m * math.sqrt(2.0)
        adjacent_bound_s = adjacent_access_m / max_speed_mps(mode)
        if adjacent_bound_s > min(thresholds_s):
            raise Refused(
                f"the reconstructed OFF_NETWORK bound (0) is not exact even for cells adjacent to "
                f"an OK cell: their access reaches {adjacent_access_m:.1f}m "
                f"({max_access_m:g}m + one {grid.cell_m:g}m diagonal), a real bound of "
                f"{adjacent_bound_s:.1f}s, past the smallest threshold of "
                f"{min(thresholds_s):.0f}s. Such a cell would be reported UNKNOWN where the "
                "pipeline proves FAIL. Rebuild with the real bound, or raise the threshold."
            )
        min_possible = np.where(reason == Reason.OK, seconds, 0.0)
        min_possible = np.where(reason == Reason.BEYOND_HORIZON, horizon_s, min_possible)
        prov["min_possible_s"] = {
            "origin": "reconstructed",
            "rule": "seconds where OK, horizon_s where BEYOND_HORIZON, 0 where OFF_NETWORK",
            "soundness": ("0 never exceeds the real bound, so the reconstruction can only report "
                          "UNKNOWN where the pipeline proves FAIL; it can never manufacture an "
                          "exclusion. It is NOT outcome-identical over the surface: OFF_NETWORK "
                          "access is >= max_access_m, so the real bound is unbounded above"),
            "exact_for_emitted_rows": {
                "why": ("only OFF_NETWORK cells adjacent to an OK cell are emitted, and adjacency "
                        "bounds their access by max_access_m + one cell diagonal"),
                "adjacent_access_max_m": round(adjacent_access_m, 1),
                "adjacent_bound_max_s": round(adjacent_bound_s, 1),
                "smallest_threshold_s": min(thresholds_s),
                "max_access_m": max_access_m,
                "max_speed_mps": max_speed_mps(mode),
            },
        }

    # `validate` is a partial cross-check between the two files, which were written by separate
    # runs 43 minutes apart. It requires a finite time exactly where the reason is OK, which catches
    # the common mismatch -- but it establishes particular invariants, NOT shared provenance: two
    # builds with the same OK mask and different times both pass, as does swapping OFF_NETWORK for
    # BEYOND_HORIZON among the infinite cells, and a matching shape does not establish a matching
    # grid origin. Only the build sidecar can bind the files into one build.
    surf = Surface(
        mode=mode,
        engine="own-graph",
        target=category,
        aggregation=CATEGORY_COST_SELECTED,
        horizon_s=horizon_s,
        seconds=seconds,
        reason=reason,
        min_possible_s=min_possible,
    )
    try:
        surf = surf.validate()
    except ValueError as e:
        raise Refused(
            f"{sec_path.name} and {reason_path.name} violate a Surface invariant together: {e}. "
            f"They were written by separate runs, so rebuilding one without the other leaves them "
            f"inconsistent. Rebuild every array and the sidecar in one run: uv run python "
            f"spikes/s2_building_weighted_coverage.py {category} {mode}"
        ) from e
    return surf, prov


def strata(
    surf: Surface, outcomes: dict[int, np.ndarray], *, thresholds_min: tuple[int, ...]
) -> dict[str, np.ndarray]:
    """The seven candidate pools, as boolean masks over the grid."""
    seconds, reason = surf.seconds, surf.reason
    ok = reason == Reason.OK
    off = reason == Reason.OFF_NETWORK
    neighbourhood = np.ones((3, 3), dtype=bool)
    tightest, loosest = min(thresholds_min), max(thresholds_min)

    out: dict[str, np.ndarray] = {}
    for t_min in thresholds_min:
        # Within +/- 90 s of a threshold: the band where our rounding, our speed model and the
        # centre-to-door offset can each flip the answer a household acts on. Split by the side of
        # the threshold, which is the side of the *answer*: `_pass` holds cells the product shows
        # as passing, `_fail` cells it shows as failing.
        t = t_min * 60.0
        band = ok & (np.abs(seconds - t) <= BAND_S)
        out[f"band{t_min}min_pass"] = band & (seconds <= t)
        out[f"band{t_min}min_fail"] = band & (seconds > t)

    # The product declines to answer immediately next door to a cell that **passes**. Either the
    # access rule is too strict or the graph is missing a path people use; the two look identical
    # from the layer, and a walk can separate them.
    #
    # This dilated `ok` rather than PASS until Codex pass 26: 24,468 cells qualified, 633 of them
    # with a building, and the three drawn had nearest answering neighbours at 3,615 s, 4,783 s and
    # 4,293 s -- an hour from a grocery, not beside a pass at all. Dilating the PASS mask at the
    # loosest threshold gives 1,081 cells, 77 with a building. Far fewer, and the right ones.
    passing = outcomes[loosest] == Outcome.PASS
    out[f"off_network_beside_pass{loosest}min"] = off & ndimage.binary_dilation(
        passing, structure=neighbourhood)

    # Controls, so a systematic offset shows up as a shifted control rather than being inferred
    # from the bands. `binary_erosion` keeps only cells whose whole 3x3 neighbourhood agrees, so a
    # control is not a near-boundary cell that happens to be deep in seconds.
    #
    # The margin is what makes a control a control, and it is bounded on both sides: at least
    # CONTROL_MARGIN_S clear of the threshold, so no plausible offset could move it, and no further
    # than the walk cap, because the predicted seconds are the time the owner must spend.
    pass_everywhere = ndimage.binary_erosion(
        outcomes[tightest] == Outcome.PASS, structure=neighbourhood, border_value=0)
    fail_everywhere = ndimage.binary_erosion(
        outcomes[loosest] == Outcome.FAIL, structure=neighbourhood, border_value=0)
    out["deep_pass_control"] = (
        ok & (seconds <= tightest * 60.0 - CONTROL_MARGIN_S) & pass_everywhere)
    out["deep_fail_control"] = (
        ok & (seconds >= loosest * 60.0 + CONTROL_MARGIN_S) & fail_everywhere)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("category")
    ap.add_argument("mode", choices=["walk", "bike", "drive"])
    ap.add_argument("--thresholds-min", type=int, nargs="+", default=[10, 15],
                    help="criterion thresholds in minutes (default: 10 15)")
    ap.add_argument("--per-stratum", type=int, default=3,
                    help="journeys drawn from each of the seven strata (default: 3, so 21 "
                         "journeys, the scale pass 25 suggested for 3-6 household person-hours)")
    ap.add_argument("--min-buildings", type=int, default=1,
                    help="skip cells with fewer buildings; 0 disables the filter (default: 1)")
    ap.add_argument("--max-walk-min", type=float, default=DEFAULT_MAX_WALK_MIN,
                    help=f"skip journeys whose predicted one-way time exceeds this, because the "
                         f"predicted seconds are the time the owner must spend (default: "
                         f"{DEFAULT_MAX_WALK_MIN:g}). 0 removes the cap")
    # Two floats rather than one "LON,LAT" string: every longitude here starts with a minus sign,
    # and argparse reads `--near -79.05,35.91` as an unknown option. It accepts a bare negative
    # *number*, so `--near -79.05 35.91` -- the form anyone would type -- works.
    ap.add_argument("--near", nargs=2, type=float, metavar=("LON", "LAT"),
                    help="restrict to journeys within --radius-km of this point, so the sheet is "
                         "walkable in one outing instead of scattered over the metro")
    ap.add_argument("--radius-km", type=float, default=5.0)
    ap.add_argument("--horizon-min", type=float,
                    help="declare the horizon the layer was built to, in minutes. Authoritative: "
                         "it skips the plausibility heuristic, which is a heuristic and can refuse "
                         "a legitimate build whose frontier is sparse")
    ap.add_argument("--seed", type=int, default=20261109)
    ap.add_argument("--out", type=Path,
                    help="output CSV (default: docs/experiments/audit/<metro>-<cat>-<mode>.csv)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing sheet. Without this the script refuses, because "
                         "the sheet is meant to be filled in by hand and a rerun would erase it")
    args = ap.parse_args()

    metro = get_metro()
    grid = metro.grid()
    thresholds_min = tuple(sorted(set(args.thresholds_min)))
    thresholds_s = tuple(float(t) * 60.0 for t in thresholds_min)
    if not thresholds_min:
        raise Refused("at least one threshold is needed")

    t0 = time.perf_counter()
    surf, prov = load_surface(
        grid, category=args.category, mode=args.mode, metro=metro.name,
        thresholds_s=thresholds_s,
        declared_horizon_s=None if args.horizon_min is None else args.horizon_min * 60.0)
    outcomes = {
        t_min: evaluate(
            Criterion(label=f"{args.category} within {t_min} min", mode=args.mode,
                      target=args.category, kind="category", threshold_s=t_min * 60.0),
            surf,
        )
        for t_min in thresholds_min
    }
    pools = strata(surf, outcomes, thresholds_min=thresholds_min)

    eligible = np.ones(surf.shape, dtype=bool)
    notes: dict = {}
    distance_km = None
    if args.max_walk_min > 0:
        # The first version of this sheet asked for 6.22 hours of one-way walking across 18 rows,
        # 3.57 of them in three "controls" of 108, 50 and 56 minutes.
        #
        # A cell with no finite prediction is deliberately kept, and is therefore **not capped and
        # not in the budget**: an OFF_NETWORK cell has no predicted time to cap by. Adjacency to a
        # PASS bounds its distance to the *indexed network* and says nothing about how long the
        # walk is -- the whole reason to walk it is that we do not know.
        cap_s = args.max_walk_min * 60.0
        eligible &= ~(np.isfinite(surf.seconds) & (surf.seconds > cap_s))
        notes["max_walk_min"] = args.max_walk_min
    if args.min_buildings > 0:
        bpath = V2 / "data" / "layers" / f"own_{metro.name}_buildings_per_cell.npy"
        if not bpath.exists():
            raise Refused(f"missing {bpath}; pass --min-buildings 0 to select without it")
        counts = np.load(bpath)
        if counts.shape != surf.shape:
            raise Refused(f"{bpath.name} is {counts.shape}, grid is {surf.shape}")
        eligible &= counts >= args.min_buildings
        notes["buildings"] = {
            "path": str(bpath.relative_to(REPO)), "sha256": file_digest(bpath),
            "min_buildings": args.min_buildings,
            "licence_use": "count raster only; individual footprints are not read or republished",
        }
    else:
        counts = np.zeros(surf.shape, dtype=np.int64)

    # Before the --near mask, so an emptied stratum can report its nearest member under the same
    # building and walk-cap filters. Reconstructing this as `eligible | ~within` was wrong: outside
    # the radius that expression is true whatever the other filters say, and it reported a cell with
    # no building in it as the nearest walkable one.
    eligible_without_near = eligible.copy()
    if args.near:
        lon, lat = args.near
        try:
            here = grid.cell_for_lonlat(lon, lat)
        except ValueError as e:
            # Not merely outside: a point that does not project into this UTM zone at all, which
            # `cell_for_lonlat` refuses to report as an ordinary "outside the grid".
            raise Refused(f"--near {lon} {lat}: {e}") from e
        if here is None:
            raise Refused(f"--near {lon} {lat} is outside the {metro.name} grid")
        xs, ys = grid.cell_centers_xy()
        from pyproj import Transformer
        x0, y0 = Transformer.from_crs("EPSG:4326", grid.crs, always_xy=True).transform(lon, lat)
        distance_km = np.hypot(xs - x0, ys - y0) / 1000.0
        within = distance_km <= args.radius_km
        eligible &= within
        notes["near"] = {"lon": lon, "lat": lat, "cell": list(here),
                         "radius_km": args.radius_km, "cells_within": int(within.sum())}

    lons, lats = grid.cell_centers_lonlat()
    lons_all, lats_all = lons, lats
    minutes = encode_minutes(surf.seconds)
    # The reconstructed OFF_NETWORK bound is exact only for a cell adjacent to an OK cell, so the
    # adjacency is re-checked per emitted row rather than inferred from the stratum it came from.
    beside_ok = ndimage.binary_dilation(surf.reason == Reason.OK, structure=np.ones((3, 3), bool))
    rng = np.random.default_rng(args.seed)
    door_bound_m = grid.cell_m * math.sqrt(2.0) / 2.0

    rows: list[dict] = []
    census: dict = {}
    for name, pool in pools.items():
        available = pool & eligible
        flat = np.flatnonzero(available)
        take = min(args.per_stratum, STRATUM_DRAW_CAP.get(name, args.per_stratum), flat.size)
        picked = rng.choice(flat, size=take, replace=False) if take else np.empty(0, dtype=int)
        census[name] = {"in_stratum": int(pool.sum()), "eligible": int(flat.size),
                        "drawn": int(take)}
        # A stratum emptied by `--near` is not the same as a stratum that does not exist, and the
        # difference decides what the owner should do about it. `off_network_beside_pass15min` has
        # 77 walkable cells in the whole metro and none within 5 km of Chapel Hill, which is a fact
        # about a well-connected town rather than a missing question -- but the owner can only act
        # on it if told where the nearest one is.
        if take == 0 and distance_km is not None:
            reachable = pool & eligible_without_near
            if reachable.any():
                k = int(np.argmin(np.where(reachable, distance_km, np.inf)))
                row, col = divmod(k, grid.ncols)
                census[name]["nearest_outside_radius"] = {
                    "km": round(float(distance_km[row, col]), 1),
                    "cell": [row, col],
                    "lat": round(float(lats_all[row, col]), 5),
                    "lon": round(float(lons_all[row, col]), 5),
                }
        for n, flat_idx in enumerate(sorted(picked.tolist()), start=1):
            row, col = divmod(int(flat_idx), grid.ncols)
            lon, lat = float(lons[row, col]), float(lats[row, col])
            # The new helper, used as a guard on every emitted row: the coordinate we hand the
            # owner must land back in the cell whose answer we printed beside it.
            back = grid.cell_for_lonlat(lon, lat)
            if back != (row, col):
                raise Refused(f"cell ({row}, {col}) centre round-tripped to {back}")
            sec = float(surf.seconds[row, col])
            enc = int(minutes[row, col])
            if (surf.reason[row, col] == Reason.OFF_NETWORK
                    and prov["min_possible_s"]["origin"] == "reconstructed"
                    and not beside_ok[row, col]):
                raise Refused(
                    f"cell ({row}, {col}) is OFF_NETWORK and not adjacent to any OK cell, so its "
                    "reconstructed bound of 0 is not exact: the pipeline might prove FAIL where "
                    "this sheet would print UNKNOWN. Only adjacency bounds the access distance "
                    "(200 m is its floor, not its ceiling)."
                )
            rec = {
                "journey_id": f"{name}-{n:02d}",
                "stratum": name,
                "row": row,
                "col": col,
                "query_lon": f"{lon:.6f}",
                "query_lat": f"{lat:.6f}",
                "osm_link": f"https://www.openstreetmap.org/#map=18/{lat:.5f}/{lon:.5f}",
                "buildings_in_cell": int(counts[row, col]),
                "door_offset_max_m": f"{door_bound_m:.1f}",
                "seconds": f"{sec:.1f}" if math.isfinite(sec) else "",
                "reason": Reason(int(surf.reason[row, col])).name,
                "encoded_minutes": "" if enc == NODATA else enc,
            }
            disagrees = []
            for t_min in thresholds_min:
                rec[f"outcome_{t_min}min"] = Outcome(int(outcomes[t_min][row, col])).name
                # What a client deciding from the encoded whole minute would say. `encode_minutes`
                # rounds to nearest, so `minute <= t` holds whenever `seconds < 60t + 30`: the
                # encoded artifact answers a threshold 30 s more permissive than the float surface,
                # in that direction only. Measured over the Triangle, 8.15% of the cells a
                # minute-only client shows as passing 10 minutes do not pass it. Which verdict the
                # product actually shows is S3.5's decision (plan §0 step 6), so the sheet names
                # the rows where the two differ instead of quietly picking one.
                if enc != NODATA and (enc <= t_min) != (Outcome(int(outcomes[t_min][row, col]))
                                                        is Outcome.PASS):
                    disagrees.append(str(t_min))
            rec["encoding_disagrees_min"] = " ".join(disagrees)
            rec.update({c: "" for c in OWNER_COLUMNS})
            rows.append(rec)

    out_path = args.out or (REPO / "docs" / "experiments" / "audit" /
                            f"{metro.name}-{args.category}-{args.mode}.csv")
    if out_path.exists() and not args.force:
        raise Refused(f"{out_path} exists. It is meant to be filled in by hand, so a rerun would "
                      "erase the walked results; pass --force to overwrite deliberately.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    walk_min = [float(r["seconds"]) / 60.0 for r in rows if r["seconds"]]
    meta = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "v2/scripts/audit_recommendations.py",
        "purpose": "S3 plan section 0 step 0: journeys for the owner-gated walked audit",
        "metro": metro.name,
        "category": args.category,
        "mode": args.mode,
        "thresholds_min": list(thresholds_min),
        "seed": args.seed,
        "per_stratum": args.per_stratum,
        "journeys": len(rows),
        "grid": {"cell_m": grid.cell_m, "nrows": grid.nrows, "ncols": grid.ncols,
                 "crs": grid.crs, "version": profile.grid_version(grid)},
        "profile_version": profile.profile_version(),
        "layer": prov,
        "selection": {"strata": census, **notes},
        "door_offset_max_m": round(door_bound_m, 2),
        "band_s": BAND_S,
        "control_margin_s": CONTROL_MARGIN_S,
        "max_walk_min": args.max_walk_min,
        "predicted_walk": {
            "rows_with_a_finite_time": len(walk_min),
            "rows_with_no_prediction": len(rows) - len(walk_min),
            "total_hours_one_way": round(sum(walk_min) / 60.0, 2),
            "longest_min": round(max(walk_min), 1) if walk_min else None,
            "note": ("the cap and this budget cover only rows with a finite predicted time; an "
                     "OFF_NETWORK row has none, and adjacency to a PASS bounds its distance to "
                     "the indexed network, not the length of the walk"),
        },
        "blind_spot": (
            "The layer's aggregation is cost_selected_category: the time of the journey our cost "
            "model selected, an UPPER BOUND, not the minimum over qualifying destinations. The "
            "selected destination's identity is not stored either, so this audit establishes that "
            "some qualifying destination was open and reachable, never that ours was. Narrowing, "
            "not closing, the closed-destination blind spot that E1 and E2 share; closing it needs "
            "one bounded graph load over the sampled cells, keeping the POI-to-node association."
        ),
        "attribution": {
            "buildings_in_cell": (
                "Derived from Overture Maps buildings, release 2026-10-21.0, aggregated to counts "
                "per cell. No footprint geometry is reproduced. Upstream in this metro: "
                "OpenStreetMap (454,012 rows, ODbL 1.0), Microsoft ML Buildings (360,755 rows, "
                "ODbL 1.0 -- NOT CC BY, which an earlier version of this notice said) and Esri "
                "Community Maps contributors (26,653 rows, CC BY 4.0 with OpenStreetMap waivers). "
                "ODbL 4.3 and CC BY 3 notice obligations "
                "apply to a count raster as much as to geometry; see docs/experiments/audit/"
                "README.md and project-v2-rethink-decisions decision 17."
            ),
            "travel_times": ("our own routing over an OpenStreetMap extract (ODbL 1.0). Running "
                             "our own router does not remove the source-database notice"),
            "overture": "https://docs.overturemaps.org/attribution/",
            "odbl": "https://opendatacommons.org/licenses/odbl/1-0/",
            "cc_by": "https://creativecommons.org/licenses/by/4.0/legalcode.en",
        },
        "seconds_precision": (
            "The stored seconds are float32. A model value of 600.00001 s is stored as 600.0 and "
            "so passes a 600 s threshold the model fails. This audit evaluates the stored "
            "artifact, which is what the product ships, not the model's float64 answer."
        ),
        "reproducibility": (
            f"v2/data/ is gitignored, so the input rasters named above do not travel with a "
            f"clone: this sheet is reproducible only on a machine that holds them. Rebuild with "
            f"`uv run python spikes/s2_building_weighted_coverage.py {args.category} {args.mode}`, "
            f"which needs data/{metro.name}/roads.graphml (670 MB). The sha256s identify the "
            f"inputs on a machine that has them."
        ),
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }
    meta_path = out_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")

    print(f"{len(rows)} journeys -> {_rel(out_path)}")
    print(f"provenance        -> {_rel(meta_path)}")
    print(f"min_possible_s     : {prov['min_possible_s']['origin']} "
          f"(reason max {prov['reason_max_name']})")
    for name, c in census.items():
        print(f"  {name:<28} {c['in_stratum']:>7,} cells  {c['eligible']:>7,} eligible  "
              f"{c['drawn']:>2} drawn")
        n = c.get("nearest_outside_radius")
        if n:
            print(f"  {'':<28} none in radius; nearest is {n['km']} km away at "
                  f"{n['lat']},{n['lon']} (cell {n['cell'][0]},{n['cell'][1]})")
    if walk_min:
        print(f"predicted one-way walking: {sum(walk_min) / 60.0:.2f} h over "
              f"{len(walk_min)} rows with a finite time, longest {max(walk_min):.0f} min")
    print(f"built in {meta['elapsed_s']}s without loading the road graph")


if __name__ == "__main__":
    try:
        main()
    except Refused as e:
        sys.exit(f"refused: {e}")
