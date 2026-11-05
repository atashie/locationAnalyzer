# Geocoding contract benchmark (2026-11-03 13:36:17)

40 OSM address points sampled from the slice (truth = the OSM point itself, so this favours Nominatim slightly; Codex pass 3 M3) plus 10 ambiguous / POI-style queries. One request per second to Nominatim with an identifying User-Agent.

| provider | n | matched | median err m | p90 err m | > 250 m | median s |
|---|---|---|---|---|---|---|
| census | 40 | 33 | 81 | 210 | 4 | 0.10 |
| nominatim | 40 | 36 | 0 | 38 | 2 | 0.33 |


> **The S2.1 resolver sections appended below carry their own dates, and the earlier ones are
> superseded.** Any run quoting an index of **96,585 places / 90,349 Overture rows / 177
> localities** used the partly evaluation-only Overture download *and* a resolver predating the
> Codex pass-10 and pass-11 fixes; its candidate lists, outcomes and timings are all affected. The
> current index is **113,720 places / 107,484 Overture rows / 229 localities**. Read the latest
> dated section (Codex pass-11 M5).

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

> *Superseded input: evaluation-extent Overture download, and a resolver predating the Codex pass-10 and pass-11 fixes. Current index 113,720 / 107,484 / 229.*

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

> *Superseded input: evaluation-extent Overture download, and a resolver predating the Codex pass-10 and pass-11 fixes. Current index 113,720 / 107,484 / 229.*

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

> *Superseded input: evaluation-extent Overture download, and a resolver predating the Codex pass-10 and pass-11 fixes. Current index 113,720 / 107,484 / 229.*

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


### S2.1 correctness, not confidence (2026-11-04 13:06:24)

`s2_resolver_fixtures.py` reports 10/10 candidates and 7 single answers. That measures **confidence**. This checks the answers against the independent spot-check reference points, with a deliberately coarse 800 m threshold — the references are not POI centroids, so this separates *same place* from *somewhere else entirely*.

| query | outcome | top candidate | category | distance from reference | verdict |
|---|---|---|---|---|---|
| `Whole Foods, Chapel Hill NC` | resolved | Whole Foods Market | supermarket | — | **ungraded** |
| `Whole Foods Durham` | resolved | Whole Foods Market | supermarket | — | **ungraded** |
| `Harris Teeter Carrboro` | resolved | Harris Teeter | supermarket | — | **ungraded** |
| `UNC Hospitals` | ambiguous | UNC Hospitals & Pharmacy | pharmacy | 973 m | **right place NOT offered** |
| `Duke Hospital` | resolved | Duke Hospital | — | 56 m | **correct** |
| `RTP` | ambiguous | Aventura RTP | historic_site | 14056 m | **right place NOT offered** |
| `Fidelity Investments Durham NC` | resolved | Fidelity Investments | broker | — | **ungraded** |
| `Southpoint` | resolved | Southpoint | dessert_shop | 732 m | **correct** |
| `Carrboro Farmers Market` | resolved | Carrboro Farmers Market | farmers_market | 227 m | **correct** |
| `Weaver Street Market` | ambiguous | Weaver Street Market | supermarket | — | **ungraded** |

**3 of 5 graded queries land on the right place.** Only queries whose intended answer was written down beforehand can be graded; the rest are printed for reading rather than scored, because a resolver cannot be marked against an answer nobody recorded. For an *ambiguous* outcome the grading asks whether the right place is **offered** at all, since ambiguity is a legitimate answer and a chooser the household resolves.


### S2.1 correctness, not confidence (2026-11-04 13:17:36)

`s2_resolver_fixtures.py` reports 10/10 candidates and 7 single answers. That measures **confidence**. This checks the answers against the independent spot-check reference points, with a deliberately coarse 800 m threshold — the references are not POI centroids, so this separates *same place* from *somewhere else entirely*.

