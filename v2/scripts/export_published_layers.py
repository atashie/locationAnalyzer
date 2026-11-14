"""Export the **published** layers in `published-v3` for the browser — S3.5's export half.

**The route-flag plane is optional and its absence means "this layer does not disclose".** A layer
carries one only when `<stem>_restricted_route.npy` sits beside its surface triple, written by
`scripts/flag_restricted_routes.py --write-raster`. A manifest that declares no `flag_file`
discloses nothing about routes, which is a different statement from "no route is restricted" — and
the decoder reports `restrictedIncludedCount: null` rather than 0 so a reader cannot confuse them.

`spikes/g3-render/export_layers.py` exports the G1 engine-comparison tifs and has two defects S3.5
names: it discovers layers by `<engine>_<category>_<mode>`, so it **omits**
`own_triangle_grocery_walk.tif` — the actual product layer — and it targets the 401 × 550 Phase 0
slice rather than the 514 × 643 Triangle footprint. Those two together mean the browser has never
once rendered the layer the product publishes.

This does not patch that exporter. It is a different job: that one compares engines from minute
rasters, and a minute raster **cannot** carry the status plane this format needs, because the
reason and the bound were discarded before the tif was written. This reads the surface triple that
`build_layer_surface` produced — seconds, reason and `min_possible_s` — and writes both planes.

**Nearest resampling for both planes, and no interpolation of anything.** A status code is a name,
so averaging two of them is meaningless; a minute is a decision input, so averaging two of them
publishes a region nobody computed. Pixels the source does not cover become `OUTSIDE` in the status
plane, which decodes to UNKNOWN — never to a known failure, and never to a travel time.

Writes `fixtures/published/<id>.value.bin`, `<id>.status.bin` and `manifest.json`, and reports the
deflated size of each, which is S3.5's transfer-size question.

    python scripts/export_published_layers.py
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import shutil
import sys
import zlib

import numpy as np
import rasterio
from rasterio.transform import from_bounds, from_origin
from rasterio.warp import Resampling, reproject

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from locfinder import wire                                      # noqa: E402
from locfinder.metros import get_metro                          # noqa: E402
from locfinder.status import CATEGORY_COST_SELECTED, Surface    # noqa: E402

V2 = pathlib.Path(__file__).resolve().parents[1]
LAYERS = V2 / "data" / "layers"
OUT = V2 / "spikes" / "g3-render" / "fixtures" / "published"
METRO = get_metro()

#: Every published surface, by the stem of its `.npy` triple. The product layer first.
SOURCES = [
    ("own_triangle_grocery_walk", "Grocery, walk (100 m)", 100.0),
    ("own_triangle_grocery_walk_cell200", "Grocery, walk (200 m candidate)", 200.0),
]


def load_route_flag(stem: str, shape, horizon_s: float,
                    fingerprint: str | None = None) -> np.ndarray | None:
    """The per-cell route flag, if this layer bundle carries one.

    Returning `None` is meaningful: it is "this layer does not disclose", and every consumer has to
    keep it distinct from a plane of zeros.

    Pass 48: the horizon is checked here because the 5,145-cell defect WAS a horizon disagreement
    between this raster and the surface it describes, and `wire.encode_route_flag` catches only one
    direction of it. A surface horizon SMALLER than the flag's leaves flags where the status is no
    longer OK, which that invariant refuses. A LARGER one leaves cells newly OK whose flag was
    never computed, so they ship ROUTE_CLEAR -- and a clear flag asserts nothing, which is exactly
    why nothing downstream can notice. The pairing is therefore checked where the pairing is made.
    """
    path = LAYERS / f"{stem}_restricted_route.npy"
    if not path.exists():
        return None
    flag = np.load(path)
    if flag.shape != tuple(shape):
        raise SystemExit(
            f"{path.name} is {flag.shape} and the surface is {tuple(shape)}; refusing to publish a "
            "disclosure that does not describe this layer")
    meta_path = LAYERS / f"{stem}_restricted_route_build.json"
    recorded = None
    if meta_path.exists():
        recorded = json.loads(meta_path.read_text(encoding="utf-8")).get("horizon_s")
    if recorded is None:
        # The raster in the repository predates the field. Accepting it keeps this a check rather
        # than a rebuild, but the gap is named rather than passed over in silence.
        print(f"  WARNING: {meta_path.name} records no horizon_s, so the flag cannot be checked "
              f"against the surface's {horizon_s:g} s. Rebuild it with "
              f"scripts/flag_restricted_routes.py --write-raster to close this.")
    elif float(recorded) != float(horizon_s):
        raise SystemExit(
            f"{path.name} was computed with horizon {float(recorded):g} s and the surface applies "
            f"{float(horizon_s):g} s. A smaller surface horizon leaves flags on journeys the layer "
            "no longer publishes; a larger one leaves newly published journeys silently unflagged. "
            "Rebuild the flag raster against this surface.")
    # Pass 48 F3: and WHICH surface. Shape, aggregate count and `flag implies OK` all accepted a
    # plane with one flag flipped down and one up, because a clear flag is not an assertion and
    # cannot be checked against anything. Provenance can be.
    if fingerprint is not None and meta_path.exists():
        stated = json.loads(meta_path.read_text(encoding="utf-8")).get("surface_fingerprint")
        if stated is None:
            print(f"  WARNING: {meta_path.name} records no surface_fingerprint, so this flag "
                  "cannot be tied to the surface it describes. Rebuild it with "
                  "scripts/flag_restricted_routes.py --write-raster to close this.")
        elif stated != fingerprint:
            raise SystemExit(
                f"{path.name} was computed against surface {stated} and this surface is "
                f"{fingerprint}. The flag describes a different layer, or the plane has been "
                "altered since it was written. A clear flag asserts nothing, so nothing else in "
                "this pipeline can notice. Rebuild the flag raster against this surface.")
    return flag


def load_selected_destination(stem: str, shape, horizon_s: float,
                             fingerprint: str | None = None):
    """`(plane, side table)` for this layer, or `(None, None)` if it names no destinations.

    `None` is meaningful in the same way the route flag's is: it means **this layer does not say
    which destination**, which a consumer must keep distinct from "there is no destination".

    The side table is a separate artifact with its own licence block and is carried through
    unmodified. The grocery names are CDLA-Permissive-2.0, Apache-2.0 and CC0-1.0, so they are
    publishable with attribution and carry none of the contractually restricted sources decision
    17 forbids -- but the travel-time layer is ODbL-published and ODbL is share-alike, so the two
    stay separate files rather than one merged object.
    """
    path = LAYERS / f"{stem}_selected_destination.npy"
    table_path = LAYERS / f"{stem}_selected_destination_table.json"
    if not path.exists():
        return None, None
    if not table_path.exists():
        raise SystemExit(
            f"{path.name} exists and {table_path.name} does not. A plane of ordinals with no table "
            "to index names nothing at all, and publishing it would ship identifiers no reader "
            "can resolve")
    plane = np.load(path)
    if plane.shape != tuple(shape):
        raise SystemExit(
            f"{path.name} is {plane.shape} and the surface is {tuple(shape)}; refusing to publish "
            "destinations that do not describe this layer")
    meta_path = LAYERS / f"{stem}_selected_destination_build.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    recorded = meta.get("horizon_s")
    if recorded is None:
        print(f"  WARNING: {meta_path.name} records no horizon_s, so the destination plane cannot "
              f"be checked against the surface's {horizon_s:g} s")
    elif float(recorded) != float(horizon_s):
        raise SystemExit(
            f"{path.name} was computed with horizon {float(recorded):g} s and the surface applies "
            f"{float(horizon_s):g} s, so the two disagree about which cells have a journey at all")
    stated = meta.get("surface_fingerprint")
    if fingerprint is not None and stated is not None and stated != fingerprint:
        raise SystemExit(
            f"{path.name} was computed against surface {stated} and this surface is {fingerprint}. "
            "The destinations describe a different layer, or the plane has been altered since it "
            "was written")
    table = json.loads(table_path.read_text(encoding="utf-8"))
    count = len(table.get("destinations", []))
    named = plane[plane != wire.DEST_NONE]
    if named.size and int(named.max()) >= count:
        raise SystemExit(
            f"{path.name} names ordinal {int(named.max())} and {table_path.name} holds {count} "
            "destinations, so at least one published cell points past the end of the table")
    check_table_is_publishable(table, table_path)
    return plane, table


# Every key a published side table is allowed to carry, at EVERY level, and every licence a
# record may be published under.
#
# Pass 49: the exporter carried the table through byte-for-byte and enforced nothing, so a field
# added upstream would ship -- and the fields deliberately left out of `place_record` are exactly
# the ones decision 17 forbids in an ODbL-published bundle: phones, emails, websites, socials,
# addresses and provider record ids. An allowlist is the only form of this check that works,
# because a blocklist cannot name a field nobody has invented yet.
#
# **Pass 50 finding B1: the first version checked two levels out of four.** It did not look at the
# table's root keys, at the keys inside the root `licence` object, or at the TYPES of the values
# in the fields it did allow. So a phone could arrive as root metadata, an upstream provider id
# inside `licence`, and a website inside an object stored under `brand` -- all three serialised
# unchanged, and the shipped-bundle check passed 75/75 on the result. A guarantee that "no
# forbidden field can leave" has to cover every entrance.
ROOT_FIELDS = {"what_this_is", "built", "mode", "category", "licence", "node_is_not_a_shop",
               "destinations"}
LICENCE_FIELDS = {"this_table", "source", "why_it_is_a_separate_artifact",
                  "fields_deliberately_omitted", "redistribution"}
PLACE_FIELDS = {"gers_id", "name", "brand", "category", "operating_status", "licence"}
ENTRY_FIELDS = {"ordinal", "node_index", "place_count", "places"}
PUBLISHABLE_LICENCES = {"CDLA-Permissive-2.0", "Apache-2.0", "CC0-1.0"}


def check_table_is_publishable(table: dict, table_path) -> None:
    """Refuse a side table that carries a key, a type or a licence nobody reviewed.

    This is a build-time gate, not a wire check: it decides what is allowed to leave the machine.
    It is deliberately strict about *unknown* things rather than about known-bad ones, and it is
    strict at every level, because a field smuggled in at the root ships exactly as readily as one
    smuggled into a place record.
    """
    name = getattr(table_path, "name", str(table_path))

    def refuse(what: str) -> None:
        raise SystemExit(f"{name}: {what}")

    def check_keys(obj, allowed: set[str], where: str) -> None:
        if not isinstance(obj, dict):
            refuse(f"{where} is {type(obj).__name__}, expected an object")
        extra = sorted(set(obj) - allowed)
        if extra:
            refuse(f"{where} carries {extra}, which this exporter has never reviewed for "
                   "publication. The fields left out of place_record() are the ones decision 17 "
                   "forbids in a published bundle -- phones, emails, websites, socials, "
                   "addresses, upstream provider record ids -- so an unreviewed key is refused "
                   f"rather than shipped. Add it to the allowlist deliberately, or stop "
                   "producing it")

    def check_scalar(value, where: str) -> None:
        """A reviewed FIELD holding an unreviewed OBJECT is how a website gets published."""
        if value is None or isinstance(value, (str, bool, int)):
            return
        if isinstance(value, float):
            if value != value:
                refuse(f"{where} is a float NaN. `json.dumps` writes that as the bare token NaN, "
                       "which is not JSON and which no browser will parse -- pass 49 finding 2. "
                       "A missing value is None")
            return
        refuse(f"{where} is {type(value).__name__}, and only scalars are published here. A "
               "nested object inside a reviewed field is an unreviewed field with a reviewed "
               "name -- pass 50 finding B1")

    check_keys(table, ROOT_FIELDS, "the table root")
    if "licence" in table:
        check_keys(table["licence"], LICENCE_FIELDS, "the root licence block")
        for key, value in table["licence"].items():
            if isinstance(value, list):
                for i, item in enumerate(value):
                    check_scalar(item, f"licence.{key}[{i}]")
            else:
                check_scalar(value, f"licence.{key}")
    for key, value in table.items():
        if key not in ("destinations", "licence"):
            check_scalar(value, f"the root field {key!r}")

    if not isinstance(table.get("destinations"), list):
        refuse("the table has no destinations list")
    for entry in table["destinations"]:
        check_keys(entry, ENTRY_FIELDS, f"destination entry {entry.get('ordinal')}"
                   if isinstance(entry, dict) else "a destination entry")
        for key in ("ordinal", "node_index", "place_count"):
            if not isinstance(entry.get(key), int) or isinstance(entry.get(key), bool):
                refuse(f"destination entry {entry.get('ordinal')} has {key}="
                       f"{entry.get(key)!r}, which is not an integer")
        if not isinstance(entry.get("places"), list) or not entry["places"]:
            refuse(f"destination entry {entry.get('ordinal')} carries no places; a node is a "
                   "destination only because a place is on it")
        if len(entry["places"]) != entry["place_count"]:
            refuse(f"destination entry {entry.get('ordinal')} declares "
                   f"{entry['place_count']} places and carries {len(entry['places'])}")
        for place in entry["places"]:
            check_keys(place, PLACE_FIELDS, f"a place record on entry {entry.get('ordinal')}")
            for key, value in place.items():
                check_scalar(value, f"place field {key!r} on entry {entry.get('ordinal')}")
            if not isinstance(place.get("gers_id"), str) or not place["gers_id"]:
                refuse(f"a place record on entry {entry.get('ordinal')} has no GERS id")
            lic = place.get("licence")
            if lic is not None and lic not in PUBLISHABLE_LICENCES:
                refuse(f"a place record is licensed {lic!r}, which is not one of "
                       f"{sorted(PUBLISHABLE_LICENCES)}. A licence this exporter has not "
                       "reviewed does not get published on the strength of being unfamiliar")


def load_surface(stem: str) -> tuple[Surface, dict]:
    build = json.loads((LAYERS / f"{stem}_build.json").read_text(encoding="utf-8"))
    seconds = np.load(LAYERS / f"{stem}.npy").astype(np.float64)
    reason = np.load(LAYERS / f"{stem}_reason.npy")
    lower = np.load(LAYERS / f"{stem}_min_possible_s.npy").astype(np.float64)
    surf = Surface(mode=build["mode"], engine=build["engine"], target=build["category"],
                   aggregation=build.get("aggregation", CATEGORY_COST_SELECTED),
                   horizon_s=float(build["horizon_s"]), seconds=seconds, reason=reason,
                   min_possible_s=lower).validate()
    return surf, build


def source_transform(build: dict, shape: tuple[int, int]):
    """The source grid's transform, from the build record rather than from a tif.

    `build.json` carries the origin and cell size for a layer this script wrote; the published
    100 m layer predates that and is reconstructed from the metro grid instead. Both are checked
    against the array's shape, because a transform that disagrees with its array silently places
    every cell in the wrong place.
    """
    if {"x_min", "y_max", "cell_m"} <= build.keys():
        x_min, y_max, cell_m = build["x_min"], build["y_max"], build["cell_m"]
        crs = build.get("crs", METRO.crs)
        # Pass 43 F8: this branch used to take the origin on trust. A transposed 83,076-cell
        # triple passed and would have exported under the wrong footprint -- silently, because a
        # transform that disagrees with its array moves every cell rather than failing.
        # Pass 44 F6: `None not in recorded` skipped the WHOLE guard when either dimension was
        # missing, so a record explicitly saying `nrows=258` accepted a 322-row array once
        # `ncols` was lost. Each supplied dimension is now checked on its own.
        for key, got in (("nrows", shape[0]), ("ncols", shape[1])):
            recorded = build.get(key)
            if recorded is not None and int(recorded) != int(got):
                raise SystemExit(
                    f"the build record says {key}={recorded} and the array has {got}; refusing "
                    "to export it under a transform that does not describe it")
    else:
        grid = METRO.grid()
        x_min, y_max, cell_m, crs = grid.x_min, grid.y_max, grid.cell_m, grid.crs
        if (grid.nrows, grid.ncols) != shape:
            raise SystemExit(
                f"the metro grid is {grid.nrows}x{grid.ncols} and the array is {shape[0]}x"
                f"{shape[1]}; refusing to guess a transform for it")
    return from_origin(x_min, y_max, cell_m, cell_m), crs


def reproject_plane(plane: np.ndarray, transform, crs, *, src_fill: int, dst_fill: int,
                    bounds, nrows: int, ncols: int, dtype=np.uint8) -> np.ndarray:
    """Nearest-resample one plane onto the published WGS84 grid.

    `dtype` exists for the destination plane, which is `uint16`: every other plane is a byte and
    the parameter was previously hard-coded. Resampling stays NEAREST for all of them -- a status
    code is a name, a minute is a decision input and a destination ordinal is an identity, and
    averaging any of the three publishes something nobody computed.
    """
    dst = np.full((nrows, ncols), dst_fill, dtype=dtype)
    reproject(source=np.ascontiguousarray(plane, dtype=dtype), destination=dst,
              src_transform=transform, src_crs=crs, src_nodata=src_fill,
              dst_transform=from_bounds(*bounds, ncols, nrows),
              dst_crs="EPSG:4326", dst_nodata=dst_fill, resampling=Resampling.nearest)
    return dst


INDEX_NONE = 0xFFFFFFFF

LICENCES = pathlib.Path(__file__).resolve().parents[1] / "licences"


def stamp() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")

# The attribution each licence needs carried with the data, beyond its text, and the text that
# must actually appear in it.
#
# Pass 50 finding B2: the first version checked only that the pathname EXISTED, so an empty file
# satisfied it. A notice requirement discharged by an empty file is not discharged. Each entry
# therefore names the string the file has to contain -- for Foursquare, the copyright line
# Overture's documentation gives as the minimum.
LICENCE_NOTICES = {
    # Apache-2.0 §4(d): keep the attribution notices from the source NOTICE file. In Overture,
    # Apache-licensed Places records are the Foursquare-sourced ones.
    "Apache-2.0": [("NOTICE-foursquare.txt", "Copyright 2024 Foursquare Labs, Inc.")],
}


def write_licence_bundle(out: pathlib.Path, tables: list[dict], releases: set[str]) -> dict:
    """Copy the text of every licence the published tables carry, and write the attribution.

    Pass 49 finding 3. The tables carried SPDX identifiers and an Overture release label, and
    nothing else: no licence texts, no Foursquare notice. CDLA-Permissive-2.0 §2.1 requires the
    **text of the agreement** to be made available with shared data, and Apache-2.0 §4 requires
    recipients to receive the licence, a statement of modification, and the source notices. A
    label is not a licence; "publishable with attribution" described the licence rather than
    anything the build had done.

    Refuses rather than warns. A bundle that ships a label it cannot resolve has already failed.
    """
    present = sorted({p.get("licence") for t in tables if t
                      for e in t.get("destinations", []) for p in e.get("places", [])
                      if p.get("licence")})
    missing = [lic for lic in present if not (LICENCES / f"{lic}.txt").exists()]
    if missing:
        raise SystemExit(
            f"the side tables carry {missing}, and {LICENCES} holds no text for them. Add the "
            "text, or stop publishing records under a licence this build cannot hand on")
    dest = out / "LICENSES"
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for lic in present:
        shutil.copyfile(LICENCES / f"{lic}.txt", dest / f"{lic}.txt")
        copied.append(f"LICENSES/{lic}.txt")
        for notice, required in LICENCE_NOTICES.get(lic, []):
            src = LICENCES / notice
            if not src.exists():
                raise SystemExit(
                    f"{lic} requires {notice} to travel with the data and {src} does not exist")
            text = src.read_text(encoding="utf-8")
            if required not in text:
                raise SystemExit(
                    f"{lic} requires {notice} to carry {required!r} and it does not. Pass 50 "
                    "finding B2: this gate used to check only that the file existed, so an empty "
                    "file passed -- and a notice requirement discharged by an empty file is not "
                    "discharged")
            shutil.copyfile(src, dest / notice)
            copied.append(f"LICENSES/{notice}")
    counts = collections.Counter(
        p.get("licence") for t in tables if t
        for e in t.get("destinations", []) for p in e.get("places", []))
    text = ATTRIBUTION.format(
        when=stamp(),
        releases=", ".join(sorted(releases)) or "unrecorded",
        counts="\n".join(f"* **{k}** — {v} place records" for k, v in sorted(counts.items())
                         if k),
        files="\n".join(f"* `{f}`" for f in copied))
    (out / "ATTRIBUTION.md").write_text(text, encoding="utf-8")
    return {"licences_present": present, "files": copied + ["ATTRIBUTION.md"],
            "place_records_by_licence": {k: v for k, v in sorted(counts.items()) if k},
            # Pass 50 finding B2. What this gate does and does not establish, in the manifest,
            # so a consumer is not left to infer clearance from the presence of files.
            "what_this_establishes": (
                "that every licence a published record names has its text in LICENSES/, and that "
                "each required notice file exists and carries its required line"),
            "what_this_does_not_establish": (
                "Apache-2.0 4 compliance for the Apache-licensed records. 4(a) is satisfied; "
                "4(b) is not discharged by ATTRIBUTION.md, because the requirement concerns "
                "notices carried by the modified files; 4(c) requires retaining all upstream "
                "copyright, patent, trademark and attribution notices and this build has not "
                "inventoried them; 4(d) requires a readable copy of the source NOTICE and the "
                "shipped file says on its face that it is not one. Treat the Apache records as "
                "NOT cleared for redistribution until the real NOTICE is obtained"),
            "apache_records_are_cleared_for_redistribution": False}


ATTRIBUTION = """# Attribution and licensing for this bundle

