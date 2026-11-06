# The comparison page

Reference for the switcher-and-map page that rule 1 and *The deliverable* ask for. Everything
here was built and measured on a real trip; the failures described are ones this pattern hit, not
hypotheticals.

## Generate the page, don't hand-write it

Write a small generator that reads `itinerary_compare.py --out` JSON and emits the HTML. The
point is not tidiness — it is **rule 3 enforced by construction**. A hand-written page lets you
retype a figure, and the moment you change a dwell time or reroute an option, every clock below
it is stale. A generator cannot drift.

```
itinerary_compare.py --spec trip.json --out measured.json   # measure
build_page.py                                               # emit HTML from measured.json
```

One real consequence: when a dwell time changed late, the page's arrival times, the elapsed
totals, the rhythm bars and the table all moved together. Nothing needed checking.

## Structure that worked

```
header            the question, the direct drive, one line saying the weighing is theirs
switcher          one button per option: name + arrival + cost + halt count
split             map (sticky) | timeline for the selected option
rhythm strips     all options on one time axis -- see below, this is the real comparison
totals table      all options, every column, selected row tinted
notes             what the trade is, what's closed, upgrades, traffic
unverified        the "nothing is confirmed for the date" paragraph plus the calls
provenance        measured / derived / calculated / standing-hours
```

Switching updates five things at once: route highlight, markers, timeline, table row, rhythm
strip. Wire them from one `select(key)` function; anything you forget to wire becomes a view
showing another option's data.

## The map will probably disappoint you — plan for that

**Options on the same corridor produce near-identical routes.** On a 540-mile drive with five
options, two were *geometrically identical* and the widest pairwise separation was 0.5° — the
rest were under 0.13°. Five overlapping lines on a map imply a divergence that does not exist.

So be clear what the map is for:

- **It orients.** Where the corridor runs, where the stops fall along it, how the day is spaced
  geographically. That is worth the space.
- **It does not compare.** Say so in the legend, in plain words: *"All five routes drawn — they
  use the same roads, so they almost coincide. The numbered markers are where the selected
  option stops."*

Check this before you design around it. Cheap test on the measured geometry:

```python
for a, b in itertools.combinations(options, 2):
    sep = max(min(math.hypot(p[0]-q[0], p[1]-q[1]) for q in geom[b]) for p in geom[a])
```

If separations are small, the map is context and **the comparison has to live somewhere else.**

## Leg-rhythm strips: what actually differs

When the routes coincide, what differs is **how the day is carved up**. One horizontal bar per
option, all on the same time axis (scale every bar to the longest option's elapsed time), grey
for driving and the accent for stopped. This renders the real trade-off in one glance:

> *Fewest stops* came out at 80.7% of the longest option's elapsed time — with a 3h20 leg in it.
> *Most time on your feet* reached 96.7% and never drove more than 2h15 at a go. Fewer halts buys
> an earlier arrival and costs a longer stretch in the car. No table makes that as obvious.

Label each strip with its arrival time and its **longest single leg** — that number is what
decides whether a plan survives a small child.

## Projection and geometry

Artifact pages block every external fetch, so tiles never load and Leaflet renders blank. Bake
the geometry in; `itinerary_compare.py` emits it already simplified.

Equirectangular fit to the bounding box, longitude scaled by `cos(mean latitude)`:

```python
mean_lat = math.radians((bbox["min_lat"] + bbox["max_lat"]) / 2)
kx = math.cos(mean_lat)
w_deg = (bbox["max_lon"] - bbox["min_lon"]) * kx
h_deg =  bbox["max_lat"] - bbox["min_lat"]
VH = 1000.0; VW = VH * w_deg / h_deg; PAD = VH * 0.035

def proj(lat, lon):
    x = ((lon - bbox["min_lon"]) * kx / w_deg) * (VW - 2*PAD) + PAD
    y = (1 - (lat - bbox["min_lat"]) / h_deg) * (VH - 2*PAD) + PAD
    return x, y
```

Emit SVG `path` strings from Python, not coordinates plus in-page projection code — the page then
has no geometry logic to get wrong, and markers use the same `proj()` as the paths by construction.

**Verify numerically instead of by eye.** `file://` URLs cannot be screenshotted by the browser
extension, and the check that matters is arithmetic anyway. Assert that landmarks land in the
right relative positions and that no point escapes the viewBox:

```
Chapel Hill      x= 768.5 y=  35.0     # NE corner
Thomasville      x=  35.0 y= 955.6     # SW corner
total out-of-bounds points: 0
```

A decode-at-precision-5 bug shows up instantly here as coordinates in the wrong quadrant — and
is nearly invisible on a blank-ground map, which is what makes it worth asserting.

SVG paint order is document order, so lift the selected route by moving its node after the others:

```js
sel.parentNode.insertBefore(sel, sel.parentNode.querySelector(".markers"));
```

## Copy rules

- Option names say what the option **is**: *Fewest stops, earliest arrival* / *One big thing: the
  swamp* / *If it rains* / *Fort and swamp, longest day*. Never *Recommended*, never *Best*.
- An option over the traveller's rough budget gets the overage and a sentence, in body type:
  *"Four options sit under it, and Fort and swamp runs 18 min over. That is a price, not a
  disqualification."* No strike-through, no red, no "rejected".
- State what the reader decides, once, near the top: *"Which trade is worth it is yours to call."*
- Keep the closures and the unverified list as prose sections, not footnotes. A Wednesday closure
  that kills the best attraction at a stop is headline information.

## Accessibility and the boring bits

- `role="radiogroup"` on the switcher, `role="radio"` + `aria-checked` per button, arrow-key
  handling. People operate this with a keyboard.
- Toggle views with the `hidden` attribute, not `style.display` — the artifact wrapper ships
  `[hidden]{display:none!important}`.
- Three theme states: bare `:root` for the full light palette, `@media (prefers-color-scheme:dark)`
  guarded as `:root:not([data-theme="light"])`, and `:root[data-theme="dark"]`. Every colour
  defined in the bare block first.
- Count your tags before publishing. A generated page makes a cheap smoke test possible: open vs
  close counts per element, and one assertion that each option produced exactly one switcher
  button, one route path, one marker group, one timeline, one rhythm strip and one table row.
