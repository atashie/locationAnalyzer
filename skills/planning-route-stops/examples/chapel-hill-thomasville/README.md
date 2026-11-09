# Chapel Hill, NC → Thomasville, GA — Wednesday 25 November 2026

A worked example of `planning-route-stops`: a family of four with boys aged 6 and 9, driving
the day before Thanksgiving. Nine itineraries, three on each of three genuinely different
corridors, each built around one substantial active stop near lunchtime with short run-around
stops either side, and lunch as a short list of nearby places rather than one restaurant.

Published artifact: https://claude.ai/code/artifact/bc120a95-023a-4184-81da-b12cebebe9b9

Source of that page: `github.com/atashie/locationAnalyzer`, branch `master`, at
`skills/planning-route-stops/examples/chapel-hill-thomasville/`. The page states this in its own
provenance footer, so the artifact URL on its own is enough to find this directory — which was
not true of the first version, and a session on another machine stalled on exactly that.

## What is here, and why each file matters

| File | Regenerable? | What it holds |
|---|---|---|
| `research/*.json` | **No** | Every candidate the 2026-11-08 search found, in the research brief's schema: 230 entries (about 120 activity stops and 107 lunch places) across the three corridors, each with coordinates, hours as fields, prices, status labels and operator URLs. Six passes: a lunchtime-excursion pass per corridor and a pit-stop pass per stretch of road. `carried_over_stops.keep.json` holds the stops checked in the first pass. |
| `assemble_spec.py` | **No** | Picks from `research/`, normalises hours ("to sunset" becomes 17:30 and says so in the facility name), groups lunch places into "pick one" stops, defines the nine options and the "considered and left out" list, and writes `spec.json`. Re-picking costs no research. |
| `spec.json` | Yes, from the two above | 38 stops with a `role` each (`pit`, `excursion`, `lunch`), 81 facility schedules, 9 options with their own departure hours, 16 considered-and-left-out entries. |
| `build_page.py` | **No** | The page generator. Reads the two JSON files below and emits `route-options.html` — switcher, baked SVG basemap, per-option timelines, leg-rhythm strips, totals. |
| `experiments.json` | **No** | Corridor baselines measured bare (coastal, fall line, Atlanta, Jacksonville) plus rejected candidates. These are measurements, not derivations — nothing else records them. |
| `measured.json` | Yes, with network | Output of `itinerary_compare.py`. Legs, detours, arrival clocks, hours verdicts, route geometry. |
| `basemap.json` | Yes, with network | Output of `basemap.py`. State outlines and interstate centrelines, simplified and bakeable. |

`research/`, `assemble_spec.py`, `build_page.py` and `experiments.json` are the ones that cannot be
recovered by re-running anything. The other two are committed so the example rebuilds with **no network at
all** — which is also what lets `doccheck.py` verify the prose against real figures anywhere.

Deliberately not committed (see `.gitignore`): `states_raw.json` (3.6 MB) and
`motorways_raw.json` (10.6 MB) upstream fetches, the `.route-cache/` directory, and the
generated `route-options.html`.

## Rebuilding

Offline, from exactly what is committed:

```bash
python build_page.py            # -> route-options.html, ~144 KB
```

Re-picking stops or options, then re-measuring against live routing (needs network; responses are
cached in `.route-cache/`, so only a changed route sends a request):

```bash
python assemble_spec.py
python ../../itinerary_compare.py --spec spec.json \
    --date 2026-11-25 --utc-offset -5 --out measured.json
python build_page.py
```

Rebuilding the basemap (needs Census TIGERweb and an Overpass mirror; the Overpass query takes
about a minute and the mirrors rate-limit, so the raw fetches are cached locally once pulled):

```bash
cp ../../basemap.py . && python basemap.py
```

## Updating the published artifact

The page is already live at the URL above. To change it, **republish to that same URL** — pass
it as `url` to the Artifact tool. Publishing without it creates a *second* artifact rather than
updating the first, and whoever has the old link keeps seeing the old page.

The tool refuses to publish over an artifact this conversation has not read, so the sequence
from a fresh session is: read the existing artifact by its URL, rebuild locally, then publish
to that URL. Keep the favicon off the republish; an artifact keeps the icon it has, and a
changed icon reads to a viewer as a different page.

## Changing the trip

Edit `assemble_spec.py`, not `spec.json` (which it overwrites). Everything that describes the
journey is chosen there:

- **A stop's hours** — edit its `facilities` entries. Each takes `open`/`close` as `HH:MM`,
  `days` (`daily`, `Mon-Thu`, `Mon,Fri-Sun`), optionally `last_entry`, or `always: true` for
  something with no fixed hours. Hours are local to the stop; add `utc_offset` if it sits in a
  different zone from the origin.
- **A departure time** — each option carries its own `depart_h`, because corridors want
  different start times: one built on a 24-hour forecourt rewards 04:45, one built on
  attractions that open at 09:00 punishes it.
- **A new option** — add a key naming what distinguishes it, never its rank. The tool refuses
  `recommended`, `best` and friends. Keep to three per corridor.
- **A stop's role** — `pit` (short run-around), `excursion` (the one big active stop) or
  `lunch` (a list of places as facilities). The page's prose is computed from roles.

Editing dwell times or hours costs **no routing requests** — the cache is keyed on coordinates
and costing, so only a changed route re-measures.

## Verifying a change

```bash
python ../../selftest.py                 # 42 invariants, no network
python ../../doccheck.py .               # prose vs code, using this example's figures
```

## Caveats carried by this example

Most opening times are **published routines not checked against the date**. Four stops are
checked against the operator for 25 November and labelled `confirmed`: Adrenaline Monkey and
Treetop Quest Dunwoody (booking systems), Stone Mountain Park (its daily calendar) and Crowders
Mountain State Park (holiday list). Drive times are **free-flow**: the engine has no traffic model,
and the coastal options put 262 miles of southbound I-95 through the Carolinas on one of the
heaviest travel days of the year. There is no traffic layer and deliberately so.

Every option arrives at or after the 17:35 sunset: a two-hour stop plus lunch and two short stops
on a 9-10 hour drive does that. The page says so per option rather than hiding it.

The traveller asked for "Flying Rabbit Adventures (Dunwoody)": Flying Rabbit is in Greenville, SC
and closed Mon-Thu, so the Dunwoody aerial park, Treetop Quest, is the one used.

Where research passes disagreed, the operator's page was re-read and wins: Amerson River Park's
November hours (07:00-18:00), South of the Border's 24 h pumps and 07:00 Pantry, and the
Okefenokee tower (closed). Beyond those, spot checks of two or three citations per pass matched their sources.
