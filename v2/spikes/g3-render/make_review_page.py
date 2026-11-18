"""Build a reviewable copy of this spike for publishing as a Claude Artifact.

**Why this exists.** The spike is normally read by running a static server on the loopback
interface, which means only the person at this machine can look at it. Owner request 2026-11-18:
*"recreate a version of the interactive html that you shared earlier in this session so that users
can review the current version."* A published copy needs no server and no checkout.

**Why it is a script and not a one-off edit.** `CLAUDE.md`: anything needed to rebuild a published
artifact is committed alongside it, because the generator for one live page once existed only in a
session temp directory. Run this and the published page is reproducible from the current spike.

**What it changes, and nothing else.** The point of a review copy is that it is the real page, so
the transform is deliberately minimal and every item here is forced by the artifact sandbox:

1. **The document skeleton is removed.** A published artifact supplies its own
   `<!doctype>`/`<html>`/`<head>`/`<body>` and a charset and viewport meta, so leaving ours in
   would nest one document inside another.
2. **MapLibre's stylesheet link is dropped.** The sandbox admits stylesheets from Google Fonts
   only; a cdnjs stylesheet is blocked silently. A small inline fallback replaces the few rules
   that matter, because this page adds no MapLibre controls of its own -- `app.js` constructs the
   map and nothing else. MapLibre's *script* is on the allowlist and still loads, pinned and with
   its SRI hash intact.
3. **The basemap is replaced by a blank tile served from the artifact itself.**
   `tile.openstreetmap.org` is not reachable from the sandbox, and `app.js` reports every map
   error in a red banner, so leaving it in would fill the page with blocked-request noise and look
   broken. The published `versions.json` points the raster source at `blank-tile.png`, a 256x256
   transparent PNG published beside the page, with the tile coordinates as a query string so each
   tile keeps a distinct cache key.
   **A `data:` URI does not work here and was tried first:** MapLibre's tile loader fetches
   through its AJAX path and rejects a `data:` URL outright --
   `AJAXError: Failed to fetch (0): data:image/png;base64,...` -- which produces exactly the error
   banner this is meant to avoid. A same-origin file does work.
   **Not loading OSM tiles into a shared page also happens to be the right thing**: the tile usage
   policy is for development and low volume, which a shared link is not.
4. **The `.bin` fixtures are renamed to `.wasm`, and `manifest.json` is rewritten to match.** A
   published artifact serves a fixed list of file types and `.bin` is not one of them, so the
   layers have to travel under a served *binary* extension. `.wasm` is the only one that is
   binary by nature, which matters: a text type risks the bytes being re-encoded on upload, and
   these are raw `uint8`/`uint16` planes. `app.js` fetches them with `arrayBuffer()` and checks
   every length against `nrows*ncols`, so a mangled file fails loudly rather than drawing a wrong
   map. No page code changes -- only the filenames inside the manifest.
5. **The app's height is pinned in viewport units.** `styles.css` sizes the app with
   `height: 100%` on `html` and `body`, and at >= 880px the map takes its height purely from the
   flex chain (`#map { height: auto; flex: 1; min-height: 0 }`). Inside the artifact skeleton that
   percentage resolves against a padded `:root` with no definite height, so the whole chain can
   collapse to zero and **the page renders blank** -- which it did, intermittently, depending on
   when layout ran. A viewport unit does not depend on an ancestor's height. This is an override
   in the review copy only; whether `styles.css` itself should stop relying on percentage
   inheritance is a separate question about the spike.
6. **A banner is added** stating all of the above on the page itself, so a reviewer is never
   working out for themselves why there is no map imagery.

Timings measured in the sandbox include its own overhead, so the committed numbers in
`docs/experiments/g3-rendering.md` remain the ones measured locally.

**FIXED 2026-11-18, second pass.** The mask did not paint and the MapLibre attribution control
did not appear, and both had one cause: the map container had no definite height when `app.js`
constructed the map, and a `canvas` source needs a laid-out container.

The diagnosis was right and the first fix was wrong in an instructive way. `styles.css` ALREADY
gives `#map` a definite height -- `height: 52vh; min-height: 260px` -- which needs no ancestor
height and works in the skeleton untouched. Only the `@media (min-width: 880px)` rule breaks it, by
handing the height to the flex chain from `html, body { height: 100% }`. So the whole fix is to put
the base rule back above 880px. The first attempt instead rewrote the ancestors' heights in `svh`
units, which left the mask broken and additionally killed the attribution control, whose container
is `position: absolute; inset: 0` against the map and so needs the same definite box.

**The lesson, since it is the second time this exact shape has come up: the page already contained
the rule that worked.** The failure was a narrower override sitting on top of it, and the fix was
to remove the override's effect rather than to invent a replacement for the thing underneath.

Two things were got wrong on the way and are recorded so they are not retried:

* **`#map { flex: none }` pushed the whole criteria panel off-screen.** `#map` carries
  `width: 100%` in the base rule, so with `flex: none` it takes the entire flex row. Only the
  HEIGHT properties may be overridden above 880px.
* **Dispatching `resize` on `window` does nothing, and the nudge that did it was removed.**
  MapLibre GL JS 5 watches the container with a `ResizeObserver`; the window event is not the
  thing it listens to. Five nudges over three seconds changed nothing, verified in a fresh tab.

**WHAT IS STILL NOT PERFECT, stated rather than implied by silence: the mask does not paint until
the MAP CONTAINER IS RESIZED.** It is computed and uploaded correctly on load. The trigger was
found by elimination, each tested in a fresh tab:

* panning or zooming the map -- **does not work**, though it does repaint the attribution;
* scrolling the page -- does not work; the page does not scroll;
* waiting 50 seconds -- does not work, so it is not the worker being slow;
* dispatching `resize` on `window` -- does not work, because MapLibre GL JS 5 watches the
  container with a `ResizeObserver` and the window event is not what it listens to. The nudge
  that did this was removed again rather than left in looking useful;
* the mouse wheel over the criteria panel -- does not work; the panel does not scroll that way;
* **DRAGGING THE CRITERIA PANEL'S SCROLLBAR -- works, reproduced twice in two tabs.** It relayouts
  the flex row, the container's size changes, the observer fires, everything repaints. The banner
  names this exact gesture rather than "scroll the panel", because the wheel does not do it and a
  banner that sends the reviewer to a gesture that fails is worse than no banner.

Fixing it properly needs `map.resize()` or `map.triggerRepaint()`, and the map object lives inside
`app.js`'s closure where an injected script cannot reach it. The alternative is editing the spike,
which this generator deliberately does not do -- a review copy is worth having precisely because it
is the real page. So the banner names the one gesture that works, which is a line of text rather
than a silent surprise.

The local server remains the only way to see the page with real basemap imagery:

    cd v2/spikes/g3-render && ../../.venv/Scripts/python.exe -m http.server 8099 --bind 127.0.0.1

One more trap worth recording, because it cost several reloads: **a tab that has been scrolled
renders the artifact blank on every later load**, scroll position being restored past the content.
A fresh tab renders it correctly. That is viewer state, not the page.

Run from `v2/`:
    python spikes/g3-render/make_review_page.py --out <build dir>

Then publish `<build dir>/index.html` as the page, with the spike's own `styles.css`, `geom.js`,
`card.js`, `app.js`, `worker.js`, `<build dir>/versions.json` and `fixtures/published/*` as the
supporting files.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent

#: Removed because the artifact supplies its own skeleton.
SKELETON = (
    "<!doctype html>",
    '<html lang="en">',
    "<head>",
    "</head>",
    "<body>",
    "</body>",
    "</html>",
    '<meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
)

#: The blocked stylesheet, matched as a block so a version bump cannot leave it behind silently.
MAPLIBRE_CSS = re.compile(
    r'\s*<!--.*?-->\s*<link rel="stylesheet"\s+href="https://cdnjs\.cloudflare\.com[^"]*'
    r'maplibre-gl\.css"\s+integrity="[^"]*"\s+crossorigin="anonymous">',
    re.S,
)

#: Replaces it. Only what this page actually needs: MapLibre's canvas must fill its container, and
#: the default attribution control must stay legible, since the spike adds no other controls.
FALLBACK_CSS = """  <style>
    /* MapLibre's own stylesheet is blocked by the artifact sandbox (stylesheets may only come
       from Google Fonts), so these are the few rules this page relies on. The spike adds no
       MapLibre controls beyond the default attribution, so nothing else is missing. */
    .maplibregl-map { position: relative; overflow: hidden; }
    .maplibregl-canvas-container, .maplibregl-canvas { position: absolute; top: 0; left: 0; }
    .maplibregl-canvas-container canvas { width: 100%; height: 100%; outline: none; }
    .maplibregl-control-container { position: absolute; inset: 0; pointer-events: none; }
    .maplibregl-ctrl-bottom-right {
      position: absolute; right: 0; bottom: 0; pointer-events: auto;
    }
    .maplibregl-ctrl-attrib {
      margin: 0; padding: 1px 6px; font-size: 11px; line-height: 1.5;
      background: rgba(255, 255, 255, 0.82); color: var(--muted);
    }
    .maplibregl-ctrl-attrib a { color: inherit; }
    .maplibregl-ctrl-attrib-button { display: none; }
  </style>"""

#: Must come AFTER the `styles.css` link, or the cascade drops it on the floor.
SIZING_OVERRIDE = """  <style>
    /* REVIEW COPY ONLY, and far smaller than it was. styles.css already gives `#map` a DEFINITE
       height -- `height: 52vh; min-height: 260px` -- which needs no ancestor height and works
       inside the artifact skeleton untouched. The only rule that breaks is the one at >= 880px,
       `#map { height: auto; flex: 1; min-height: 0 }`, which hands the map's height to the flex
       chain from `html, body { height: 100% }`; inside the skeleton that percentage resolves
       against a padded :root with no definite height and collapses to zero. A zero-height
       container at construction time is why the MASK DID NOT PAINT: `app.js` builds the map
       immediately and a `canvas` source needs a laid-out container.

       So the fix is to put the base rule back above 880px, and nothing else. The first attempt
       instead set `html, body { height: auto }` with `min-height` in `svh` units, which left the
       mask broken AND stopped the MapLibre attribution control appearing -- the control container
       is `position: absolute; inset: 0` against the map, so it needs the same definite box. */
    @media (min-width: 880px) {
      /* Override the HEIGHT properties only. `flex: 1` and the auto width have to survive,
         or the map takes the whole row and pushes the panel off-screen -- which is exactly what
         `flex: none` did on the first try at this. */
      #map { height: 52vh; min-height: 260px; }
    }
  </style>"""


STYLES_LINK = '<link rel="stylesheet" href="styles.css">'

BANNER = """  <div class="banner warn" id="banner-review">
    <strong>Published for review.</strong> This is the committed spike at
    <code>v2/spikes/g3-render/</code>, built by <code>make_review_page.py</code>. Three things
    differ from running it locally, all forced by the published sandbox:
    <strong>there is no basemap imagery</strong> &mdash; <code>tile.openstreetmap.org</code> is not
    reachable here, so the basemap is a blank tile and the overlay sits on empty ground (the OSM
    tile policy is for development and low volume anyway, which a shared link is not);
    <strong>MapLibre's own stylesheet is blocked</strong>, so a small fallback is inlined; and
    <strong>the timings include the sandbox's overhead</strong>, so read them as indicative &mdash;
    the committed numbers in <code>docs/experiments/g3-rendering.md</code> were measured locally.
    Everything else &mdash; the mask, the polygonizer, the per-cell card, the topology checks
    &mdash; is computed in this page and is the real thing.
    <br><br>
    <strong>Drag the scrollbar at the right edge of the criteria panel, and the overlay
    appears.</strong> It is computed correctly on load; MapLibre does not paint it until the map
    container is resized, and that drag is what relayouts the row. Tested and ruled out: panning
    or zooming the map, scrolling the page, the mouse wheel over the panel, and simply waiting.
    Everything behaves normally once it has appeared.
  </div>
