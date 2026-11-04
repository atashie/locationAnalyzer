# Geocoding contract benchmark (2026-11-03 13:36:17)

40 OSM address points sampled from the slice (truth = the OSM point itself, so this favours Nominatim slightly; Codex pass 3 M3) plus 10 ambiguous / POI-style queries. One request per second to Nominatim with an identifying User-Agent.

| provider | n | matched | median err m | p90 err m | > 250 m | median s |
|---|---|---|---|---|---|---|
| census | 40 | 33 | 81 | 210 | 4 | 0.10 |
| nominatim | 40 | 36 | 0 | 38 | 2 | 0.33 |

## Ambiguous and POI-style queries

| query | census | nominatim |
|---|---|---|
| Whole Foods, Chapel Hill NC | no match | match: Whole Foods Market, 81, Elliott Road, Blue Hill District, Chapel Hill, Orange Co |
| Whole Foods Durham | no match | match: Whole Foods Market, 621, Broad Street, 9th Street District, Old West Durham, Dur |
| Harris Teeter Carrboro | no match | match: Harris Teeter, 310, North Greensboro Street, Downtown, Carrboro, Orange County,  |
| UNC Hospitals | no match | match: UNC Health Blue Ridge, 2201, South Sterling Street, Morganton, Burke County, Nor |
| Duke Hospital | no match | match: Duke Hospital, Erwin Road, Crest Street, Durham, Durham County, North Carolina,  |
| RTP | no match | match: RTP, Research Triangle Park, Wake County, North Carolina, 27709, United States |
| Fidelity Investments Durham NC | no match | match: Fidelity Investments, 5411, Page Road, Nelson, Durham, Durham County, North Caro |
| Southpoint | no match | match: Southpoint, Kenosha, Kenosha County, Wisconsin, 53143, United States |
| Carrboro Farmers Market | no match | match: Carrboro Farmers' Market, 301, West Main Street, Downtown, Carrboro, Orange Coun |
| Weaver Street Market | no match | match: Weaver Street Market, 101, East Weaver Street, Downtown, Carrboro, Orange County |

## Contract notes

- Census Geocoder: street addresses only (no POI names); public-domain output; display the Census disclaimer; no autocomplete endpoint.
- Nominatim public API: 1 req/s application-wide, identifying User-Agent, attribution, results may be cached, autocomplete forbidden; dev-time only.
- A POI/name resolver (for 'Whole Foods', 'UNC Hospitals') must come from our own Overture/OSM place index, not from the geocoder.
- **Verdict (2026-11-03).** Street addresses: Census Geocoder first (public domain, 0.10 s median, 33/40 matched, 81 m median error against OSM points), Nominatim second at 1 req/s (36/40, near-zero error because the truth set is OSM itself). Named places: Census cannot resolve any; Nominatim resolves most but **without a region bias it returns the wrong "UNC Hospitals" (Morganton, 180 km away) and the wrong "Southpoint" (Wisconsin)** — any name lookup must be bounded to the search metro (`viewbox`+`bounded=1`, or our own Overture/OSM place index first). For the product: resolve names against the accepted Overture/OSM place index restricted to the metro, show candidates when more than one matches, and fall back to Census/Nominatim only for street addresses. Before public use, replace the public Nominatim instance (policy forbids production use) with a self-hosted or licensed geocoder. Autocomplete is out of scope for Phase 0.

Raw results: v2/data/geocode_bench.json

### S2.1 place-name resolver on the real metro index (2026-11-04 11:41:22)

Index: **96,585 places** from 90,349 Overture accepted rows + 7,425 OSM POIs, bounded by the **triangle routing bbox** — not the evaluation bbox, because a workplace can legitimately sit outside the area we grid. 177 distinct localities. Built in 3.2 s; median query **13.5 ms**.

The ten queries are verbatim from `geocoding.md`, where **Census resolved none of them** and unbounded Nominatim answered two of them with places in other states.

**10 of 10 produce candidates** — 4 a single confident answer, 6 ambiguous (a chooser), 0 not found. Ambiguity is the correct outcome for a brand with several shops; being decisive there is exactly the Morganton failure.

| query | outcome | top candidate | locality | source | matched on |
|---|---|---|---|---|---|
| `Whole Foods, Chapel Hill NC` | **ambiguous** | Whole Foods Market | Chapel Hill | osm +overture | `name:contains+locality` |
| `Whole Foods Durham` | **resolved** | Whole Foods Market | Durham | osm +overture | `name:contains+locality` |
| `Harris Teeter Carrboro` | **ambiguous** | Harris Teeter | Wake Forest | osm +overture | `name:exact` |
| `UNC Hospitals` | **ambiguous** | UNC Hospitals & Pharmacy | Chapel Hill | overture | `name:contains` |
| `Duke Hospital` | **resolved** | Duke Hospital | — | osm | `name:exact` |
| `RTP` | **ambiguous** | Aventura RTP | Durham | overture | `name:contains` |
| `Fidelity Investments Durham NC` | **ambiguous** | Fidelity Investments | Cary | overture | `name:exact` |
| `Southpoint` | **resolved** | Southpoint | Durham | overture | `name:exact` |
| `Carrboro Farmers Market` | **resolved** | Carrboro Farmers Market | Carrboro | overture | `name:exact` |
| `Weaver Street Market` | **ambiguous** | Weaver Street Market | Carrboro | osm +overture | `name:exact` |

