# The comparison page

Reference for the switcher-and-map page that rule 1 and *The deliverable* ask for. Everything
here was built and measured on a real trip; the failures described are ones this pattern hit, not
hypotheticals.

## Generate the page, don't hand-write it

Write a small generator that reads `itinerary_compare.py --out` JSON and emits the HTML. The
point is not tidiness — it is **rule 3 enforced by construction** for everything the generator
actually derives. A hand-written page lets you retype a figure, and the moment you change a dwell
time or reroute an option, every clock below it is stale.

```
itinerary_compare.py --spec trip.json --out measured.json   # measure
build_page.py                                               # emit HTML from measured.json
```

**A generator does not protect the prose.** An adversarial review of one of these pages found
**14 numeric literals in the generator's own copy** — corridor times, two leg durations, a
"+16 min" comparison, two arrival clocks — all of which would survive a reroute unchanged. The
structured tables were live; the sentences around them were not, which is worse than obvious
staleness because they read as derived.

Two rules, then:

- **Derive every number that appears in prose**, from `measured.json` or from a small
  `experiments.json` holding one-off measurements (corridor baselines, rejected candidates). If a
  figure cannot be derived, it does not belong in a sentence.
- **Grep your own generator before publishing**: `grep -n '"n">[0-9+]' build_page.py` and check
  nothing comes back that is not an f-string substitution.

Doing this caught two further errors that had survived every earlier pass: a corridor quoted as
"+1h00" was +1h01, and the direct drive quoted as 8h41 was 8h42 — because the duration helpers
truncated seconds instead of rounding to the nearest minute, and a small negative rendered as
"-1h59".

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

## Hours belong next to the stop, not in a note below

The timeline's job is not only *when you arrive* but *what is open when you do*. Render each
stop as its facilities, each with the verdict `itinerary_compare.py` computed:

| Verdict | Treatment |
|---|---|
| `always` / `open` | accent rule on the left, normal weight |
| `opens` | warning rule, and the wait spelled out: "opens 07:00, 6 min into the halt" |
| `shut` / `closed` | dimmed, struck through, with when it opens |
| `unknown` | flag rule — hours exist but nobody published them in a checkable form |

Two rules learned the hard way:

- **A collision belongs beside the stop it affects.** The first version of one page *did* state
  that a stop's attractions opened at 11:00 while the arrival was 06:53 — in a prose section well
  below the timeline. The reader asked why a shut stop was being suggested, and was right to. Put
  the verdict in the row; the prose section explains, it does not carry the warning.
- **Rewriting the timeline is where status labels get dropped.** Replacing a chips row with a
  facilities list silently removed every "standing hours / could not determine" label, breaking
  rule 4 inside a change that had nothing to do with it. Facilities carry their own `status`;
  render it per row, and assert the counts after generating:

```python
for cls in ("standing", "confirmed", "unknown"):
    print(cls, len(re.findall(rf'class="src src-{cls}"', html)))
```

Flag the collisions on the switcher too — an option whose lunch stop opens half an hour after you
reach it should say so before the reader selects it, not after.

## Grouping by corridor

Once the options span genuinely different roads, the flat switcher stops working: a reader
scanning seven buttons cannot see that three are the same road and one goes via Atlanta. Group
them.

- One column per corridor, headed by its name and the roads it actually uses
  (`I-77, I-20, Fall Line Fwy, I-75`) — read from `maneuvers[].street_names`, not from the cities
  you chose. A corridor label guessed from waypoints was wrong once in three.
- Colour the routes **by corridor, not by option**, and tint the group heading to match. Within a
  corridor the lines overlap anyway, so per-option colours buy nothing and spend the palette.
- Put each option's **departure** in its button alongside the arrival, because once corridors set
  their own departure hours "arrive 17:36" is meaningless without "leave 05:18".
- Add a **longest leg** column to the totals table. With corridors in play it varies from 2:08 to
  4:34, and it is the number that decides whether a plan survives a small child — more decisive
  than total drive time, which barely moves.

On the rhythm strips, anchor every bar to the *earliest* departure across all options and draw
the waiting time as a hatched lead-in. Otherwise an option that leaves two hours later looks
shorter than it is, which is the one thing the strips exist to prevent.

## Basemap layering

`basemap.py` writes `basemap.json`; the generator inlines it as four SVG groups, in this order,
all **beneath** the route paths:

```
base-states        state outlines, stroked (never filled -- clipped runs are open polylines)
base-roads         stitched interstate centrelines, thinner and fainter than any route
base-road-labels   I-95, I-85 ... with paint-order:stroke and a halo in the map background colour
base-cities        dots plus labels, two weights (major / minor), same halo treatment
```

Then routes, then the selected option's markers, then origin/destination. Getting the order
wrong is not subtle: roads over routes makes the corridors unreadable.

Three details that make the difference between a basemap and clutter:

- **Give the `svg` its own background token** (`--map-bg`) distinct from the page panel, so the
  map reads as a map rather than as a diagram on a card. Define it in all three theme blocks.
- **Halo every label** with `paint-order:stroke; stroke:var(--map-bg); stroke-width:5px`. Without
  it, city names sitting on a route line are illegible, and you will not notice in one theme.
- **Keep basemap strokes thinner and lower-contrast than the thinnest route.** The basemap is
  reference, not content; if it competes, the comparison is harder to read than with no basemap
  at all. Interstate lines at 2.4 px against routes at 4 px unselected and 9 px selected worked.

Pad the projection bbox (0.45° here) *before* projecting anything, so routes and basemap share
one `proj()`. Deriving the padded window inside the generator rather than in `basemap.py` keeps
the basemap reusable across trips in the same region.