| query | outcome | top candidate | category | distance from reference | verdict |
|---|---|---|---|---|---|
| `Whole Foods, Chapel Hill NC` | ambiguous | Whole Foods Market | supermarket | — | **ungraded** |
| `Whole Foods Durham` | ambiguous | Whole Foods Market | supermarket | — | **ungraded** |
| `Harris Teeter Carrboro` | ambiguous | Harris Teeter | supermarket | — | **ungraded** |
| `UNC Hospitals` | ambiguous | UNC Hospitals & Pharmacy | pharmacy | 973 m | **right place NOT offered** |
| `Duke Hospital` | resolved | Duke Hospital | platform | 56 m | **correct** |
| `RTP` | ambiguous | Aventura RTP | historic_site | 14056 m | **right place NOT offered** |
| `Fidelity Investments Durham NC` | resolved | Fidelity Investments | broker | — | **ungraded** |
| `Southpoint` | resolved | Southpoint | dessert_shop | 732 m | **correct** |
| `Carrboro Farmers Market` | resolved | Carrboro Farmers Market | farmers_market | 227 m | **correct** |
| `Weaver Street Market` | ambiguous | Weaver Street Market | supermarket | — | **ungraded** |

**3 of 5 graded queries land on the right place.** Only queries whose intended answer was written down beforehand can be graded; the rest are printed for reading rather than scored, because a resolver cannot be marked against an answer nobody recorded. For an *ambiguous* outcome the grading asks whether the right place is **offered** at all, since ambiguity is a legitimate answer and a chooser the household resolves.


### S2.1 correctness, not confidence (2026-11-04 13:19:09)

`s2_resolver_fixtures.py` reports 10/10 candidates and 7 single answers. That measures **confidence**. This checks the answers against the independent spot-check reference points, with a deliberately coarse 800 m threshold — the references are not POI centroids, so this separates *same place* from *somewhere else entirely*.

| query | outcome | top candidate | category | distance from reference | verdict |
|---|---|---|---|---|---|
| `Whole Foods, Chapel Hill NC` | ambiguous | Whole Foods Market | supermarket | — | **ungraded** |
| `Whole Foods Durham` | resolved | Whole Foods Market | supermarket | — | **ungraded** |
| `Harris Teeter Carrboro` | resolved | Harris Teeter | supermarket | — | **ungraded** |
| `UNC Hospitals` | ambiguous | UNC Hospitals & Pharmacy | pharmacy | 973 m | **right place NOT offered** |
| `Duke Hospital` | resolved | Duke Hospital | platform | 56 m | **correct** |
| `RTP` | ambiguous | Aventura RTP | historic_site | 14056 m | **right place NOT offered** |
| `Fidelity Investments Durham NC` | resolved | Fidelity Investments | broker | — | **ungraded** |
| `Southpoint` | resolved | Southpoint | dessert_shop | 732 m | **correct** |
| `Carrboro Farmers Market` | resolved | Carrboro Farmers Market | farmers_market | 227 m | **correct** |
| `Weaver Street Market` | ambiguous | Weaver Street Market | supermarket | — | **ungraded** |

**3 of 5 graded queries land on the right place.** Only queries whose intended answer was written down beforehand can be graded; the rest are printed for reading rather than scored, because a resolver cannot be marked against an answer nobody recorded. For an *ambiguous* outcome the grading asks whether the right place is **offered** at all, since ambiguity is a legitimate answer and a chooser the household resolves.


### S2.1 correctness, not confidence (2026-11-04 13:19:43)

`s2_resolver_fixtures.py` reports 10/10 candidates and 7 single answers. That measures **confidence**. This checks the answers against the independent spot-check reference points, with a deliberately coarse 800 m threshold — the references are not POI centroids, so this separates *same place* from *somewhere else entirely*.

| query | outcome | top candidate | category | distance from reference | verdict |
|---|---|---|---|---|---|
| `Whole Foods, Chapel Hill NC` | ambiguous | Whole Foods Market | supermarket | — | **ungraded** |
| `Whole Foods Durham` | resolved | Whole Foods Market | supermarket | — | **ungraded** |
| `Harris Teeter Carrboro` | resolved | Harris Teeter | supermarket | — | **ungraded** |
| `UNC Hospitals` | ambiguous | UNC Hospitals & Pharmacy | pharmacy | 973 m | **right place NOT offered** |
| `Duke Hospital` | resolved | Duke Hospital | platform | 56 m | **WRONG ENTITY (a stop or subsidiary feature, not the place)** |
| `RTP` | ambiguous | Aventura RTP | historic_site | 14056 m | **right place NOT offered** |
| `Fidelity Investments Durham NC` | resolved | Fidelity Investments | broker | — | **ungraded** |
| `Southpoint` | resolved | Southpoint | dessert_shop | 732 m | **correct** |
| `Carrboro Farmers Market` | resolved | Carrboro Farmers Market | farmers_market | 227 m | **correct** |
| `Weaver Street Market` | ambiguous | Weaver Street Market | supermarket | — | **ungraded** |

