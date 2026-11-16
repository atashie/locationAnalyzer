"""What the page **draws**, against what the publication **says** — queue item 3, first half.

Codex pass 54 asked for this comparison in two steps rather than one: compare the **drawn** pixel
with the **published** pixel first, and only then trace that pixel back to the source grid.
Comparing the page straight against `GridSpec.cell_for_lonlat` folds the WGS84 re-tiling and
MapLibre's placement into one number, and `s3-5-export-regrid.json` has already measured the
re-tiling. So this script holds both grids fixed and changes only one thing: **which published row
is painted at a given latitude.**

The published raster's rows are linear in latitude. MapLibre draws a `canvas` source as a textured
quad whose four corners are placed in Web Mercator, so the texture row it samples is linear in
Mercator *y*. `measure_shipped_disclosure.mercator_rows` is the rule that produced the published
"131,571 structures shift by one row" figure, and this script imports that same function rather
than restating it, so what is tested here is the claim that was published.

**The displacement is sub-pixel, and that is why a naive probe would have found nothing.** At every
one of the 514 row *centres* the two rules agree exactly, so a browser probe aimed at cell centres
could not have failed — it would have reported agreement and established nothing. The disagreement
lives near row *boundaries*: the drawn texture is offset by up to 0.3656 of a row, about 36 m,
zero at the north and south edges of the footprint and largest in the middle.

**The household figure is not the row-index movement.** A row that moves is only visible if the
colour moves with it, so this reports, for each threshold, how many structures stand where the map
paints one verdict and the card states another — and reports the two directions separately,
because they are different harms:

* **painted excluded, card included** — a *false exclusion in the picture*. This is the one Codex
  pass 54 named as unexamined: a household discards a neighbourhood because it is outside the
  coloured area, and never opens a card there, so no explanation ever gets the chance to correct
  the colour.
* **painted included, card excluded** — a household is drawn in and then told out, which is
  visible to anyone who opens the card and so cannot silently remove a candidate.

Two controls, because a count like this must be able to come out zero and must be able to come out
large. The **null** control replaces the drawn rule with the published rule and must report zero
contradictions at every threshold; the **one-row** control shifts by a whole row and must report
many more than the real rule. A measurement that cannot do both is not measuring the displacement.

What this cannot establish: that MapLibre really places the quad this way. That is one browser
session, and the `probes` section is its predeclared oracle — written here, before any browser ran,
with the sensitive probes marked, because a probe at a cell centre is inert by construction.

    v2/.venv/Scripts/python.exe scripts/measure_drawn_pixel.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
from pyproj import Transformer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from measure_shipped_disclosure import mercator_rows                     # noqa: E402
from locfinder import wire                                               # noqa: E402
from locfinder.measure.frames import structure_population                # noqa: E402
from locfinder.metros import get_metro                                   # noqa: E402
from locfinder.status import Outcome                                     # noqa: E402

V2 = pathlib.Path(__file__).resolve().parents[1]
LAYERS = V2 / "data" / "layers"
PUBLISHED = V2 / "spikes" / "g3-render" / "fixtures" / "published"
STEM = "own_triangle_grocery_walk"
METRO = get_metro()
ARTIFACT = V2.parent / "docs" / "experiments" / "s3-10-drawn-pixel.json"

#: The page opens with this threshold on the one published walk layer -- `defaultThreshold` in
#: `app.js`. It leads the list because it is the number a household meets before touching anything.
PAGE_DEFAULT_MIN = 20
THRESHOLDS_MIN = (PAGE_DEFAULT_MIN, 10, 15, 25, 45)

#: What `worker.js` paints for each outcome: included is translucent blue, unknown is a diagonal
#: hatch, excluded is fully transparent and shows the basemap. The names are the words a report may
#: use; the bytes are in `worker.js` (`PX_IN`, `PX_NODATA`, `PX_OUT`).
PAINT = {int(Outcome.PASS): "blue (included)",
         int(Outcome.FAIL): "transparent (excluded)",
         int(Outcome.UNKNOWN): "hatched (unknown)"}

OUTCOME_NAME = {int(Outcome.PASS): "PASS", int(Outcome.FAIL): "FAIL",
                int(Outcome.UNKNOWN): "UNKNOWN"}

STATUS_NAME = {wire.OK: "OK", wire.OFF_NETWORK: "OFF_NETWORK",
               wire.BEYOND_HORIZON: "BEYOND_HORIZON", wire.NO_PATH: "NO_PATH",
               wire.LAYER_UNKNOWN: "LAYER_UNKNOWN", wire.OUTSIDE: "OUTSIDE",
               wire.UNKNOWN_CAUSE: "UNKNOWN_CAUSE"}

#: `worker.js`'s three pixels, and the hatch it draws an unknown cell with.
PX_IN = [24, 119, 242, 150]
PX_NODATA = [60, 60, 60, 130]
PX_OUT = [0, 0, 0, 0]
HATCH_PERIOD, HATCH_WIDTH = 8, 2


def paint_rgba(code: int, row: int, col: int) -> list[int]:
    """The exact RGBA `worker.js` writes for one cell, so the probe compares bytes and not words.

    The mask canvas is one pixel per published cell, and an unknown cell is hatched by cell index:
    `((row + col) & 7) < 2` carries the grey and the rest is left transparent. So a single unknown
    cell off the stripe is painted the same bytes as an excluded one — the hatch reads as a texture
    over a region, not as a colour on a cell — and a probe that inferred the outcome from the pixel
    would be guessing. Hence the expectation is computed here, from the outcome, with the phase.
    """
    if code == int(Outcome.PASS):
        return list(PX_IN)
    if code == int(Outcome.FAIL):
        return list(PX_OUT)
    return list(PX_NODATA) if ((row + col) % HATCH_PERIOD) < HATCH_WIDTH else list(PX_OUT)


def mercator_y(lat: np.ndarray) -> np.ndarray:
    """Web Mercator *y*, up to the affine scaling the quad's corners cancel out."""
    return np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def published_rows(lat: np.ndarray, north: float, south: float, nrows: int) -> np.ndarray:
    """The row the publication assigns, and the row the card names.

    This is `cellForLonLat` in `card.js` restated independently from the format's own definition —
    rows linear in latitude over `bounds_wgs84` — so that the browser's answer is compared against
    the specification rather than against itself.
    """
    return np.floor((north - lat) / (north - south) * nrows).astype(np.int64)


