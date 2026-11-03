"""Gate G2 part 2: isochrone latency for fixed, routable anchors in the active metro.

Measures p50/p95/max per (costing, minutes) at concurrency 1 and 8, records every
failure with its case identity and error body (Codex pass 3 H9), separates a cold
pass from a warm pass, and includes two deliberately off-network anchors to see how
the engine fails. Appends a results section to docs/experiments/g2-valhalla.md.

Run from v2/ with Valhalla serving. Target and label are environment-driven:
  uv run python spikes/g2_anchor_bench.py                       # default metro, VALHALLA_URL
  VALHALLA_URL=http://localhost:8003 G2_LABEL=north-carolina uv run python spikes/g2_anchor_bench.py
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import statistics
import time
from pathlib import Path

import httpx

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DATA, METRO, RESULTS, VALHALLA  # noqa: E402

URL = f"{VALHALLA}/isochrone"
LABEL = os.environ.get("G2_LABEL", "slice")
OUT_MD = RESULTS / "g2-valhalla.md"
OUT_JSON = DATA / f"g2_anchor_bench_{LABEL}.json"

# Fixed, reproducible anchors (lat, lon). Routable set: known places in the slice.
ROUTABLE = {
    "UNC Hospitals": (35.9049, -79.0469),
    "Duke University Hospital": (36.0075, -78.9381),
    "RTP Fidelity (Kit Creek Rd)": (35.8720, -78.8450),
    "Downtown Durham (Main & Mangum)": (35.9960, -78.9010),
    "Carrboro Town Hall": (35.9100, -79.0750),
    "Cary Downtown Park": (35.7880, -78.7810),
    "RDU Terminal 2": (35.8776, -78.7875),
    "Hillsborough Courthouse": (36.0750, -79.0990),
    "Southpoint Mall": (35.9050, -78.9450),
    "NC State Bell Tower": (35.7860, -78.6630),
}
random.seed(42)
_E = METRO.evaluation
BBOX = (_E.west, _E.south, _E.east, _E.north)
RANDOM = {f"random-{i:02d}": (random.uniform(BBOX[1], BBOX[3]), random.uniform(BBOX[0], BBOX[2])) for i in range(90)}
OFF_NETWORK = {"Jordan Lake (water)": (35.7400, -79.0300), "Falls Lake (water)": (36.0150, -78.7000)}
ANCHORS = {**ROUTABLE, **RANDOM, **OFF_NETWORK}
CASES = [("auto", 25), ("auto", 45), ("bicycle", 15), ("pedestrian", 15)]


async def one(client: httpx.AsyncClient, name: str, lat: float, lon: float, costing: str, minutes: int) -> dict:
    body = {"locations": [{"lat": lat, "lon": lon}], "costing": costing, "contours": [{"time": minutes}],
            "polygons": True, "reverse": True}
    t0 = time.perf_counter()
    try:
        r = await client.post(URL, json=body, timeout=90)
        dt = time.perf_counter() - t0
        ok = r.status_code == 200
        return {"anchor": name, "costing": costing, "minutes": minutes, "ok": ok, "status": r.status_code,
                "seconds": dt, "bytes": len(r.content), "error": None if ok else r.text[:200]}
    except Exception as e:  # noqa: BLE001 - we want every failure recorded, not raised
        return {"anchor": name, "costing": costing, "minutes": minutes, "ok": False, "status": None,
                "seconds": time.perf_counter() - t0, "bytes": 0, "error": repr(e)[:200]}


async def run(concurrency: int, anchors: dict) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient() as client:
        async def guarded(name, a, c):
            async with sem:
                return await one(client, name, a[0], a[1], c[0], c[1])
        return list(await asyncio.gather(*[guarded(n, a, c) for c in CASES for n, a in anchors.items()]))


def summarize(rows: list[dict], label: str) -> list[str]:
    out = [f"\n#### {label}", "", "| costing | minutes | n | ok | failed | p50 s | p95 s | max s | median KB |", "|---|---|---|---|---|---|---|---|---|"]
    for costing, minutes in CASES:
        sel = [r for r in rows if r["costing"] == costing and r["minutes"] == minutes]
        ok = sorted(r["seconds"] for r in sel if r["ok"])
        failed = [r for r in sel if not r["ok"]]
        if not ok:
            out.append(f"| {costing} | {minutes} | {len(sel)} | 0 | {len(failed)} | - | - | - | - |")
            continue
        p95 = ok[max(int(round(0.95 * len(ok))) - 1, 0)]
        kb = statistics.median(r["bytes"] for r in sel if r["ok"]) / 1024
        out.append(f"| {costing} | {minutes} | {len(sel)} | {len(ok)} | {len(failed)} | {statistics.median(ok):.3f} | {p95:.3f} | {ok[-1]:.3f} | {kb:.0f} |")
    fails = [r for r in rows if not r["ok"]]
    if fails:
        out += ["", "Failures (anchor, case, status, error):"]
        out += [f"- {r['anchor']} / {r['costing']} {r['minutes']} min / {r['status']} / {r['error']}" for r in fails[:20]]
        if len(fails) > 20:
            out.append(f"- ... {len(fails) - 20} more in {OUT_JSON.name}")
    return out


def main() -> None:
    outside = [n for n, (lat, lon) in ROUTABLE.items() if not METRO.evaluation.contains(lat, lon)]
    if outside:
        raise SystemExit(f"named anchors outside the {METRO.name} evaluation bbox: {outside}")
    lines = ["", f"## Anchor latency benchmark ({LABEL}, metro {METRO.name}, {URL})", f"run at {time.strftime('%Y-%m-%d %H:%M:%S')}; anchors={len(ANCHORS)} "
             f"({len(ROUTABLE)} named, {len(RANDOM)} random, {len(OFF_NETWORK)} off-network); cases={CASES}; reverse=true"]
    all_rows: dict[str, list[dict]] = {}
    # cold pass: routable named anchors only, concurrency 1
    all_rows["cold c=1 (named anchors)"] = asyncio.run(run(1, ROUTABLE))
    lines += summarize(all_rows["cold c=1 (named anchors)"], "cold, concurrency 1, named anchors")
    for c in (1, 8):
        key = f"warm c={c}"
        all_rows[key] = asyncio.run(run(c, ANCHORS))
        lines += summarize(all_rows[key], f"warm, concurrency {c}, all anchors")
    lines += ["", "Pass criterion (synthesis G2): auto 25 min p95 < 0.8 s and auto 45 min p95 < 2 s at concurrency 8, "
              "with an explicit, acceptable failure rate; peak memory from data/valhalla_mem_samples.txt is reported separately. "
              "Named anchors are asserted inside the metro evaluation bbox before the run (Codex pass 4 H4)."]
    text = "\n".join(lines)
    print(text)
    OUT_JSON.write_text(json.dumps(all_rows, indent=1), encoding="utf-8")
    with OUT_MD.open("a", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