Written by `scripts/export_published_layers.py` on {when}. Every licence named here has its text
in `LICENSES/`, because a licence identifier is not a licence.

## The destination names

From **Overture Maps, release {releases}**, which licenses Places records by source:

{counts}

**These records have been modified.** Only `gers_id`, `name`, `brand`, `category`,
`operating_status` and `licence` are carried; phones, emails, websites, socials, addresses and
upstream provider record ids are dropped, and the records are grouped by the road-network node
they snap to. Apache-2.0 §4(b) requires modified files to carry prominent notices stating that
they were changed; the build date above is recorded because it is useful, **not** because §4(b)
asks for a date — an earlier version of this file said it did, and it does not.

### What is not yet established

Stating this here rather than implying compliance by silence:

* **§4(b)** is not discharged by this file alone. The requirement is about notices carried by the
  modified files; the modified file is `*.destinations.json` and it carries no such notice.
* **§4(c)** requires retaining all copyright, patent, trademark and attribution notices from the
  source. This build has not inventoried those upstream notices, so it cannot claim to have
  retained them all.
* **§4(d)** requires a readable copy of the attribution notices from the source `NOTICE`.
  `LICENSES/NOTICE-foursquare.txt` states on its face that it is **not** that copy: the upstream
  file is behind a gated repository. It carries the one line Overture documents as the minimum.