**2 of 5 graded queries land on the right place**, and 1 resolve confidently onto a feature that merely *refers* to a place (a stop, a platform, an ATM) rather than the place itself — a distance test calls those correct, which is why identity is checked separately. Only queries whose intended answer was written down beforehand can be graded; the rest are printed for reading rather than scored, because a resolver cannot be marked against an answer nobody recorded. For an *ambiguous* outcome the grading asks whether the right place is **offered** at all, since ambiguity is a legitimate answer and a chooser the household resolves.


### S2.1 correctness, not confidence (2026-11-04 13:28:00)

`s2_resolver_fixtures.py` reports 10/10 candidates and 7 single answers. That measures **confidence**. This checks the answers against the independent spot-check reference points, with a deliberately coarse 800 m threshold — the references are not POI centroids, so this separates *same place* from *somewhere else entirely*.

| query | outcome | top candidate | category | distance from reference | verdict |
|---|---|---|---|---|---|
| `Whole Foods, Chapel Hill NC` | ambiguous | Whole Foods Market | supermarket | — | **ungraded** |
| `Whole Foods Durham` | resolved | Whole Foods Market | supermarket | — | **ungraded** |
| `Harris Teeter Carrboro` | resolved | Harris Teeter | supermarket | — | **ungraded** |
| `UNC Hospitals` | ambiguous | UNC Hospitals & Pharmacy | pharmacy | 973 m | **right place NOT offered** |
| `Duke Hospital` | resolved | Duke Hospital | platform | 56 m | **WRONG ENTITY (a stop or subsidiary feature, not the place)** |
| `RTP` | ambiguous | Aventura RTP | historic_site | 14056 m | **right place NOT offered** |
| `Fidelity Investments Durham NC` | resolved | Fidelity Investments | broker | — | **ungraded** |
| `Southpoint` | resolved | Southpoint | dessert_shop | 732 m | **correct** |
| `Carrboro Farmers Market` | resolved | Carrboro Farmers Market | farmers_market | 227 m | **correct** |
| `Weaver Street Market` | ambiguous | Weaver Street Market | supermarket | — | **ungraded** |

**2 of 5 graded queries land on the right place**, and 1 resolve confidently onto a feature that merely *refers* to a place (a stop, a platform, an ATM) rather than the place itself — a distance test calls those correct, which is why identity is checked separately. Only queries whose intended answer was written down beforehand can be graded; the rest are printed for reading rather than scored, because a resolver cannot be marked against an answer nobody recorded. For an *ambiguous* outcome the grading asks whether the right place is **offered** at all, since ambiguity is a legitimate answer and a chooser the household resolves.


### S2.1 correctness, not confidence (2026-11-04 13:57:58)

`s2_resolver_fixtures.py` reports 10/10 candidates and 7 single answers. That measures **confidence**. This checks the answers against the independent spot-check reference points, with a deliberately coarse 800 m threshold — the references are not POI centroids, so this separates *same place* from *somewhere else entirely*.

| query | outcome | top candidate | category | distance from reference | verdict |
|---|---|---|---|---|---|
| `Whole Foods, Chapel Hill NC` | ambiguous | Whole Foods Market | supermarket | — | **ungraded** |
| `Whole Foods Durham` | resolved | Whole Foods Market | supermarket | — | **ungraded** |
| `Harris Teeter Carrboro` | resolved | Harris Teeter | supermarket | — | **ungraded** |
| `UNC Hospitals` | ambiguous | UNC Hospitals & Pharmacy | pharmacy | 973 m | **right place NOT offered** |
| `Duke Hospital` | ambiguous | Duke Hospital | platform | 56 m | **right place offered** |
| `RTP` | ambiguous | Aventura RTP | historic_site | 14056 m | **right place NOT offered** |
| `Fidelity Investments Durham NC` | resolved | Fidelity Investments | broker | — | **ungraded** |
| `Southpoint` | resolved | Southpoint | dessert_shop | 732 m | **correct** |
| `Carrboro Farmers Market` | resolved | Carrboro Farmers Market | farmers_market | 227 m | **correct** |
| `Weaver Street Market` | ambiguous | Weaver Street Market | supermarket | — | **ungraded** |