def displacement(north: float, south: float, nrows: int, samples: int = 200_001) -> dict:
    """The sub-row offset profile, and the check that the rule under test is the published one."""
    lat = np.linspace(south, north, samples)
    yn, ys = mercator_y(np.array([north]))[0], mercator_y(np.array([south]))[0]
    cont_drawn = (yn - mercator_y(lat)) / (yn - ys) * nrows
    cont_pub = (north - lat) / (north - south) * nrows
    offset = cont_drawn - cont_pub

    # The rule under test must be the one the published figure used, not a restatement of it.
    inner = lat[1:-1]
    mine = np.floor((yn - mercator_y(inner)) / (yn - ys) * nrows).astype(np.int64)
    theirs = mercator_rows(inner, north, south, nrows)
    if not np.array_equal(mine, theirs):
        raise SystemExit("the local Mercator row rule disagrees with "
                         "measure_shipped_disclosure.mercator_rows, so this script would be "
                         "testing a different claim from the one that was published")

    row_centres = np.arange(nrows)
    lat_centres = north - (row_centres + 0.5) * (north - south) / nrows
    centre_drawn = mercator_rows(lat_centres, north, south, nrows)
    worst = int(np.argmax(np.abs(offset)))
    row_m = (north - south) / nrows * 111_320.0
    return {
        "what_moves": ("which published ROW is painted at a latitude. Columns do not move at all: "
                       "Mercator x is linear in longitude, so the column the page draws and the "
                       "column it names are the same column"),
        "max_offset_rows": round(float(abs(offset[worst])), 4),
        "max_offset_metres": round(float(abs(offset[worst])) * row_m, 2),
        "at_latitude": round(float(lat[worst]), 6),
        "sign": ("positive offset means the colour painted at a latitude belongs to a cell FURTHER "
                 "SOUTH than the one the card names, so the coloured picture sits north of where "
                 "the publication puts it"),
        "offset_at_latitude": {f"{v:.3f}": round(float(offset[np.argmin(abs(lat - v))]), 4)
                               for v in (35.70, 35.75, 35.80, 35.85, 35.925, 36.00, 36.05,
                                         36.10, 36.15)},
        "share_of_the_latitude_span_over_quarter_row": round(float((abs(offset) > 0.25).mean()), 4),
        "row_centres_where_the_two_rules_disagree": int((centre_drawn != row_centres).sum()),
        "why_that_is_zero_and_matters": (
            "at every row centre the two rules name the same row, so a browser probe aimed at cell "
            "centres cannot fail. It would report agreement at all 514 rows and establish nothing. "
            "The probes below are placed near row boundaries for exactly this reason"),
        "one_row_in_metres": round(float(row_m), 2),
    }


