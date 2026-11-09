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

**What it does not know, which is the finding to carry forward.** The committed layer is an
aggregate — the minimum over every qualifying destination — and the identity of the destination it
chose is not stored. So the sheet cannot say "we routed you to this grocery"; it can only ask which
one the owner actually used. The audit can therefore establish that *some* destination was open and
reachable, not that *the product's* destination was. Recovering the chosen destination needs the
graph and a per-cell argmin, which `build_layer_surface` does not emit today. Until it does, the
closed-destination blind spot is narrowed by this audit, not closed.

## The lower bound is reconstructed, and that is only safe under an assertion

`status.Surface` needs three arrays and only two are on disk: `seconds` and `reason` were saved by
`spikes/s2_building_weighted_coverage.py`, `min_possible_s` was not. Loading it properly means
rebuilding from the 670 MB `roads.graphml`, which costs minutes and would make the owner's loop slow
enough to skip.

It can be reconstructed for **this** artifact because its reason array contains only `OK`,
`OFF_NETWORK` and `BEYOND_HORIZON`:

* `OK` -> the reported seconds, which is exact, and the bound is unused there anyway;
* `BEYOND_HORIZON` -> the horizon, which `Surface.validate` requires exactly and which `evaluate`
  reads from `horizon_s` rather than from the array;
* `OFF_NETWORK` -> `0`, a sound but weak bound.

**That is a property of this artifact, not of the format**, so two things are asserted before any
row is written and the script refuses rather than guesses if either fails.

1. `reason.max() <= Reason.BEYOND_HORIZON`. Without this, a layer containing `NO_PATH` would be
   reconstructed with a bound of `0` and read as `UNKNOWN` — turning a *proven* failure into an
   absence, which is the single error class this stage exists to prevent.
2. `max_access_m / max_speed_mps(mode) <= min(threshold)`. This is what makes the weak `OFF_NETWORK`
   bound not merely sound but **outcome-identical** to the real one here. The real bound is
   `access_m / max_speed_mps` (`traveltime/snap.py:291`), at most `200 / 1.4 = 142.9 s` for walking;
   `evaluate` turns a bound into a known failure only when it strictly exceeds the threshold, and
   143 s never exceeds 600 s. At a threshold below that bound the reconstruction would report
   `UNKNOWN` where the pipeline reports `FAIL`, so the script refuses there.

When a layer is rebuilt with `min_possible_s` saved beside it, that file is preferred and neither
assertion is needed. The builder now writes it.

## The sheet uses no footprint geometry

Journeys are restricted to cells containing at least one building, from the already-admitted count
raster `own_<metro>_buildings_per_cell.npy` — a cell with no structure has no door to walk from, so
it is unwalkable whatever its travel time says. The *individual* Overture footprints are not read.
`data/<metro>/overture_buildings_report.json` records their admitted use as "rasterised to counts,
never republished", and this sheet is committed to the repository; putting 30 building coordinates
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
from locfinder.traveltime.speeds import max_speed_mps

REPO = Path(__file__).resolve().parents[2]
V2 = REPO / "v2"

#: The horizon and access rule the committed layers were built to, used only when the layer carries
#: no sidecar of its own. Both are **assumptions about someone else's build**, which is the shape of
#: error this stage exists to catch, so neither is trusted silently:
#:
#: * `Surface.validate` only checks `max finite <= horizon`, so assuming a horizon *larger* than the
#:   build's passes silently — measured: a 60-minute layer read as 120 minutes raises nothing.
#:   `corroborate_horizon` closes that, and the builder now writes the sidecar.
#: * `MAX_ACCESS_M` enters the outcome-equivalence check. Rather than depend on it being exactly
#:   right, the check is restated as the widest build it tolerates: the equivalence holds for any
#:   `max_access_m <= min(threshold) * max_speed_mps(mode)` — 840 m for a 10-minute walk threshold,
#:   against the 200 m this project uses, a 4.2x margin.
CUTOFF_MIN = 120.0
MAX_ACCESS_M = 200.0

#: How close the largest finite time must sit below a claimed horizon for the claim to be
#: corroborated, when any cell was cut off by it. A cutoff that bound at all leaves cells just
#: inside it: walking 60 s covers 84 m, well under one 100 m cell, so on this grid a bound cutoff
#: with no cell within 60 s of it is not a surface this pipeline produces. Measured on the committed
#: Triangle layer the gap is 0.001 s.
HORIZON_CORROBORATION_S = 60.0

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
DEEP_PASS_S = 300.0
DEEP_FAIL_S = 1800.0