"""


#: The published path of the blank basemap tile, referenced from `versions.json`.
BLANK_TILE = "blank-tile.png"


def blank_png(size: int = 256) -> bytes:
    """A fully transparent PNG, built here rather than pasted from memory.

    256x256 because that is `tileSize` in the style `app.js` builds; a 1x1 would be upscaled, and
    at zero alpha that is invisible either way, but matching the declared size keeps MapLibre off
    any rescaling path.
    """

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8-bit RGBA
    raw = b"".join(b"\x00" + b"\x00\x00\x00\x00" * size for _ in range(size))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    return png


def build_page(src: Path) -> str:
    text = src.read_text(encoding="utf-8")

    before = text
    text = MAPLIBRE_CSS.sub("\n" + FALLBACK_CSS, text, count=1)
    if text == before:
        raise SystemExit(
            "the MapLibre stylesheet link did not match. It must be removed, not left to fail "
            "silently -- check index.html and update MAPLIBRE_CSS."
        )

    for token in SKELETON:
        count = text.count(token)
        if count != 1:
            raise SystemExit(f"expected exactly one {token!r} in index.html, found {count}")
        text = text.replace(token, "", 1)

    if text.count(STYLES_LINK) != 1:
        raise SystemExit(f"expected exactly one {STYLES_LINK!r} to place the sizing override after")
    text = text.replace(STYLES_LINK, STYLES_LINK + "\n" + SIZING_OVERRIDE, 1)

    if "<header>" not in text:
        raise SystemExit("no <header> to place the review banner before")
    text = text.replace("<header>", BANNER + "\n  <header>", 1)

    # Collapse the blank lines the skeleton removal leaves behind, without touching anything else.
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    if "<!doctype" in text.lower() or "</html>" in text.lower():
        raise SystemExit("skeleton removal left a document tag behind")
    return text


def build_versions(src: Path) -> str:
    data = json.loads(src.read_text(encoding="utf-8"))
    original = data["basemap"]["tiles"]
    # Same-origin, so nothing leaves the page; the query string keeps each tile's cache key
    # distinct even though every one resolves to the same transparent image.
    data["basemap"]["tiles"] = f"{BLANK_TILE}?z={{z}}&x={{x}}&y={{y}}"
    data["basemap"]["review_copy_note"] = (
        "Published-review build: the basemap is a transparent PNG served beside the page, "
        f"because the artifact sandbox cannot reach {original}. A data: URI was tried first and "
        "MapLibre's tile loader rejects it (AJAXError: Failed to fetch (0)). Generated by "
        "spikes/g3-render/make_review_page.py. The attribution below is kept because the "
        "travel-time layers are OSM-derived, which is true whether or not tiles are drawn."
    )
    return json.dumps(data, indent=2) + "\n"


#: `.bin` is not a type a published artifact serves. `.wasm` is the one served extension that is
#: binary by nature, so the planes travel under it without risking a text re-encode.
SERVED_BINARY = ".wasm"


def build_manifest(src: Path) -> tuple[str, dict[str, str]]:
    """Rewrite the manifest's `.bin` filenames, and return the published-path mapping."""
    data = json.loads(src.read_text(encoding="utf-8"))
    renames: dict[str, str] = {}
    for layer in data["layers"]:
        for key, value in list(layer.items()):
            if isinstance(value, str) and value.endswith(".bin"):
                renamed = value[: -len(".bin")] + SERVED_BINARY
                layer[key] = renamed
                renames[value] = renamed
    data["review_copy_note"] = (
        f"Published-review build: every `.bin` plane is served as `{SERVED_BINARY}` because a "
        "published artifact does not serve `.bin`. Bytes are unchanged and app.js checks every "
        "length against nrows*ncols. Generated by spikes/g3-render/make_review_page.py."
    )
    return json.dumps(data, indent=2) + "\n", renames


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True, help="build directory to write into")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    fixtures = HERE / "fixtures" / "published"

    page = build_page(HERE / "index.html")
    (args.out / "index.html").write_text(page, encoding="utf-8", newline="\n")
    versions = build_versions(HERE / "versions.json")
    (args.out / "versions.json").write_text(versions, encoding="utf-8", newline="\n")
    manifest, renames = build_manifest(fixtures / "manifest.json")
    (args.out / "manifest.json").write_text(manifest, encoding="utf-8", newline="\n")
    tile = blank_png()
    (args.out / BLANK_TILE).write_bytes(tile)

    print(f"wrote {args.out / 'index.html'}  ({len(page):,} bytes)")
    print(f"wrote {args.out / 'versions.json'}  ({len(versions):,} bytes)")
    print(f"wrote {args.out / 'manifest.json'}  ({len(renames)} planes renamed)")
    print(f"wrote {args.out / BLANK_TILE}  ({len(tile):,} bytes, 256x256 transparent)")

    missing = [name for name in renames if not (fixtures / name).exists()]
    if missing:
        raise SystemExit(f"manifest names files that are not there: {missing}")

    print("\nPUBLISH MAP -- published path  <-  source")
    print(f"  index.html                   <-  {args.out / 'index.html'}")
    print(f"  versions.json                <-  {args.out / 'versions.json'}")
    print(f"  {BLANK_TILE:28} <-  {args.out / BLANK_TILE}")
    print(f"  fixtures/published/manifest.json  <-  {args.out / 'manifest.json'}")
    for name in ("styles.css", "geom.js", "card.js", "app.js", "worker.js"):
        print(f"  {name:28} <-  spikes/g3-render/{name}")
    for original, renamed in sorted(renames.items()):
        print(f"  fixtures/published/{renamed}  <-  fixtures/published/{original}")
    extra = [p.relative_to(fixtures).as_posix() for p in sorted(fixtures.rglob("*"))
             if p.is_file() and p.name != "manifest.json" and p.name not in renames]
    for name in extra:
        print(f"  fixtures/published/{name}  <-  fixtures/published/{name}   (attribution, "
              "not optional)")
    total = sum(p.stat().st_size for p in fixtures.rglob("*") if p.is_file())
    print(f"\n{total / 1e6:.1f} MB of fixtures. ATTRIBUTION.md and LICENSES/ ship with them.")


if __name__ == "__main__":
    main()