So this bundle should be treated as **not cleared for redistribution of the Apache-licensed
records** until the real `NOTICE` is obtained. The partial notice is here because preserving known
attribution and naming what is missing is better than shipping nothing — but its presence is not
clearance, and the licence gate that copies it does not establish §4 compliance.

## The travel-time planes

Derived from **OpenStreetMap**, © OpenStreetMap contributors, available under the **Open Database
License (ODbL) 1.0**. The planes are an ODbL-published derived database.

## Why the names are a separate file from the planes

For organisation and for clarity about what came from where, **not** as a legal determination.
An earlier version of this project claimed that separate files were what kept permissively
licensed names out of a share-alike database, and that keeping them apart avoided having to
argue about derivative-database boundaries. Codex pass 49 finding 4 withdrew both claims: ODbL
distinguishes a collective from a derivative database by the substantive relationship between
the parts, not by how many files they are stored in. The project's own decision 17 permits
OSM-derived and Overture-derived data in the same tables provided the notices travel with them.

What is actually load-bearing is decision 17's real rule, which this bundle does satisfy: no
contractually restricted source -- no Google place ids, no RentCast, no MLS or IDX, no portal
data -- appears in any published artifact here.

## Files

{files}
* `ATTRIBUTION.md` (this file)
"""


def verify_provenance(stem: str, transform, crs, bounds, nrows: int, ncols: int,
                      *, source: dict, published: dict) -> dict:
    """Every published plane at every cell must hold the value its source cell holds.

    Pass 49 finding 1. A source-cell index is reprojected through the same nearest call as the
    planes, so the published grid carries, per cell, the identity of a source cell; then each
    published plane is compared against its source plane at that index.

    **What it establishes, stated no more strongly than pass 50 finding A1 allows.** It is an
    output-VALUE consistency check, not a proof of physical source-cell identity. If two source
    cells hold the same value, sampling either produces the same byte and the comparison cannot
    tell them apart -- so "fails whatever the values are", which this docstring used to claim, is
    false. What it does establish is that no published cell holds a value that is wrong *for the
    source cell the reprojection says fed it*, which is the thing a household would be shown.

    That is still strictly more than the two-directional destination invariant gives. That
    invariant compares answer-presence masks and never reads a value, so exchanging two valid
    destinations between two OK cells passes it and fails here.

    The returned record is a measurement, not a claim.
    """
    src_index = np.arange(next(iter(source.values())).size,
                          dtype=np.uint32).reshape(next(iter(source.values())).shape)
    idx = reproject_plane(src_index, transform, crs, src_fill=INDEX_NONE, dst_fill=INDEX_NONE,
                          bounds=bounds, nrows=nrows, ncols=ncols, dtype=np.uint32)
    covered = idx != INDEX_NONE
    flat = idx[covered].astype(np.int64)
    for name, plane in published.items():
        got = plane[covered]
        want = np.asarray(source[name]).ravel()[flat]
        if not np.array_equal(got, want):
            n = int((got != want).sum())
            raise SystemExit(
                f"{stem}: {n:,} published cells hold a {name} that is not the {name} of the "
                "source cell the reprojection says fed them. Two of these planes were resampled "
                "from different source cells, so some household would be shown one cell's "
                "journey beside another cell's destination")
        # A cell no source cell covers must hold the fill the format defines for it, not a value
        # resampling happened to leave behind.
        uncovered = plane[~covered]
        if name == "value" and uncovered.size and not (uncovered == wire.VALUE_NONE).all():
            raise SystemExit(f"{stem}: an uncovered published cell carries a value")
        if name == "status" and uncovered.size and not (uncovered == wire.OUTSIDE).all():
            raise SystemExit(f"{stem}: an uncovered published cell carries a status other than "
                             "OUTSIDE, which is the one thing v1 could not say")
        if name == "destination" and uncovered.size and not (uncovered == wire.DEST_NONE).all():
            raise SystemExit(f"{stem}: an uncovered published cell names a destination")
    return {
        "cells_traced_to_a_source_cell": int(covered.sum()),
        "cells_no_source_covers": int((~covered).sum()),
        "planes_compared": sorted(published),
        "what_this_establishes": (
            "every listed plane at every covered cell equals that plane's value at the source "
            "cell a jointly reprojected index says fed it. The destination plane's "
            "two-directional invariant does not establish this: it compares answer-presence "
            "masks and never reads a value, so exchanging two valid destinations between two OK "
            "cells passes it and fails here"),
        "what_this_does_not_establish": (
            "physical source-cell identity. Two source cells holding the same value are "
            "indistinguishable to this comparison, so it is an output-VALUE consistency check "
            "rather than a provenance proof -- pass 50 finding A1. What a household would be "
            "shown is nonetheless pinned, because a value that is right for the cell the "
            "reprojection names is the value that cell's journey produced"),
    }


def deflated(data: bytes) -> int:
    return len(zlib.compress(data, 9))


def v1_plane(value: np.ndarray, status: np.ndarray) -> np.ndarray:
    """The single plane v1 would have written: minutes where OK, `255` everywhere else.

    Pass 43 F5: the first version compared v2's two planes against **v2's own value plane**, which
    carries a lower bound at every missing cell. v1 stored `NODATA` there, and a constant
    compresses far better than a bound, so the baseline was too large and the reported overhead
    too small -- 9% where the true figure is 18%.
    """
    return np.where(status == wire.OK, value, 255).astype(np.uint8)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidates", action="store_true",
                    help="also export the rejected 200 m candidate. Pass 43 F4: every manifest "
                         "entry starts enabled in the page, so shipping the candidate beside the "
                         "product made the default answer the INTERSECTION of two versions of one "
                         "criterion, which removed 4,022 passing pixels at the default threshold")
    ap.add_argument("--nrows", type=int, default=514)
    ap.add_argument("--ncols", type=int, default=643)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    args = ap.parse_args(argv)

    e = METRO.evaluation
    bounds = (e.west, e.south, e.east, e.north)
    args.out.mkdir(parents=True, exist_ok=True)

    entries = []
    sizes = []
    published_tables = []   # every side table that actually ships, for the licence bundle
    releases = set()        # the Overture releases those tables name
    for stem, label, cell_m in SOURCES:
        if cell_m != 100.0 and not args.candidates:
            continue
        if not (LAYERS / f"{stem}.npy").exists():
            print(f"  skipping {stem}: not on disk")
            continue
        surf, build = load_surface(stem)
        value, status = wire.encode_planes(surf)
        fingerprint = wire.surface_fingerprint(surf.seconds, surf.reason)
        raw_flag = load_route_flag(stem, value.shape, surf.horizon_s, fingerprint=fingerprint)
        raw_dest, dest_table = load_selected_destination(
            stem, value.shape, surf.horizon_s, fingerprint=fingerprint)
        dest = (None if raw_dest is None
                else wire.encode_selected_destination(raw_dest, status))
        flag = None if raw_flag is None else wire.encode_route_flag(raw_flag, status)
        transform, crs = source_transform(build, value.shape)

        # The value plane's fill is VALUE_NONE, which carries no time and no bound. The status
        # plane's fill is OUTSIDE, which is the thing v1 could not say: a pixel this export covers
        # and the source did not.
        v = reproject_plane(value, transform, crs, src_fill=wire.VALUE_NONE,
                            dst_fill=wire.VALUE_NONE, bounds=bounds,
                            nrows=args.nrows, ncols=args.ncols)
        s = reproject_plane(status, transform, crs, src_fill=wire.OUTSIDE,
                            dst_fill=wire.OUTSIDE, bounds=bounds,
                            nrows=args.nrows, ncols=args.ncols)
        # A status code that survived reprojection must still be one we define. Nearest never
        # invents a value, so this is a guard against a future resampling change, not a live path.
        unknown = sorted(set(np.unique(s).tolist()) - set(wire.STATUS_CODES))
        if unknown:
            raise SystemExit(f"{stem}: reprojection produced undefined status codes {unknown}")

        vb, sb = v.tobytes(), s.tobytes()
        (args.out / f"{stem}.value.bin").write_bytes(vb)
        (args.out / f"{stem}.status.bin").write_bytes(sb)
        entry = {
            "id": stem, "label": label, "engine": build["engine"], "mode": build["mode"],
            "category": build["category"], "cell_m": cell_m,
            "horizon_s": surf.horizon_s,
            "value_file": f"{stem}.value.bin", "status_file": f"{stem}.status.bin",
            "source_shape": list(value.shape),
        }
        db = None
        if dest is not None:
            dplane = reproject_plane(dest, transform, crs, src_fill=wire.DEST_NONE,
                                     dst_fill=wire.DEST_NONE, bounds=bounds,
                                     nrows=args.nrows, ncols=args.ncols, dtype=wire.DEST_DTYPE)
            # BOTH directions, on the reprojected planes. The value, status and destination planes
            # are three independent nearest calls; pass 48 measured 0 of 330,502 shipped cells
            # taking a mixed triple, and this is the first check that would CATCH one, because a
            # status from one source cell beside a sentinel from another is a contradiction.
            orphan = (dplane != wire.DEST_NONE) & (s != wire.OK)
            missing = (dplane == wire.DEST_NONE) & (s == wire.OK)
            if orphan.any() or missing.any():
                raise SystemExit(
                    f"{stem}: after reprojection {int(orphan.sum())} cells name a destination with "
                    f"no published journey and {int(missing.sum())} publish a time with no "
                    "destination. Nearest resampling moved the planes apart, so some shipped cell "
                    "holds one source cell's status beside another's destination")
            db = wire.destination_plane_bytes(dplane)
            (args.out / f"{stem}.dest.bin").write_bytes(db)
            (args.out / f"{stem}.destinations.json").write_text(
                json.dumps(dest_table, indent=2, allow_nan=False), encoding="utf-8")
            published_tables.append(dest_table)
            source = (dest_table.get("licence") or {}).get("source")
            if source:
                releases.add(str(source))
            entry["dest_file"] = f"{stem}.dest.bin"
            entry["dest_table"] = f"{stem}.destinations.json"
            entry["dest_byte_order"] = wire.DEST_BYTE_ORDER
            entry["dest_none"] = int(wire.DEST_NONE)
            entry["named_cells"] = int((dplane != wire.DEST_NONE).sum())
            entry["distinct_destinations"] = int(np.unique(
                dplane[dplane != wire.DEST_NONE]).size)

        fb = None
        if flag is not None:
            # Uncovered pixels become ROUTE_CLEAR, which is safe only because the status plane
            # marks them OUTSIDE: a zero flag at a cell with no published answer discloses
            # nothing, and `wire.encode_route_flag` enforces that a SET flag implies status OK.
            fplane = reproject_plane(flag, transform, crs, src_fill=wire.ROUTE_CLEAR,
                                     dst_fill=wire.ROUTE_CLEAR, bounds=bounds,
                                     nrows=args.nrows, ncols=args.ncols)
            bad = (fplane == wire.ROUTE_RESTRICTED) & (s != wire.OK)
            if bad.any():
                raise SystemExit(
                    f"{stem}: {int(bad.sum())} reprojected cells carry a route flag where the "
                    "status is not OK; nearest resampling moved the two planes apart")
            fb = fplane.tobytes()
            (args.out / f"{stem}.flag.bin").write_bytes(fb)
            entry["flag_file"] = f"{stem}.flag.bin"
            entry["flagged_cells"] = int((fplane == wire.ROUTE_RESTRICTED).sum())

        # ------------------------------------------------------------ pass 49 finding 1
        # The real provenance check, and the reason the two-directional invariant is not one.
        #
        # That invariant compares the destination plane's answer-PRESENCE mask against the status
        # plane's. Exchange two valid destinations between two OK cells and both directions still
        # hold, every aggregate is unchanged, and two journeys are misidentified -- Codex did
        # exactly that on the shipped plane and nothing noticed. The claim that it was "the first
        # check that would CATCH a mixed triple" is withdrawn: it never inspects a value.
        #
        # What does catch one: reproject a SOURCE-CELL IDENTIFIER through the same nearest call,
        # then require every published plane at every cell to equal its source plane at the cell
        # the identifier names. Three independent nearest calls that disagree about which source
        # cell fed a published cell cannot survive this, whatever the values happen to be.
        provenance_checked = verify_provenance(
            stem, transform, crs, bounds, args.nrows, args.ncols,
            source={"value": value, "status": status,
                    **({"destination": dest} if dest is not None else {}),
                    **({"flag": flag} if flag is not None else {})},
            published={"value": v, "status": s,
                       **({"destination": dplane} if dest is not None else {}),
                       **({"flag": fplane} if flag is not None else {})})
        entry["planes_share_a_source_cell"] = provenance_checked
        entries.append(entry)
        sizes.append({
            "id": stem,
            "raw_bytes": len(vb) + len(sb) + (len(fb) if fb else 0) + (len(db) if db else 0),
            "deflated_value": deflated(vb), "deflated_status": deflated(sb),
            "deflated_flag": deflated(fb) if fb else None,
            "deflated_dest": deflated(db) if db else None,
            "deflated_total": (deflated(vb) + deflated(sb) + (deflated(fb) if fb else 0)
                               + (deflated(db) if db else 0)),
            "v1_raw_bytes": len(vb),
            "v1_deflated": deflated(v1_plane(v, s).tobytes()),
            "status_counts": {wire.STATUS_CODES[int(c)]: int(n)
                              for c, n in zip(*np.unique(s, return_counts=True))},
        })

    if not entries:
        raise SystemExit("nothing to export")

    licensing = (write_licence_bundle(args.out, published_tables, releases)
                 if published_tables else None)

    manifest = {
        "encoding": wire.ENCODING,
        # `None`, not `{}`, where nothing with a licence obligation ships: "this bundle carries no
        # third-party names" and "this bundle ships names and says nothing about their licence"
        # are different statements, and the second one is the bug.
        "licensing": licensing,
        "discloses_restricted_routes": any("flag_file" in e for e in entries),
        "names_selected_destinations": any("dest_file" in e for e in entries),
        "what_an_absent_destination_plane_means": (
            "that the layer does not say WHICH destination its times were measured to, NOT that "
            "there is no destination. A decoder must report that distinction"),
        "a_destination_is_a_node_and_not_a_shop": (
            "the plane names a node and the side table carries every place on it. The selection "
            "is a cost-argmin over nodes, so where a node holds more than one place the pipeline "
            "did not choose between them and no consumer may present one as THE destination. The "
            "owner's rule, 2026-11-13: the node plus the set, and the card chooses"),
        "destination_plane_byte_order": wire.DEST_BYTE_ORDER,
        "why_the_destination_plane_declares_a_byte_order": (
            "it is the only uint16 plane. Read with the wrong order its ordinals are VALID -- they "
            "index real destinations -- and wrong, which produces a confident incorrect shop name "
            "rather than an error. A decoder that cannot confirm the order must refuse the plane"),
        "what_an_absent_flag_plane_means": (
            "that the layer does not disclose, NOT that no route is restricted. A decoder must "
            "report that distinction rather than defaulting to clean"),
        "route_flag_codes": {str(k): v for k, v in wire.ROUTE_FLAG_CODES.items()},
        "nrows": args.nrows, "ncols": args.ncols,
        "bounds_wgs84": list(bounds),
        "units": "minutes",
        "value_means": ("travel time where status is OK; a LOWER BOUND on it where status is "
                        "OFF_NETWORK, BEYOND_HORIZON or NO_PATH; nothing otherwise"),
        "status_codes": {str(k): v for k, v in wire.STATUS_CODES.items()},
        "value_none": wire.VALUE_NONE, "value_max": wire.VALUE_MAX,
        "generator": "v2/scripts/export_published_layers.py",
        "synthetic": False,
        "note": ("Reprojected from UTM 17N (EPSG:32617) to a WGS84 lon/lat grid with "
                 "rasterio.warp.reproject, NEAREST for both planes: a status code is a name and a "
                 "minute is a decision input, and averaging either publishes something nobody "
                 "computed. Uncovered pixels are OUTSIDE, which decodes to UNKNOWN."),
        "layers": entries,
        "transfer_bytes": sizes,
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")

    print(f"wrote {len(entries)} layers to {args.out}")
    print(f"\n{'layer':30s} {'raw':>10s} {'deflated':>10s} {'flag':>9s} {'dest':>9s} "
          f"{'v1 defl.':>10s} {'ratio':>6s}")
    for s in sizes:
        fl = f"{s['deflated_flag']:,}" if s["deflated_flag"] is not None else "-"
        de = f"{s['deflated_dest']:,}" if s.get("deflated_dest") is not None else "-"
        print(f"{s['id']:30s} {s['raw_bytes']:>10,} {s['deflated_total']:>10,} {fl:>9s} "
              f"{de:>9s} {s['v1_deflated']:>10,} "
              f"{s['deflated_total'] / s['v1_deflated']:>6.2f}x")
    for s in sizes:
        print(f"\n{s['id']} status plane: {s['status_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
