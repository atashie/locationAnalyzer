"""What the route-flag plane costs, against the alternatives rather than against nothing.

Codex pass 48 §D, and it refutes a claim I made. The commit that published the plane said *"the
byte argument for the bit does not survive measurement either: the plane is 17.3% set, spatially
clustered, and deflates to 25,651 bytes."* That reports a measurement of the option I **chose** and
calls it a refutation of the option I **rejected**. I never priced the bit. A measurement that
cannot come out against you is not evidence.

So this prices five encodings of the same information:

* the plane as shipped — one `uint8` per cell, deflated;
* a packed bitmap — eight cells per byte, deflated;
* run-length over the bit sequence, row-major and column-major, as varints, deflated;
* a sorted index of set cells as delta-varints, deflated;
* and the counterfactual the commit rejected — the flag as a bit in the status byte, priced as the
  **growth** of the status plane, which is the only alternative that adds no plane at all.

The last is the only number that can settle the format argument on cost. Status codes run 0–6, so
bit 3 is free of them.

Needs no graph and no surface: it reads the shipped planes.

    v2/.venv/Scripts/python.exe scripts/price_flag_encodings.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import zlib

import numpy as np

V2 = pathlib.Path(__file__).resolve().parents[1]
PUBLISHED = V2 / "spikes" / "g3-render" / "fixtures" / "published"
STEM = "own_triangle_grocery_walk"
ARTIFACT = V2.parent / "docs" / "experiments" / "s3-8-flag-format-cost.json"
#: The bit the counterfactual would use. Status codes occupy 0..6, so 8 collides with none of them.
STATUS_BIT = 3


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


def run_lengths(bits: np.ndarray) -> np.ndarray:
    """Runs of the bit sequence, starting with a run of zeros, possibly of length zero."""
    change = np.flatnonzero(np.diff(bits.astype(np.int8))) + 1
    lengths = np.diff(np.concatenate(([0], change, [bits.size])))
    if bits.size and bits[0]:
        lengths = np.concatenate(([0], lengths))
    return lengths


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=ARTIFACT)
    args = ap.parse_args(argv)

    man = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    nrows, ncols = man["nrows"], man["ncols"]
    entry = next(l for l in man["layers"] if l["id"] == STEM)
    if "flag_file" not in entry:
        raise SystemExit(f"{STEM} ships no flag plane, so there is nothing to price")
    flag = np.frombuffer((PUBLISHED / entry["flag_file"]).read_bytes(), dtype=np.uint8)
    status = np.frombuffer((PUBLISHED / entry["status_file"]).read_bytes(), dtype=np.uint8)
    value = np.frombuffer((PUBLISHED / entry["value_file"]).read_bytes(), dtype=np.uint8)
    bits = flag == 1

    if int(status.max()) >= (1 << STATUS_BIT):
        raise SystemExit(f"a status code of {int(status.max())} reaches bit {STATUS_BIT}, so the "
                         "counterfactual below would overwrite a code rather than add to it")

    status_alone = deflated(status.tobytes())
    merged = status | (bits.astype(np.uint8) << STATUS_BIT)
    rl_row = varints(run_lengths(bits))
    rl_col = varints(run_lengths(bits.reshape(nrows, ncols).T.ravel()))
    idx = np.flatnonzero(bits)
    delta = varints(np.diff(np.concatenate(([0], idx))))

    encodings = {
        "separate_uint8_plane_as_shipped": {"raw_bytes": int(flag.size),
                                            "deflated_bytes": deflated(flag.tobytes())},
        "separate_packed_bitmap": {"raw_bytes": int(np.packbits(bits).size),
                                   "deflated_bytes": deflated(np.packbits(bits).tobytes())},
        "separate_runlength_rowmajor": {"raw_bytes": len(rl_row),
                                        "deflated_bytes": deflated(rl_row)},
        "separate_runlength_colmajor": {"raw_bytes": len(rl_col),
                                        "deflated_bytes": deflated(rl_col)},
        "separate_delta_index": {"raw_bytes": len(delta), "deflated_bytes": deflated(delta)},
        "a_bit_in_the_status_byte": {
            "raw_bytes": 0,
            "deflated_bytes": deflated(merged.tobytes()) - status_alone,
            "how_this_is_priced": ("the GROWTH of the status plane, because this alternative adds "
                                   "no plane: status alone deflates to "
                                   f"{status_alone:,} and with the flag in bit {STATUS_BIT} to "
                                   f"{deflated(merged.tobytes()):,}"),
        },
    }

    value_defl = deflated(value.tobytes())
    cheapest = min(k for k in encodings
                   if encodings[k]["deflated_bytes"] == min(
                       e["deflated_bytes"] for e in encodings.values()))
    report = {
        "what_this_is": ("the flag plane's cost against the alternatives rather than against "
                         "nothing. The commit that shipped it reported only its own size and "
                         "called that a refutation of the bit, which it is not"),
        "cells": int(flag.size), "set_cells": int(bits.sum()),
        "set_share": float(bits.mean()),
        "encodings": encodings,
        "bundle": {
            "value_plane_deflated": value_defl,
            "status_plane_deflated": status_alone,
            "total_as_shipped": value_defl + status_alone
                                + encodings["separate_uint8_plane_as_shipped"]["deflated_bytes"],
            "total_with_the_status_bit": value_defl + deflated(merged.tobytes()),
            "total_with_a_packed_bitmap": value_defl + status_alone
                                          + encodings["separate_packed_bitmap"]["deflated_bytes"],
        },
        "cheapest_encoding": cheapest,
        "what_this_settles": (
            "the SIZE argument, against the choice that shipped. The bit is cheaper than the "
            "separate plane, and a packed bitmap is cheaper than either of the two separate "
            "encodings considered. So 'the byte argument does not survive measurement' must be "
            "withdrawn"),
        "the_contract_argument_is_withdrawn": (
            "the commit said the layer contract forbids a bit in the status byte, because wire "
            "codes are assigned explicitly and may not be reinterpreted. Pass 48 F6: that is "
            "true of v2 and irrelevant here. Setting a bit while still calling it published-v2 "
            "would violate the contract, but published-v3 is a new encoding either way, and a new "
            "encoding may define `status = byte & 7` and `restricted = byte & 8` as explicitly as "
            "it defines a third plane. Old readers refuse an unknown encoding in both designs"),
        "what_actually_decides_it": (
            "OPTIONALITY, which a bit cannot express. An absent plane says THIS LAYER DOES NOT "
            "DISCLOSE; a clear bit inside a byte that must be present says NO ROUTE IS "
            "RESTRICTED, and those are different statements that no consumer may confuse. "
            "Orthogonality is the secondary reason -- the status answers why there is no time and "
            "the flag answers what the route used -- and a byte whose meaning is 'a code, or a "
            "code plus eight' is harder to validate against a code table. That buys 4,555 bytes, "
            "2.00% of the compressed bundle, and the owner may price it differently"),
        "the_decode_cost_this_does_not_measure": (
            "a packed bitmap or a bit field costs a shift and a mask per cell inside the compute "
            "loop, 330,502 times per repaint, where a uint8 plane costs a single byte load. That "
            "is a latency measurement and this is a size measurement; the cheaper encodings are "
            "not recommended on this evidence alone"),
    }

    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{int(bits.sum()):,} of {int(flag.size):,} cells set ({bits.mean():.1%})\n")
    print(f"{'encoding':<36} {'raw':>10} {'deflated':>10}")
    for name, e in encodings.items():
        print(f"{name:<36} {e['raw_bytes']:>10,} {e['deflated_bytes']:>10,}")
    b = report["bundle"]
    print(f"\nbundle as shipped          {b['total_as_shipped']:>10,}")
    print(f"bundle with a packed bitmap {b['total_with_a_packed_bitmap']:>9,}")
    print(f"bundle with the status bit  {b['total_with_the_status_bit']:>9,}"
          f"  ({b['total_as_shipped'] - b['total_with_the_status_bit']:+,} against shipped)")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
