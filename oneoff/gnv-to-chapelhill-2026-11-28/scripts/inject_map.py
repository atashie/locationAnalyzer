"""Splice build/mapdata.json into planner.html, replacing the __MAPDATA__ token.

Keeps planner.html self-contained (the artifact CSP blocks external fetches)
while leaving the geometry reproducible from scripts/build_map.py.
"""

import pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent
page = HERE / "planner.html"
data = (HERE / "build" / "mapdata.json").read_text()

src = page.read_text(encoding="utf-8")
token = "__MAPDATA__"
if token not in src:
    raise SystemExit("token already injected or missing; nothing to do")
page.write_text(src.replace(token, data), encoding="utf-8")
print(f"injected {len(data)} bytes of map geometry")
