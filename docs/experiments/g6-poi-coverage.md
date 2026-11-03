# G6: POI coverage and licence (generated 2026-11-03 13:31:43)

Slice bbox 550x401 cells. Overture release 2026-10-21.0: raw 57719, accepted 57719, rejected 0 (fail-closed resolver; every source entry carried an explicit allow-listed licence: {'CDLA-Permissive-2.0': 53147, 'Apache-2.0': 3813, 'CC0-1.0': 759}). Observed source datasets: ['AllThePlaces', 'Birdeye', 'BrightQuery', 'DAC', 'Foursquare', 'Microsoft', 'OpenTravel', 'Overture', 'Overture-signals', 'PinMeTo', 'RenderSEO', 'Uberall', 'meta'].
OSM POIs (QuackOSM, exploded tags): 4337 features.

Agreement = other source has a feature within 50 m (not recall; see manual audit below).

| category | overture n | osm n | overture with OSM within 50 m | osm with Overture within 50 m | overture dup pairs (25 m, same name) | notes |
|---|---|---|---|---|---|---|
| grocery | 285 | 146 | 126 | 109 | 5 |  |
| park | 363 | 545 | 63 | 63 | 0 |  |
| playground | 22 | 515 | 8 | 11 | 0 |  |
| coffee | 354 | 136 | 102 | 91 | 5 |  |
| pharmacy | 235 | 58 | 46 | 44 | 0 |  |
| school | 278 | 221 | 79 | 74 | 0 |  |
| library | 81 | 35 | 39 | 28 | 2 |  |
| transit_stop | 51 | 2462 | 24 | 21 | 0 | Overture has stations/facilities only; bus stops come from OSM |
| trail | 88 | 0 | 0 | 0 | 0 | no OSM tag mapping yet |

## Manual audit (to fill)

Audit 25 POIs per category against an independent inventory (e.g. municipal park lists, chain store locators, NCES for schools); record precision and recall per source and choose the preferred source per category.

| category | sample n | overture precision | overture recall | osm precision | osm recall | preferred source | reason |
|---|---|---|---|---|---|---|---|

## Independent recall check: schools vs NCES (automated part of the manual audit)

Run 2026-11-03 14:58:32. Truth set: 11 Chapel Hill-Carrboro public schools with NCES EDGE 2023-24 coordinates (cached by the CHCCS_geospatial project). A source 'finds' a school if any of its selected school-category features lies within 150 m of the NCES point. This is recall against an independent inventory, not agreement between our two sources.

| source | schools found | of | recall |
|---|---|---|---|
| Overture | 11 | 11 | 100% |
| OSM | 10 | 11 | 91% |

Overture missed: none.
OSM missed: Scroggs Elementary.

Scope limit: this covers one district and one category. Parks, playgrounds and groceries still need their own independent inventories (municipal park lists, chain store locators) before a per-category source preference is defensible.
