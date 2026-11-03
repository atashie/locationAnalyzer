"""Gate G1 comparison: own-graph vs Valhalla float-second layers on the frozen grid.

Owner decision 12: at a user threshold T, median absolute error <= 0.10*T and p90 <= 0.20*T,
evaluated on cells near the boundary (reference in [0.8T, 1.2T]). Codex pass 3 (H6/H9):
use float seconds, evaluate the UNION of reachable cells so one-sided unreachability counts,
report false inclusion/exclusion with explicit denominators, and report the one-way-adjacent
subset separately.

Run from v2/:
  uv run python spikes/g1_compare.py data/layers/own_grocery_walk.npy data/layers/valhalla_grocery_walk_controlled.npy "grocery walk controlled" [--oneway data/layers/own_walk_oneway_mask.npy]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import append_results, stamp  # noqa: E402

THRESHOLDS_MIN = [10, 15, 20, 25, 30, 45]


def table(own_s: np.ndarray, ref_s: np.ndarray, label: str) -> list[str]:
    own, ref = own_s / 60.0, ref_s / 60.0
    fo, fr = np.isfinite(own), np.isfinite(ref)
    union, both = fo | fr, fo & fr
    lines = [f"#### {label}",
             f"cells: union reachable {int(union.sum())}; both {int(both.sum())}; own-only {int((fo & ~fr).sum())}; ref-only {int((~fo & fr).sum())}",
             "", "| T min | n boundary (ref in [0.8T,1.2T]) | one-sided there | median abs err min | p90 abs err min | median/T | p90/T | false include | false exclude | PASS (acc) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for T in THRESHOLDS_MIN:
        near = fr & (ref >= 0.8 * T) & (ref <= 1.2 * T)
        near_both = near & fo
        one_sided = int((near & ~fo).sum())
        if near_both.sum() < 50:
            lines.append(f"| {T} | {int(near.sum())} | {one_sided} | - | - | - | - | - | - | n/a (<50 cells) |")
            continue
        err = np.abs(own[near_both] - ref[near_both])
        med, p90 = float(np.median(err)), float(np.percentile(err, 90))
        own_in = fo & (own <= T)
        ref_in = fr & (ref <= T)
        ref_out = union & ~ref_in
        fi = float((own_in & ref_out).sum() / max(ref_out.sum(), 1))   # own says in, ref says out or unreachable
        fe = float((~own_in & ref_in).sum() / max(ref_in.sum(), 1))    # own says out/unreachable, ref says in
        ok = med <= 0.10 * T and p90 <= 0.20 * T
        lines.append(f"| {T} | {int(near.sum())} | {one_sided} | {med:.1f} | {p90:.1f} | {med / T:.2f} | {p90 / T:.2f} | {fi:.1%} | {fe:.1%} | {'PASS' if ok else 'FAIL'} |")
    lines.append("")
    lines.append("Accuracy PASS is necessary, not sufficient: one-sided unreachability near the boundary and false include/exclude rates must be judged against decision 12 in the verdict.")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("own_npy")
    ap.add_argument("ref_npy")
    ap.add_argument("label")
    ap.add_argument("--oneway", default=None, help="boolean .npy mask of one-way-adjacent cells (own graph)")
    args = ap.parse_args()
    own = np.load(args.own_npy).astype(np.float64)
    ref = np.load(args.ref_npy).astype(np.float64)
    assert own.shape == ref.shape, (own.shape, ref.shape)
    lines = [f"### G1 comparison ({stamp()}): {args.label}", f"own={Path(args.own_npy).name} ref={Path(args.ref_npy).name}", ""]
    lines += table(own, ref, "all cells")
    if args.oneway:
        m = np.load(args.oneway).astype(bool)
        lines += [""] + table(np.where(m, own, np.inf), np.where(m, ref, np.inf), f"one-way-adjacent cells only (n={int(m.sum())})")
    text = "\n".join(lines)
    print(text)
    append_results("g1-routing.md", text)


if __name__ == "__main__":
    main()
