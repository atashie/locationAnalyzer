"""Raise Valhalla service limits needed by the category-layer experiment (Task 7 method A:
one multi-location arrival isochrone). Edits v2/data/valhalla_custom_files/valhalla.json in
place and prints the before/after values; restart the container afterwards:

    uv run python infra/valhalla/patch_limits.py
    wsl -e bash -lc "cd /mnt/c/Users/arikt/documents/github/distanceFinder/v2/infra/valhalla && docker compose restart"

Defaults in Valhalla are small (isochrone max_locations is 1). We raise them for the
local experiment only; a public deployment must set its own limits deliberately.
"""
from __future__ import annotations

import json
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[2] / "data" / "valhalla_custom_files" / "valhalla.json"
WANT = {
    ("service_limits", "isochrone", "max_locations"): 1000,
    ("service_limits", "isochrone", "max_time_contour"): 120,
    ("service_limits", "isochrone", "max_distance_contour"): 200,
    ("service_limits", "isochrone", "max_distance"): 250000,
    ("service_limits", "isochrone", "max_contours"): 12,
    ("service_limits", "pedestrian", "max_distance"): 250000,
    ("service_limits", "bicycle", "max_distance"): 250000,
    ("service_limits", "auto", "max_distance"): 500000,
}


def main() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    for path, value in WANT.items():
        node = cfg
        for key in path[:-1]:
            node = node.setdefault(key, {})
        before = node.get(path[-1])
        node[path[-1]] = value
        print(".".join(path), before, "->", value)
    CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8", newline="\n")
    print("patched", CONFIG)


if __name__ == "__main__":
    main()
