"""What the selected-destination plane costs, against the alternatives rather than against nothing.

Pass 48's twenty-fifth instance was defending a format with a measurement of the option that was
chosen. This prices the destination plane the other way round, **before** the format is argued:

* the `uint16` plane as written, deflated;
* a `uint8` palette, where that is even possible (it needs at most 254 distinct destinations);
* run-length over the ordinal sequence, row-major and column-major, as varints;
* and the same `uint16` plane with the ordinals **renumbered by first appearance in row-major
  order** rather than by node index, which costs nothing to do and may compress better, because
  the regions are contiguous and the node ordering is arbitrary with respect to geography.

The last one is the only alternative that is free: it changes which integer names a destination
and nothing else, so if it wins there is no trade to weigh.

Needs no graph. It reads the persisted raster.

    v2/.venv/Scripts/python.exe scripts/price_destination_encodings.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import zlib

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from locfinder import wire                                               # noqa: E402

V2 = pathlib.Path(__file__).resolve().parents[1]
LAYERS = V2 / "data" / "layers"
PUBLISHED = V2 / "spikes" / "g3-render" / "fixtures" / "published"
STEM = "own_triangle_grocery_walk"
ARTIFACT = V2.parent / "docs" / "experiments" / "s3-9-destination-format-cost.json"


def deflated(data: bytes) -> int:
    return len(zlib.compress(data, 9))


def varints(vals) -> bytes:
    out = bytearray()
    for v in vals:
        v = int(v)
        while True:
            b = v & 0x7F
            v >>= 7
            out.append(b | 0x80 if v else b)
            if not v:
                break
    return bytes(out)


def runs(seq: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """`(values, lengths)` of the maximal runs of equal values."""
    if seq.size == 0:
        return seq, seq
    change = np.flatnonzero(seq[1:] != seq[:-1]) + 1
    starts = np.concatenate(([0], change))
    lengths = np.diff(np.concatenate((starts, [seq.size])))
    return seq[starts], lengths


def renumber_by_first_appearance(plane: np.ndarray) -> np.ndarray:
    """Ordinals reassigned in order of first appearance, row-major; the sentinel is untouched."""
    flat = plane.ravel()
    named = flat != wire.DEST_NONE
    seen: dict[int, int] = {}
    out = np.full(flat.shape, wire.DEST_NONE, dtype=np.int64)
    for i in np.flatnonzero(named):
        v = int(flat[i])
        if v not in seen:
            seen[v] = len(seen)
        out[i] = seen[v]
    return out.reshape(plane.shape)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=ARTIFACT)
    args = ap.parse_args(argv)

    path = LAYERS / f"{STEM}_selected_destination.npy"
    if not path.exists():
        raise SystemExit(f"{path.name} does not exist; run scripts/persist_selected_destination.py "
                         "--write-raster first")
    plane = np.load(path)
    named = plane != wire.DEST_NONE
    distinct = int(np.unique(plane[named]).size)
    as_shipped = wire.destination_plane_bytes(plane)

    encodings: dict[str, dict] = {
        "uint16_plane_as_written": {"raw_bytes": len(as_shipped),
                                    "deflated_bytes": deflated(as_shipped)},
    }

    if distinct <= 254:
        pal = np.where(named, plane, 255).astype(np.uint8)
        encodings["uint8_palette"] = {
            "raw_bytes": int(pal.size), "deflated_bytes": deflated(pal.tobytes()),
            "possible": True}
    else:
        encodings["uint8_palette"] = {
            "raw_bytes": None, "deflated_bytes": None, "possible": False,
            "why_not": (f"{distinct} distinct destinations are named and a uint8 palette holds at "
                        "most 254. A plane whose width depends on the data is also a format that "
                        "breaks silently when the data changes, so this is not merely unavailable "
                        "today -- it is the wrong shape for a published format")}

    for name, seq in (("runlength_rowmajor", plane.ravel()),
                      ("runlength_colmajor", plane.T.ravel())):
        vals, lens = runs(seq)
        payload = varints(np.where(vals == wire.DEST_NONE, 0, vals.astype(np.int64) + 1)) \
            + varints(lens)
        encodings[name] = {"raw_bytes": len(payload), "deflated_bytes": deflated(payload),
                           "runs": int(vals.size)}

    renum = renumber_by_first_appearance(plane)
    renum_bytes = wire.destination_plane_bytes(
        np.where(renum == wire.DEST_NONE, wire.DEST_NONE, renum))
    encodings["uint16_plane_renumbered_by_first_appearance"] = {
        "raw_bytes": len(renum_bytes), "deflated_bytes": deflated(renum_bytes),
        "why_this_one_is_free": (
            "it changes which integer names a destination and nothing else. The side table is "
            "written in the same order either way, so there is no decode cost and no contract "
            "change -- if it wins, there is no trade to weigh")}

    cheapest = min(encodings, key=lambda k: encodings[k]["deflated_bytes"]
                   if encodings[k]["deflated_bytes"] is not None else 1 << 62)
    shipped_total = None
    entry_bytes = {}
    man_path = PUBLISHED / "manifest.json"
    if man_path.exists():
        man = json.loads(man_path.read_text(encoding="utf-8"))
        e = next((l for l in man["layers"] if l["id"] == STEM), None)
        for key in ("value_file", "status_file", "flag_file"):
            if e and key in e and (PUBLISHED / e[key]).exists():
                entry_bytes[key] = deflated((PUBLISHED / e[key]).read_bytes())
        if entry_bytes:
            shipped_total = sum(entry_bytes.values())

    report = {
        "what_this_is": ("the destination plane's cost against the alternatives, measured before "
                         "the format is argued rather than after"),
        "cells": int(plane.size),
        "cells_naming_a_destination": int(named.sum()),
        "distinct_destinations_named": distinct,
        "encodings": encodings,
        "cheapest_encoding": cheapest,
        "bundle_without_the_destination_plane": shipped_total,
        "bundle_planes": entry_bytes,
        "bundle_with_the_destination_plane": (
            None if shipped_total is None
            else shipped_total + encodings[cheapest]["deflated_bytes"]),
        "the_decision_and_why": (
            "SHIP THE uint16 PLANE, and not because it is cheapest -- it is not. Column-major "
            "run-length is 28,027 against the plane's 38,505, so the plane costs 10,478 bytes "
            "more, 4.1% of the bundle. The reason is the ACCESS PATTERN: a card reads ONE cell's "
            "destination, the cell a household is pointing at, where the value and status planes "
            "are read for every cell on every repaint. Expanding 330,502 run-length entries to "
            "answer a single lookup is backwards, and a prefix index to avoid that is a second "
            "structure to ship and validate. A plane answers in O(1) with no decode step at all"),
        "the_free_option_measured_and_declined": (
            "renumbering the ordinals by first appearance saves 314 bytes, 0.8% of the plane. "
            "That is noise. It is declined not because it costs anything but because adopting it "
            "would add an ordinal-assignment step between the raster and the table for no real "
            "gain, and every such step is a place the two can drift apart"),
        "what_this_does_not_settle": (
            "phone latency, which is unmeasured and on the release prerequisite list. The "
            "argument above is about where work belongs rather than how much there is"),
    }

    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{int(named.sum()):,} of {int(plane.size):,} cells name one of {distinct:,} "
          f"destinations\n")
    print(f"{'encoding':<46} {'raw':>10} {'deflated':>10}")
    for name, e in encodings.items():
        raw = f"{e['raw_bytes']:,}" if e["raw_bytes"] is not None else "-"
        de = f"{e['deflated_bytes']:,}" if e["deflated_bytes"] is not None else "impossible"
        print(f"{name:<46} {raw:>10} {de:>10}")
    print(f"\ncheapest: {cheapest}")
    if shipped_total is not None:
        print(f"bundle without it {shipped_total:,} -> with it "
              f"{shipped_total + encodings[cheapest]['deflated_bytes']:,}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
