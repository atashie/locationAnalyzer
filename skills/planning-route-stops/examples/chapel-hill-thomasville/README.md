# Chapel Hill, NC → Thomasville, GA — Wednesday 25 November 2026

A worked example of `planning-route-stops`: a family of four with boys aged 6 and 9, driving
the day before Thanksgiving. Seven itineraries across three genuinely different corridors.

Published artifact: https://claude.ai/code/artifact/bc120a95-023a-4184-81da-b12cebebe9b9

## What is here, and why each file matters

| File | Regenerable? | What it holds |
|---|---|---|
| `spec.json` | **No** | The research. 14 stops, 23 facility schedules with opening hours, last-entry times, weekday closures, 13 operator URLs, 4 researched prices, 7 options tagged by corridor with their own departure hours. |
| `build_page.py` | **No** | The page generator. Reads the two JSON files below and emits `route-options.html` — switcher, baked SVG basemap, per-option timelines, leg-rhythm strips, totals. |
| `experiments.json` | **No** | Corridor baselines measured bare (coastal, fall line, Atlanta, Jacksonville) plus rejected candidates. These are measurements, not derivations — nothing else records them. |
| `measured.json` | Yes, with network | Output of `itinerary_compare.py`. Legs, detours, arrival clocks, hours verdicts, route geometry. |
| `basemap.json` | Yes, with network | Output of `basemap.py`. State outlines and interstate centrelines, simplified and bakeable. |

`spec.json`, `build_page.py` and `experiments.json` are the ones that cannot be recovered by
re-running anything. The other two are committed so the example rebuilds with **no network at
all** — which is also what lets `doccheck.py` verify the prose against real figures anywhere.

Deliberately not committed (see `.gitignore`): `states_raw.json` (3.6 MB) and
`motorways_raw.json` (10.6 MB) upstream fetches, the `.route-cache/` directory, and the
generated `route-options.html`.

## Rebuilding

Offline, from exactly what is committed:

```bash
python build_page.py            # -> route-options.html, ~93 KB
```

Re-measuring against live routing (needs network; responses are cached in `.route-cache/`):

```bash
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

Everything that describes the journey lives in `spec.json`:

- **A stop's hours** — edit its `facilities` entries. Each takes `open`/`close` as `HH:MM`,
  `days` (`daily`, `Mon-Thu`, `Mon,Fri-Sun`), optionally `last_entry`, or `always: true` for
  something with no fixed hours. Hours are local to the stop; add `utc_offset` if it sits in a
  different zone from the origin.
- **A departure time** — each option carries its own `depart_h`, because corridors want
  different start times: one built on a 24-hour forecourt rewards 04:45, one built on
  attractions that open at 09:00 punishes it.
- **A new option** — add a key naming what distinguishes it, never its rank. The tool refuses
  `recommended`, `best` and friends.

Editing dwell times or hours costs **no routing requests** — the cache is keyed on coordinates
and costing, so only a changed route re-measures.

## Verifying a change

```bash
python ../../selftest.py                 # 42 invariants, no network
python ../../doccheck.py .               # prose vs code, using this example's figures
```

## Caveats carried by this example

Every opening time is a **published routine checked against no specific date** — nothing here
is confirmed for 25 November. Drive times are **free-flow**: the engine has no traffic model,
and the coastal options put 262 miles of southbound I-95 through the Carolinas on one of the
heaviest travel days of the year. There is no traffic layer and deliberately so: for a trip
weeks out, live traffic is a fact about now rather than about the travel date.

Admission is unpublished for Discovery Place and Zoo Atlanta, so both Charlotte-area options
understate cost. Hiott's Pharmacy is the one stop whose hours come from third-party listings
rather than an operator page; it is labelled `unknown` throughout and renders as such.