**3 of 5 graded queries land on the right place**, and 0 resolve confidently onto a feature that merely *refers* to a place (a stop, a platform, an ATM) rather than the place itself — a distance test calls those correct, which is why identity is checked separately. Only queries whose intended answer was written down beforehand can be graded; the rest are printed for reading rather than scored, because a resolver cannot be marked against an answer nobody recorded. For an *ambiguous* outcome the grading asks whether the right place is **offered** at all, since ambiguity is a legitimate answer and a chooser the household resolves.


### S2.1 correctness, not confidence (2026-11-04 14:41:59)

`s2_resolver_fixtures.py` reports 10/10 candidates and 7 single answers. That measures **confidence**. This checks the answers against the independent spot-check reference points, with a deliberately coarse 800 m threshold — the references are not POI centroids, so this separates *same place* from *somewhere else entirely*.

| query | outcome | top candidate | category | distance from reference | verdict |
|---|---|---|---|---|---|
| `Whole Foods, Chapel Hill NC` | ambiguous | Whole Foods Market | supermarket | — | **ungraded** |
| `Whole Foods Durham` | resolved | Whole Foods Market | supermarket | — | **ungraded** |
| `Harris Teeter Carrboro` | resolved | Harris Teeter | supermarket | — | **ungraded** |
| `UNC Hospitals` | ambiguous | UNC Hospitals & Pharmacy | pharmacy | 973 m | **right place NOT offered** |
| `Duke Hospital` | ambiguous | Duke Hospital | platform | 56 m | **right place offered** |
| `RTP` | ambiguous | Aventura RTP | historic_site | 14056 m | **right place NOT offered** |
| `Fidelity Investments Durham NC` | resolved | Fidelity Investments | broker | — | **ungraded** |
| `Southpoint` | resolved | Southpoint | dessert_shop | 732 m | **correct** |
| `Carrboro Farmers Market` | resolved | Carrboro Farmers Market | farmers_market | 227 m | **correct** |
| `Weaver Street Market` | ambiguous | Weaver Street Market | supermarket | — | **ungraded** |

**3 of 5 graded queries land on the right place**, and 0 resolve confidently onto a feature that merely *refers* to a place (a stop, a platform, an ATM) rather than the place itself — a distance test calls those correct, which is why identity is checked separately. Only queries whose intended answer was written down beforehand can be graded; the rest are printed for reading rather than scored, because a resolver cannot be marked against an answer nobody recorded. For an *ambiguous* outcome the grading asks whether the right place is **offered** at all, since ambiguity is a legitimate answer and a chooser the household resolves.


### S2.1 expanded graded benchmark (2026-11-04 21:08:23)

**41 of 42 graded assertions pass.** 42 queries, 0 ungraded. Index 113,720 places, 228 localities.

Written because four consecutive Codex passes found over-corrections in `resolve.py`, each closing the reviewed case and breaking an adjacent one, and the five-query benchmark could not see them. Intended answers are recorded in `v2/benchmarks/resolver_queries.json` **before** the run. Location grading uses only the twelve independently justified spot-check reference points; everything else is a property assertion, because most of what keeps breaking is identity and confidence rather than position.

