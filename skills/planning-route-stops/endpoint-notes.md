# Public endpoint notes

Limits worth knowing before you hit them. All free, no keys.

## Valhalla (routing) — `https://valhalla1.openstreetmap.de`

- **`/sources_to_targets` caps path distance at 150 km** and returns HTTP 400 beyond it. For
  anything longer, use `/route` with the candidate as a via point: one call returns both legs,
  which is what you need anyway.
- `trip.legs[].shape` is an **encoded polyline at precision 6**, not the usual 5. Decoding at 5
  puts your geometry in the wrong hemisphere-ish place.
- Road refs live in `maneuvers[].street_names` as `"I 85 North"` — **a space, not a hyphen**.
  Matching `I-85` finds nothing.
- Costing options: `auto`, `truck`, `bicycle`, `pedestrian`, `motor_scooter`, `motorcycle`.
- **No traffic model.** Times are free-flow. Quote them as a floor, especially on a holiday.
- Rate-limit politely: ~0.5–1 s between calls.

## Overpass (OSM features) — several mirrors

- **Returns HTTP 406 to clients that send no `User-Agent`.** This looks like a query error and
  is not. Identify yourself.
- Mirrors rate-limit with 429. Try several (`overpass-api.de`, `overpass.kumi.systems`,
  `overpass.osm.ch`, `overpass.private.coffee`) with backoff, and **cache the raw response** —
  re-running a wide query during development will get you blocked.
- `highway=trunk` for US routes comes back as **hundreds of disconnected fragments**, because
  the tag only applies where the road is limited-access. US-1 returned 190 separate lines.
  Stitch by `ref` and endpoint proximity, or stick to `motorway`.

## Geometry

- **A dead-end spur costs its detour twice.** One national park visitor centre scored a +2:03
  penalty for this reason and was correctly rejected on measurement.
- Simplify with Ramer–Douglas–Peucker before shipping geometry; 3–5k points per route reduce to
  10–50 with no visible loss at map scale. Use an **iterative** implementation — recursion blows
  the stack on long routes.

## Shipping a page

- **Artifact pages block every external image, stylesheet and fetch.** Map tiles will not load:
  Leaflet renders blank. Bake geometry into the page and publish images as supporting files.
- Fonts are the exception (`fonts.googleapis.com` / `fonts.gstatic.com`); scripts only from the
  allowlisted CDNs.

## Images for cards

- Prefer the page's **`og:image`** — the preview the site publishes for itself.
- **Verify every image by eye before shipping.** Automated selection is unreliable: of 20
  images chosen by `og:image`-then-largest-photo, four were wrong — a map of *Yellowstone* for a
  South Carolina park, two municipal logos, and a transit infographic. Filename heuristics
  caught none of them.

## Browser automation (Chrome extension)

- Permissions are **per domain *and* per action**. Navigation can be allowed while JavaScript
  execution and screenshots on the same domain are denied.
- A cross-domain `navigate` **inside a batch aborts the whole batch**. Navigate standalone
  first; batch only same-domain actions afterwards.
- `computer` screenshots accept `save_to_disk`, which returns a path you can post-process.
- **`file://` URLs are refused** — "Can't interact with browser-internal or unparseable URLs",
  both standalone and with an explicit `tabId`. You cannot screenshot a local HTML file you just
  wrote. Verify generated geometry numerically instead (landmark positions, viewBox bounds, tag
  balance) and treat the published artifact as the review surface.

## Writing generator scripts via the Bash tool

- **`\n` inside a quoted heredoc does not survive.** Writing a Python generator through
  `python - <<'PY'` turned `'...\n'` into a real line break mid-literal, producing
  `SyntaxError: unterminated string literal` — three times, at successively later lines, because
  each repair introduced the next one. Build newlines with `chr(10)` and backslashes with
  `chr(92)`, or write the generator with the Write tool instead.

## Prices and availability

- **Booking engines return 403/429 to automation.** Hilton, Marriott, Hyatt, IHG, Choice and
  Expedia all refused in one project. "No live rate was obtainable for this date" is the honest
  result; a stale "from" price presented as a quote is not.
- US federal per diem is a **reimbursement ceiling**, not evidence about market pricing, and
  the fiscal year runs **October–September** — November 2026 is FY2027.