def exposure(outcomes: dict[int, np.ndarray], value: np.ndarray, rows_pub: np.ndarray,
             rows_drawn: np.ndarray, col: np.ndarray) -> dict:
    """Per threshold: how often the colour drawn under a structure contradicts its own card."""
    out: dict[str, dict] = {}
    for t_min, outcome in outcomes.items():
        card = outcome[rows_pub, col]
        seen = outcome[rows_drawn, col]
        pair = {}
        for a, an in OUTCOME_NAME.items():
            for b, bn in OUTCOME_NAME.items():
                if a == b:
                    continue
                n = int(((seen == a) & (card == b)).sum())
                if n:
                    pair[f"painted_{an}_card_{bn}"] = n
        out[str(t_min)] = {
            "structures_compared": int(len(rows_pub)),
            "rows_that_move": int((rows_drawn != rows_pub).sum()),
            "the_colour_contradicts_the_card": int((seen != card).sum()),
            "painted_excluded_card_included": int(((seen == int(Outcome.FAIL))
                                                   & (card == int(Outcome.PASS))).sum()),
            "painted_included_card_excluded": int(((seen == int(Outcome.PASS))
                                                   & (card == int(Outcome.FAIL))).sum()),
            "every_direction": pair,
            "and_the_minute_differs": int((value[rows_drawn, col]
                                           != value[rows_pub, col]).sum()),
        }
    return out


def sensitive_probe(row: int, outcome: np.ndarray, north: float, south: float, nrows: int,
                    ncols: int, margin: int = 50) -> tuple[float, int] | None:
    """A latitude inside published `row` whose drawn row is `row + 1`, and a column where that
    changes the verdict. Returns `(lat, col)`, or None if this row offers no such column.

    The latitude sits a tenth of a row above `row`'s southern edge, which is inside `row` by the
    published rule and inside `row + 1` by the drawn rule wherever the offset exceeds 0.1 rows.
    """
    row_h = (north - south) / nrows
    lat = north - (row + 1) * row_h + 0.1 * row_h
    if int(published_rows(np.array([lat]), north, south, nrows)[0]) != row:
        return None
    if int(mercator_rows(np.array([lat]), north, south, nrows)[0]) != row + 1:
        return None
    here, below = outcome[row], outcome[row + 1]
    inner = slice(margin, ncols - margin)
    cols = np.where(here[inner] != below[inner])[0] + margin
    if not len(cols):
        return None
    # **Prefer the included/excluded edge.** Any disagreement between the two rows would prove the
    # displacement, but blue against transparent is the edge a household reads as "this
    # neighbourhood is in or out", and hatch against transparent is not. Taking the first
    # disagreeing column instead put all three probes in the off-network fringe at the western
    # edge, where the contradiction is real and the decision is not.
    pf = {int(Outcome.PASS), int(Outcome.FAIL)}
    best = [c for c in cols if {int(here[c]), int(below[c])} == pf]
    return float(lat), int((best or list(cols))[0])