#: Columns the owner fills in while walking. Blank in every emitted row.
OWNER_COLUMNS = [
    "walked_date",
    "start_lon",
    "start_lat",
    "door_offset_m",
    "walked_seconds",
    "destination_used",
    "destination_open",
    "agrees",
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


def corroborate_horizon(seconds: np.ndarray, reason: np.ndarray, horizon_s: float) -> dict:
    """Check an *assumed* horizon against the arrays, as far as they can check it.

    The arrays can **falsify** a horizon claim and cannot **verify** one: `max finite <= horizon` is
    required, but nothing in them rules out a larger horizon than the build used. What they do rule
    out is a horizon far above a cutoff that visibly bound — if cells were cut off, cells sit just
    inside the cut. Returns the evidence; the caller refuses on `corroborated` being false.
    """
    finite = np.isfinite(seconds)
    max_finite = float(seconds[finite].max()) if finite.any() else float("nan")
    cut_off = int((reason == Reason.BEYOND_HORIZON).sum())
    gap = horizon_s - max_finite if finite.any() else float("inf")
    corroborated = (not cut_off) or (0.0 <= gap <= HORIZON_CORROBORATION_S)
    return {
        "max_finite_s": None if not finite.any() else round(max_finite, 3),
        "gap_to_horizon_s": None if not finite.any() else round(gap, 6),
        "cells_cut_off": cut_off,
        "corroborated": bool(corroborated),
        "basis": ("a cutoff that bound leaves cells just inside it; the arrays can falsify a "
                  "horizon claim but cannot verify one"),
    }


def load_surface(
    grid: GridSpec, *, category: str, mode: str, metro: str, thresholds_s: tuple[float, ...],
    layers: Path = LAYERS,
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
    else:
        horizon_s = CUTOFF_MIN * 60.0
        max_access_m = MAX_ACCESS_M
        build = {"origin": "assumed", "horizon_s": horizon_s, "max_access_m": max_access_m,
                 "assumed_from": "the constants in spikes/s2_building_weighted_coverage.py",
                 "horizon": corroborate_horizon(seconds, reason, horizon_s)}
        if not build["horizon"]["corroborated"]:
            raise Refused(
                f"the assumed horizon of {horizon_s:g}s is not corroborated by "
                f"{sec_path.name}: {build['horizon']['cells_cut_off']:,} cells were cut off by a "
                f"horizon, yet the largest finite time is "
                f"{build['horizon']['gap_to_horizon_s']:g}s below it. A cutoff that bound leaves "
                f"cells just inside it, so this layer was almost certainly built to a different "
                f"horizon and every BEYOND_HORIZON bound here would be wrong. Rebuild it, which "
                f"now writes the build parameters beside the layer."
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
        # Assertion 1: the reconstruction is only sound while no cell claims a proven absence of
        # any path. A NO_PATH cell reconstructed with a bound of 0 reads as UNKNOWN.
        if int(reason.max()) > int(Reason.BEYOND_HORIZON):
            raise Refused(
                f"{reason_path.name} contains {Reason(int(reason.max())).name}, so min_possible_s "
                "cannot be reconstructed: a NO_PATH cell would silently read as UNKNOWN, turning a "
                "proven failure into an absence.\nRebuild the surface with "
                "locfinder.traveltime.layer.build_layer_surface, which computes the real bound, and "
                "save it beside the layer:\n  uv run python "
                f"spikes/s2_building_weighted_coverage.py {category} {mode}"
            )
        # Assertion 2: the weak OFF_NETWORK bound of 0 is outcome-identical to the real one only
        # while the real one cannot exceed the smallest threshold.
        # Stated as the widest build this tolerates, rather than as a check on one assumed
        # access distance: the equivalence holds for any `max_access_m` up to
        # `min(threshold) * max_speed_mps`, so being wrong about the build's exact value is
        # harmless while it stays inside that envelope.
        access_limit_m = min(thresholds_s) * max_speed_mps(mode)
        weakest = max_access_m / max_speed_mps(mode)
        if max_access_m > access_limit_m:
            raise Refused(
                f"the reconstructed OFF_NETWORK bound (0) is not outcome-equivalent here: at "
                f"{max_access_m:g}m of access the real bound reaches {weakest:.1f}s, past the "
                f"smallest threshold of {min(thresholds_s):.0f}s, so some cells the pipeline "
                f"proves FAIL would be reported UNKNOWN. This reconstruction tolerates "
                f"max_access_m up to {access_limit_m:.0f}m. Rebuild with the real bound."
            )
        min_possible = np.where(reason == Reason.OK, seconds, 0.0)
        min_possible = np.where(reason == Reason.BEYOND_HORIZON, horizon_s, min_possible)
        prov["min_possible_s"] = {
            "origin": "reconstructed",
            "rule": "seconds where OK, horizon_s where BEYOND_HORIZON, 0 where OFF_NETWORK",
            "off_network_bound_equivalence": {
                "real_bound_max_s": round(weakest, 3),
                "max_access_m": max_access_m,
                "max_access_m_tolerated": round(access_limit_m, 1),
                "max_speed_mps": max_speed_mps(mode),
                "smallest_threshold_s": min(thresholds_s),
            },
        }

    # `validate` is also the cross-check between the two files, which were written by separate runs
    # 43 minutes apart: it requires a finite time exactly where the reason is OK, so a reason array
    # belonging to a different build would be rejected here rather than silently mislabel cells.
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
            f"{sec_path.name} and {reason_path.name} do not describe one surface: {e}. "
            f"They were written by separate runs, so a rebuild of one without the other leaves "
            f"them inconsistent. Rebuild both: uv run python "
            f"spikes/s2_building_weighted_coverage.py {category} {mode}"
        ) from e
    return surf, prov


def strata(
    surf: Surface, outcomes: dict[int, np.ndarray], *, thresholds_min: tuple[int, ...]
) -> dict[str, np.ndarray]:
    """The five candidate pools, as boolean masks over the grid."""
    seconds, reason = surf.seconds, surf.reason
    ok = reason == Reason.OK
    off = reason == Reason.OFF_NETWORK
    neighbourhood = np.ones((3, 3), dtype=bool)

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

    # The product says "unknown" immediately next door to a pass. Either the access rule is too
    # strict or the graph is missing a path people use; the two look identical from the layer.
    out["off_network_beside_ok"] = off & ndimage.binary_dilation(ok, structure=neighbourhood)

    # Controls, for a systematic offset to be visible rather than inferred. `binary_erosion`
    # keeps only cells whose whole 3x3 neighbourhood agrees, so a control is not a near-boundary
    # cell that happens to be deep in seconds.
    tightest, loosest = min(thresholds_min), max(thresholds_min)
    pass_everywhere = ndimage.binary_erosion(
        outcomes[tightest] == Outcome.PASS, structure=neighbourhood, border_value=0)
    fail_everywhere = ndimage.binary_erosion(
        outcomes[loosest] == Outcome.FAIL, structure=neighbourhood, border_value=0)
    out["deep_pass_control"] = ok & (seconds <= DEEP_PASS_S) & pass_everywhere
    out["deep_fail_control"] = ok & (seconds >= DEEP_FAIL_S) & fail_everywhere
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
    # Two floats rather than one "LON,LAT" string: every longitude here starts with a minus sign,
    # and argparse reads `--near -79.05,35.91` as an unknown option. It accepts a bare negative
    # *number*, so `--near -79.05 35.91` -- the form anyone would type -- works.
    ap.add_argument("--near", nargs=2, type=float, metavar=("LON", "LAT"),
                    help="restrict to journeys within --radius-km of this point, so the sheet is "
                         "walkable in one outing instead of scattered over the metro")
    ap.add_argument("--radius-km", type=float, default=5.0)
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
    surf, prov = load_surface(grid, category=args.category, mode=args.mode, metro=metro.name,
                              thresholds_s=thresholds_s)
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
        within = np.hypot(xs - x0, ys - y0) <= args.radius_km * 1000.0
        eligible &= within
        notes["near"] = {"lon": lon, "lat": lat, "cell": list(here),
                         "radius_km": args.radius_km, "cells_within": int(within.sum())}

    lons, lats = grid.cell_centers_lonlat()
    minutes = encode_minutes(surf.seconds)
    rng = np.random.default_rng(args.seed)
    door_bound_m = grid.cell_m * math.sqrt(2.0) / 2.0

    rows: list[dict] = []
    census: dict = {}
    for name, pool in pools.items():
        available = pool & eligible
        flat = np.flatnonzero(available)
        take = min(args.per_stratum, flat.size)
        picked = rng.choice(flat, size=take, replace=False) if take else np.empty(0, dtype=int)
        census[name] = {"in_stratum": int(pool.sum()), "eligible": int(flat.size),
                        "drawn": int(take)}
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
        "deep_pass_s": DEEP_PASS_S,
        "deep_fail_s": DEEP_FAIL_S,
        "blind_spot": (
            "The committed layer is an aggregate over destinations and does not store which "
            "destination it chose, so this audit can establish that some destination was open and "
            "reachable, not that the product's destination was. Narrowing, not closing, the "
            "closed-destination blind spot that E1 and E2 share."
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
        print(f"  {name:<24} {c['in_stratum']:>7,} cells  {c['eligible']:>7,} eligible  "
              f"{c['drawn']:>2} drawn")
    print(f"built in {meta['elapsed_s']}s without loading the road graph")


if __name__ == "__main__":
    try:
        main()
    except Refused as e:
        sys.exit(f"refused: {e}")