| query | outcome | leading candidate | category | verdict | detail |
|---|---|---|---|---|---|
| `UNC Hospitals` | ambiguous | UNC Hospitals & Pharmacy | pharmacy | pass | lead role facility; offered within 800 m; leader name matches |
| `UNC Hospitals Chapel Hill` | ambiguous | Unc Hospitals, Chapel Hill NC | hospital | pass | lead role facility; offered within 800 m; leader name matches |
| `UNC Hospitals, Chapel Hill NC` | ambiguous | Unc Hospitals, Chapel Hill NC | hospital | pass | lead role facility; offered within 800 m; leader name matches |
| `Duke Hospital` | ambiguous | Duke Hospital | platform | pass | outcome ambiguous; a real place is among the options |
| `Duke University Hospital` | ambiguous | Duke University Hospital Imaging Services | radiology | pass | lead role facility; offered within 800 m; leader name matches |
| `Duke Hospital bus stop` | resolved | Duke Hospital | platform | pass | outcome resolved; lead role stop; offered within 800 m; leader within 56 m |
| `Southpoint` | resolved | Southpoint | dessert_shop | pass | leader name matches; leader 731 m away |
| `The Streets at Southpoint` | ambiguous | The Streets At Southpoint | shopping_mall | pass | leader name matches; leader 311 m away |
| `RTP` | ambiguous | Aventura RTP | historic_site | pass | ambiguous, so no confident claim was made |
| `Research Triangle Park` | ambiguous | Research Triangle Park | professional_service | pass | ambiguous, so no confident claim was made |
| `RDU` | ambiguous | CrossFit RDU | gym | pass | lead role facility; ambiguous, so no confident claim was made |
| `RDU Airport` | ambiguous | RDU Airport | airport_terminal | pass | lead role facility; ambiguous, so no confident claim was made |
| `Carrboro Farmers Market` | resolved | Carrboro Farmers Market | farmers_market | pass | offered within 800 m; leader name matches |
| `Weaver Street Market` | ambiguous | Weaver Street Market | supermarket | pass | leader name matches |
| `Harris Teeter Carrboro` | resolved | Harris Teeter | supermarket | pass | outcome resolved; locality matched; leader name matches |
| `Harris Teeter` | ambiguous | Harris Teeter | supermarket | pass | outcome ambiguous |
| `Whole Foods` | ambiguous | Whole Foods Market | supermarket | pass | outcome ambiguous |
| `Whole Foods Durham` | resolved | Whole Foods Market | supermarket | pass | lead role facility; locality matched; leader name matches |
| `Durham Whole Foods` | resolved | Whole Foods Market | supermarket | pass | lead role facility; locality matched; leader name matches |
| `the Whole Foods in Durham` | resolved | Whole Foods Market | supermarket | pass | lead role facility; locality matched; leader name matches |
| `Chapel Hill` | ambiguous | Chapel Hill | gym | pass | ambiguous, so no confident claim was made |
| `Franklin Street` | resolved | Franklin Street | — | pass | confident, 325 m away |
| `NC State` | resolved | NC State | college_university | pass | confident, 4805 m away |
| `Hillsborough` | ambiguous | Hillsborough Mart | convenience | pass | ambiguous, so no confident claim was made |
| `Hillsborough Street` | ambiguous | Hillsborough Street Exxon | gas_station | pass | ambiguous, so no confident claim was made |
| `Cary` | ambiguous | Cary | — | pass | ambiguous, so no confident claim was made |
| `Morganton` | not_found | — | — | pass | outcome not_found |
| `Asheville` | ambiguous | Grove Park Inn, Asheville NC | hotel | pass | outcome ambiguous |
| `Wegmans Chapel Hill` | ambiguous | Wegmans | supermarket | pass | lead role facility; leader name matches |
| `Trader Joes` | ambiguous | Trader Joe's | supermarket | pass | lead role facility; leader name matches |
| `Trader Joe's` | ambiguous | Trader Joe's | supermarket | pass | lead role facility; leader name matches; same leader as its pair |
| `Duke Street Durham` | ambiguous | Durham Pediatrics at North Duke Street | pediatric_clinic | pass | lead role facility |
| `Durham Station` | resolved | Durham Station | bus_station | pass | lead role station; leader name matches |
| `Durham train station` | ambiguous | Train Station | platform | pass | outcome ambiguous; a candidate named ['durham', 'station'] is 466 m away |
| `Bay Leaf` | ambiguous | Bay Leaf Fire Department | fire_station | pass | lead role facility |
| `ATM` | ambiguous | ATM | atm | pass | outcome ambiguous |
| `parking` | resolved | Parking | parking | **FAIL** | outcome 'resolved', wanted one of ['ambiguous', 'not_found'] |
| `Downtown Durham` | ambiguous | Downtown Durham | farmers_market | pass | ambiguous, so no confident claim was made |
| `Durham` | ambiguous | Durham | station | pass | ambiguous, so no confident claim was made |
| `` | not_found | — | — | pass | outcome not_found; no candidates, as required |
| `zzzzqqq not a place` | not_found | — | — | pass | outcome not_found; no candidates, as required |
| `Harris Teeter` | ambiguous | Harris Teeter | supermarket | pass | outcome ambiguous; 8 corroborated |

**Failures, with the assertion each one guards:**

- `parking` — outcome 'resolved', wanted one of ['ambiguous', 'not_found']. *KNOWN OPEN FAILURE, cause named: a single Overture listing named exactly 'Parking' is the sole exact match at 1.000 and wins outright. Unlike a bare locality, this index CAN hold car parks, so the honest fix is to route a bare category noun to the category criterion rather than to the anchor resolver — a product-routing decision, not a scoring tweak, so it is recorded rather than guessed at. Left red deliberately.*