def inert_probe(outcome: np.ndarray, nrows: int, ncols: int) -> tuple[int, int] | None:
    """A cell whose neighbours above and below agree with it, so the probe must find agreement."""
    agree = ((outcome[1:-1] == outcome[:-2]) & (outcome[1:-1] == outcome[2:])
             & (outcome[1:-1] == int(Outcome.PASS)))
    rows, cols = np.where(agree[200:300, 100:ncols - 100])
    if not len(rows):
        return None
    return int(rows[0]) + 201, int(cols[0]) + 100


def destination_record(records: list, di: int) -> dict | None:
    """What the card has to name, straight from the side table the plane indexes.

    A destination is a node and not a shop: `destinationText` in `card.js` names every place on
    the node when there is more than one, so the oracle predeclares the list and the count rather
    than a single name it would have had to choose.
    """
    if di == 65535 or di >= len(records):
        return None
    rec = records[di]
    return {"ordinal": rec.get("ordinal"), "place_count": rec.get("place_count"),
            "place_names": [p.get("name") for p in rec.get("places", []) if p.get("name")]}


def build_probes(man: dict, value: np.ndarray, status: np.ndarray, flag: np.ndarray,
                 dest: np.ndarray, dest_records: list, outcome: np.ndarray) -> list[dict]:
    """The predeclared oracle for the browser session, written before any browser ran."""
    nrows, ncols = man["nrows"], man["ncols"]
    west, south, east, north = man["bounds_wgs84"]
    row_h, col_w = (north - south) / nrows, (east - west) / ncols
    probes: list[dict] = []

    def add(pid: str, why: str, lon: float, lat: float, sensitive: bool) -> None:
        rec: dict = {"id": pid, "why": why, "lon": round(lon, 7), "lat": round(lat, 7),
                     "sensitive": sensitive}
        inside = (west <= lon < east) and (south < lat <= north)
        if not inside:
            rec["expected_card"] = {"outside": True}
            rec["expected_published_cell"] = None
            probes.append(rec)
            return
        r = int(published_rows(np.array([lat]), north, south, nrows)[0])
        c = int(np.floor((lon - west) / (east - west) * ncols))
        d = int(np.clip(mercator_rows(np.array([lat]), north, south, nrows), 0, nrows - 1)[0])
        di = int(dest[r, c])
        rec["expected_published_cell"] = {"row": r, "col": c}
        rec["expected_drawn_row"] = d
        rec["expected_drawn_minus_published"] = d - r
        rec["expected_card"] = {
            "value_byte": int(value[r, c]),
            "status_byte": int(status[r, c]),
            "status_name": STATUS_NAME.get(int(status[r, c]), "?"),
            "route_flag_byte": int(flag[r, c]),
            "destination_index": None if di == 65535 else di,
            "destination": destination_record(dest_records, di),
            "outcome": OUTCOME_NAME[int(outcome[r, c])],
            "paint_of_the_cell_the_card_names": PAINT[int(outcome[r, c])],
            "rgba_of_the_cell_the_card_names": paint_rgba(int(outcome[r, c]), r, c),
        }
        rec["expected_paint_under_the_pointer"] = PAINT[int(outcome[d, c])]
        rec["expected_rgba_under_the_pointer"] = paint_rgba(int(outcome[d, c]), d, c)
        rec["expected_outcome_under_the_pointer"] = OUTCOME_NAME[int(outcome[d, c])]
        rec["the_picture_contradicts_the_card_here"] = bool(outcome[d, c] != outcome[r, c])
        probes.append(rec)

    # Corners, half a cell inside, because a relative invariant cannot see an absence and the
    # corners are where an off-by-one placement is cheapest to see.
    for pid, lon, lat in (("corner_nw", west + col_w / 2, north - row_h / 2),
                          ("corner_ne", east - col_w / 2, north - row_h / 2),
                          ("corner_sw", west + col_w / 2, south + row_h / 2),
                          ("corner_se", east - col_w / 2, south + row_h / 2)):
        add(pid, "a footprint corner, half a cell inside; the offset is near zero at the north and "
                 "south edges, so these probes test the placement of the quad and not the stretch",
            lon, lat, sensitive=False)

    # The one cell with a real-world observation behind it.
    add("the_walked_cell", "the centre of cell (286, 129), which is the cell band15min_pass-03 was "
                           "walked from; a cell centre, so it is inert for the displacement and "
                           "present because its card is the one a person can check against a walk",
        west + (129 + 0.5) * col_w, north - (286 + 0.5) * row_h, sensitive=False)

    # The probes that can actually fail.
    for label, row in (("north", 100), ("mid", 257), ("south", 420)):
        found = sensitive_probe(row, outcome, north, south, nrows, ncols)
        if found is None:
            continue
        lat, c = found
        add(f"boundary_{label}",
            f"a tenth of a row above the southern edge of published row {row}, at a column where "
            f"rows {row} and {row + 1} differ in verdict. The card must name row {row} while the "
            f"pixel under the pointer is painted from row {row + 1}: this is the probe that can "
            f"fail, and it is where a household could be shown the wrong colour",
            west + (c + 0.5) * col_w, lat, sensitive=True)

    found = inert_probe(outcome, nrows, ncols)
    if found is not None:
        r, c = found
        add("inert_interior",
            "a cell centre whose rows above and below agree with it, so this probe MUST report "
            "agreement. It is the control on the sensitive ones: if it also disagrees, the "
            "comparison is broken rather than the placement",
            west + (c + 0.5) * col_w, north - (r + 0.5) * row_h, sensitive=False)

    add("outside_west", "a longitude west of the footprint; the card must say the pointer is "
                        "outside the published area and must not name a cell",
        west - col_w, north - row_h * 100, sensitive=False)
    add("outside_north", "a latitude north of the footprint, which is the half-open edge the "
                         "published rule includes and excludes differently from the southern one",
        west + col_w * 100, north + row_h, sensitive=False)
    return probes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=ARTIFACT)
    args = ap.parse_args(argv)

    man = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    nrows, ncols = man["nrows"], man["ncols"]
    west, south, east, north = man["bounds_wgs84"]
    entry = next(l for l in man["layers"] if l["id"] == STEM)

    def plane(key: str, dtype=np.uint8) -> np.ndarray:
        return np.frombuffer((PUBLISHED / entry[key]).read_bytes(),
                             dtype=dtype).reshape(nrows, ncols)

    value, status, flag = plane("value_file"), plane("status_file"), plane("flag_file")
    dest = plane("dest_file", np.dtype("<u2"))
    table = json.loads((PUBLISHED / entry["dest_table"]).read_text(encoding="utf-8"))
    records = table["destinations"] if isinstance(table, dict) else table

    outcomes = {t: np.asarray(wire.outcome_planes(value, status, threshold_min=t,
                                                  horizon_s=entry["horizon_s"]))
                for t in THRESHOLDS_MIN}

    grid = METRO.grid()
    _ids, pts, _total = structure_population(
        LAYERS.parent / METRO.name / "overture_buildings_accepted.parquet", grid)
    lon, lat = Transformer.from_crs(grid.crs, "EPSG:4326", always_xy=True).transform(
        pts[:, 0], pts[:, 1])
    col = np.floor((lon - west) / (east - west) * ncols).astype(np.int64)
    r_pub = published_rows(lat, north, south, nrows)
    inside = (col >= 0) & (col < ncols) & (r_pub >= 0) & (r_pub < nrows)
    col, r_pub, lat_in = col[inside], r_pub[inside], lat[inside]
    r_drawn = np.clip(mercator_rows(lat_in, north, south, nrows), 0, nrows - 1)

    report = {
        "what_this_is": ("the DRAWN pixel against the PUBLISHED pixel, which is the first of the "
                         "two steps Codex pass 54 asked be kept apart. Both grids are the shipped "
                         "514 x 643 raster; the only thing that changes is which row MapLibre "
                         "paints at a latitude"),
        "published": {"encoding": man["encoding"], "nrows": nrows, "ncols": ncols,
                      "bounds_wgs84": man["bounds_wgs84"], "layer": STEM},
        "page_default_threshold_min": PAGE_DEFAULT_MIN,
        "displacement": displacement(north, south, nrows),
        "structures": {"total": int(len(pts)), "inside_the_published_bounds": int(inside.sum()),
                       "omitted": int((~inside).sum())},
        "exposure": exposure(outcomes, value, r_pub, r_drawn, col),
        "controls": {
            "null": {
                "what_it_proves": ("that the contradictions are produced by the displacement and "
                                   "not by the comparison. The drawn rule is replaced by the "
                                   "published rule, so every count must be zero"),
                "result": exposure(outcomes, value, r_pub, r_pub, col),
            },
            "one_row": {
                "what_it_proves": ("that the comparison can report a large number, so a small one "
                                   "is a finding rather than an inert check. The drawn rule is "
                                   "shifted by a whole row"),
                "result": exposure(outcomes, value, r_pub,
                                   np.clip(r_pub + 1, 0, nrows - 1), col),
            },
        },
        "probes": build_probes(man, value, status, flag, dest, records,
                              outcomes[PAGE_DEFAULT_MIN]),
        "what_this_establishes": (
            "that the picture the page draws is displaced from the publication it draws, by up to "
            "0.37 of a row, and how many structures stand where that displacement puts a colour "
            "that contradicts their own card"),
        "what_this_does_not_establish": (
            "that MapLibre places the quad this way. The rule is read off the canvas-source "
            "contract and matches the one behind the published 131,571 figure, and no browser had "
            "confirmed it when this was written. One did on 2026-11-15 -- eleven probes, "
            "zero disagreements, s3-11-browser-placement.json. The `probes` section is that session's oracle, and the sensitive probes "
            "are the ones that can fail. It also says nothing about the source grid: that step is "
            "s3-5-export-regrid.json, and pass 54's point is that folding the two together would "
            "hand a correct measurement the wrong interpretation. And one further step is left "
            "out on purpose: the raster is drawn at SCREEN resolution with nearest resampling, so "
            "which texel a screen pixel takes depends on the zoom -- at the opening fit the "
            "footprint is about 620 pixels tall for 514 rows, so a screen pixel spans more than a "
            "row and adds a quantisation of its own. The figures here are the zoom-independent "
            "part: the colour the placement assigns at a structure's exact latitude. Rolling the "
            "zoom in would be the same conflation in a smaller form"),
    }

    null = report["controls"]["null"]["result"]
    for t, rec in null.items():
        if rec["the_colour_contradicts_the_card"]:
            raise SystemExit(f"the null control reports {rec['the_colour_contradicts_the_card']} "
                             f"contradictions at {t} minutes, so the comparison is broken")
    for t in map(str, THRESHOLDS_MIN):
        real = report["exposure"][t]["the_colour_contradicts_the_card"]
        shifted = report["controls"]["one_row"]["result"][t]["the_colour_contradicts_the_card"]
        if shifted <= real:
            raise SystemExit(f"the one-row control reports {shifted} against the real rule's "
                             f"{real} at {t} minutes, so this comparison is not sensitive to the "
                             f"displacement it claims to measure")
    if not any(p.get("sensitive") for p in report["probes"]):
        raise SystemExit("no sensitive probe was found, so the browser session would have nothing "
                         "that could fail")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    d = report["displacement"]
    print(f"wrote {args.out.name}")
    print(f"  displacement: up to {d['max_offset_rows']} rows "
          f"({d['max_offset_metres']} m) at lat {d['at_latitude']}; "
          f"{d['row_centres_where_the_two_rules_disagree']} of {nrows} row centres disagree")
    for t in map(str, THRESHOLDS_MIN):
        e = report["exposure"][t]
        print(f"  {t:>2} min: {e['rows_that_move']:,} structures read a moved row; "
              f"{e['the_colour_contradicts_the_card']:,} see a colour that contradicts the card "
              f"({e['painted_excluded_card_included']:,} painted out but included, "
              f"{e['painted_included_card_excluded']:,} painted in but excluded)")
    print(f"  probes: {len(report['probes'])}, "
          f"{sum(1 for p in report['probes'] if p.get('sensitive'))} of them able to fail")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