Full candidate lists, scores, source-native ids and licences are in `v2/data/s2_resolver_fixtures_triangle.json`.


### S2.1 place-name resolver on the real metro index (2026-11-04 11:43:32)

Index: **96,585 places** from 90,349 Overture accepted rows + 7,425 OSM POIs, bounded by the **triangle routing bbox** — not the evaluation bbox, because a workplace can legitimately sit outside the area we grid. 177 distinct localities. Built in 3.1 s; median query **13.4 ms**.

The ten queries are verbatim from `geocoding.md`, where **Census resolved none of them** and unbounded Nominatim answered two of them with places in other states.

**10 of 10 produce candidates** — 7 a single confident answer, 3 ambiguous (a chooser), 0 not found. Ambiguity is the correct outcome for a brand with several shops; being decisive there is exactly the Morganton failure.

| query | outcome | top candidate | locality | source | matched on |
|---|---|---|---|---|---|
| `Whole Foods, Chapel Hill NC` | **resolved** | Whole Foods Market | Chapel Hill | osm +overture | `name:contains+locality` |
| `Whole Foods Durham` | **resolved** | Whole Foods Market | Durham | osm +overture | `name:contains+locality` |
| `Harris Teeter Carrboro` | **resolved** | Harris Teeter | Carrboro | osm +overture | `name:exact+locality` |
| `UNC Hospitals` | **ambiguous** | UNC Hospitals & Pharmacy | Chapel Hill | overture | `name:contains` |
| `Duke Hospital` | **resolved** | Duke Hospital | — | osm | `name:exact` |
| `RTP` | **ambiguous** | Aventura RTP | Durham | overture | `name:contains` |
| `Fidelity Investments Durham NC` | **resolved** | Fidelity Investments | Durham | overture | `name:exact+locality` |
| `Southpoint` | **resolved** | Southpoint | Durham | overture | `name:exact` |
| `Carrboro Farmers Market` | **resolved** | Carrboro Farmers Market | Carrboro | overture | `name:exact` |
| `Weaver Street Market` | **ambiguous** | Weaver Street Market | Chapel Hill | osm +overture | `name:exact` |

Full candidate lists, scores, source-native ids and licences are in `v2/data/s2_resolver_fixtures_triangle.json`.


### S2.1 place-name resolver on the real metro index (2026-11-04 11:43:44)

Index: **96,585 places** from 90,349 Overture accepted rows + 7,425 OSM POIs, bounded by the **triangle routing bbox** — not the evaluation bbox, because a workplace can legitimately sit outside the area we grid. 177 distinct localities. Built in 3.2 s; median query **14.0 ms**.

The ten queries are verbatim from `geocoding.md`, where **Census resolved none of them** and unbounded Nominatim answered two of them with places in other states.

**10 of 10 produce candidates** — 7 a single confident answer, 3 ambiguous (a chooser), 0 not found. Ambiguity is the correct outcome for a brand with several shops; being decisive there is exactly the Morganton failure.

| query | outcome | top candidate | locality | source | matched on |
|---|---|---|---|---|---|
| `Whole Foods, Chapel Hill NC` | **resolved** | Whole Foods Market | Chapel Hill | osm +overture | `name:contains+locality` |
| `Whole Foods Durham` | **resolved** | Whole Foods Market | Durham | osm +overture | `name:contains+locality` |
| `Harris Teeter Carrboro` | **resolved** | Harris Teeter | Carrboro | osm +overture | `name:exact+locality` |
| `UNC Hospitals` | **ambiguous** | UNC Hospitals & Pharmacy | Chapel Hill | overture | `name:contains` |
| `Duke Hospital` | **resolved** | Duke Hospital | — | osm | `name:exact` |
| `RTP` | **ambiguous** | Aventura RTP | Durham | overture | `name:contains` |
| `Fidelity Investments Durham NC` | **resolved** | Fidelity Investments | Durham | overture | `name:exact+locality` |
| `Southpoint` | **resolved** | Southpoint | Durham | overture | `name:exact` |
| `Carrboro Farmers Market` | **resolved** | Carrboro Farmers Market | Carrboro | overture | `name:exact` |
| `Weaver Street Market` | **ambiguous** | Weaver Street Market | Chapel Hill | osm +overture | `name:exact` |

Full candidate lists, scores, source-native ids and licences are in `v2/data/s2_resolver_fixtures_triangle.json`.

