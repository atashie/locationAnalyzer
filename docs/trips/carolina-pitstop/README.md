# Carolina Pitstop Planner

Published page: https://claude.ai/artifact/D9wbv1pjQhaFFCSnXUnjsd (shared by link).

- **Background tab, "How we chose: five towns"**: the original comparison of overnight stops from
  Gainesville FL to Chapel Hill NC. It is carried over unchanged from the published
  version 1793985816-bceb. Its own generator was never committed, so its data lives only in
  `page_base.html`.
- **Booked tab, "Our Saturday: Columbia"** (added 2026-11-15; the page always opens here, and only a `#route` link opens the background tab): the booked plan. It covers the
  Staybridge Suites on Huger St and the Fireflies Holiday Lights at Segra Park on Sat 28 Nov
  2026. It compares four halfway stops and lists dinner, dessert and small, free things
  nearby.

## Rebuild tab 2

```bash
python ~/.claude/skills/planning-route-stops/itinerary_compare.py --spec spec.json \
    --date 2026-11-28 --utc-offset -5 --out measured.json   # drive legs + hours verdicts
python walk.py                                               # walks.json (venue walks)
python sunday.py                                             # sunday.json (hotel -> Chapel Hill, 4 corridors)
python morning.py                                            # morning.json (Sunday venues: walk + drive from hotel)
python project.py measured.json cola_map.json                # both days' routes into the page's map frame
python build_columbia_tab.py                                 # writes carolina-pitstop.html
```

Then publish `carolina-pitstop.html` to the URL above.

## Files

| File | What it is |
|------|------------|
| `cand.csv`, `scan.json` | The `corridor_scan.py` shortlist: 17 candidates scored against the direct route. |
| `spec.json` | The four halfway options and their facilities' hours. |
| `measured.json` | The measured output from `spec.json`. |
| `walks.json` | Walking routes from each venue to Segra Park and to the hotel. |
| `sunday.py`, `sunday.json` | The Sunday leg to Chapel Hill on each corridor. `charlotte` forces the Charlotte waypoint and matches the router's own pick, so the page drops it. |
| `morning.py`, `morning.json` | Walk and drive times from the hotel to the Sunday-morning places. Methodical and Drip geocoded to their street only, so the page borrows the measured neighbour and says "about". |
| `project.py` | Projects the routes into the page's map frame. It recovers the original map's linear lat/lon fit from the Gainesville and Chapel Hill labels, and asserts it against the Charlotte and Jacksonville labels. |

## Known gaps

- **Walk times.** All walks are Valhalla pedestrian times at adult pace.
- **Bad geocodes.** Page Ellington Park and Coastal Crust geocoded badly, so the page shows no
  measured walk for either.
- **Drive times.** Drive times are free-flow, with no Thanksgiving traffic.
- **Not shown.** The booking confirmation number is deliberately not on the page or in this
  repo.
