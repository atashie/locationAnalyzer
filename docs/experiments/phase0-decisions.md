# Phase 0 decision memo

**Date:** 2026-11-03 · **Revision 3.** Revision 2 was rewritten after Codex adversarial pass 4
(`../research/11-codex-adversarial-review-pass4-phase0.md`) found four factual errors and one
omission in revision 1; revision 3 then **reversed D1** when the walk exact-pair comparison
finished and showed our own model passing at every threshold. · **Branch:** `v2-rethink` ·
**Status:** for owner review
**Inputs:** the experiment files in this directory, the plan in `../plans/2026-11-03-phase0-experiments.md`, the design in `../research/08-synthesis.md`, the owner decisions in `../plans/2026-11-03-v2-rethink-decisions.md`, and Codex passes 3 and 4.

Per the owner's trust order — **experimental results, then the research, then our priors** — claims
are tagged **[measured]** (observed here today, numbers in the cited file), **[research]** (from the
survey, not observed here) or **[assumed]** (neither). Decisions rest on the first two; load-bearing
assumptions are named as such.

---

## 0. Corrections to earlier revisions

Revision 1 overstated the case. What was wrong, and what the evidence actually says:

| # | Earlier revision claimed | Correct |
|---|---|---|
| 1 | The adopted layer method builds a category layer in about a second (presented as settled) | Its own equivalence check had **failed** (1,635 s max difference) and revision 1 omitted that. A follow-up against exact engine times shows **neither raster method meets the owner's tolerance**; the primitive had to change (D1) |
| 2 | "All **11** valid in-slice pairs matched Transitous" | **10** pairs (5 valid origins × 2 valid anchors). All 10 matched |
| 3 | Anchors answer at p95 0.30 s with zero failures in 408 requests | True at **concurrency 1**. At concurrency 8 on 2 vCPUs the measured p95 is **1.363 s (target 0.8)** and **2.303 s (target 2.0)** — both targets **failed**, and revision 1 quoted only the favourable row |
| 4 | Portal bounding boxes are "median ~3× and up to ~3.9×" the region | **median 3.12 over all 20 regions, 3.06 over the 14 valid ones, max 5.45**. Six regions used anchors south of the slice edge and were not flagged, despite the same error being corrected in `transit.md` |
| 5 | "Everything a machine can decide alone is decided" | False. Several machine-addressable checks remained open; three are now done (§0 item 1, the G4 correction, the school recall check) and others are listed in §5 |
| 6 | Own-graph is 30× more expensive than Valhalla per layer | Compares a cold Python graph build against an already-resident tile server, and graph preparation amortises across categories. The honest comparison is in D1 |
| 7 | G5a prototypes "built" | The interaction prototypes were still being written when revision 1 was filed |
| 8 | "Every mode fails the owner's tolerance at p90" (revision 1 and 2) | Read off the raster comparison, which measures Valhalla's contour error. On exact pairs the **walk model passes at every threshold** and is unbiased; only drive fails (D1) |

The underlying experiments were sound; the reporting selected the favourable readings. The habit to
keep is the one that caught the out-of-slice origins and the stale Duke feed: look for the error
before claiming the result.

---

## 1. Decisions

### D1. The engine choice is per mode: our own graph for walking, Valhalla for driving, and Valhalla's *expansion tree* rather than its isochrone raster wherever Valhalla is the source

**[measured]** `g1-routing.md`, verdict revision 3. Exact-pair comparison against Valhalla's
`sources_to_targets`, which is the only valid way to judge a model: the layer-level raster
comparison used in revision 2 turned out to be dominated by the raster's own error.

| Mode | median error | p90 | signed median | own faster | against decision 12 |
|---|---|---|---|---|---|
| **walk** (600 cells) | 0.3-0.8 min (2-3% of T) | 1.6-5.5 min (10-16%) | **+0.2 min** | 29-43% | **passes at every threshold** |
| **drive** (304 cells) | 3.2-8.1 min (32-41%) | 5.5-12.4 min (55-62%) | **-5.4 min** | 98-100% | fails at every threshold |
| bike | pending | pending | pending | pending | pending |

Walking is a near-constant speed on a network with no one-ways, turn restrictions, signals or
congestion, so our model has little to get wrong and is **unbiased**: a +0.2 minute signed median
with "own faster" near 35% is symmetric noise. Driving is where the modelling lives, and it is
exactly what we dropped by porting the CHCCS friction speeds without its intersection penalties.

*Separately, Valhalla's isochrone GeoTIFF is not a per-cell time.* Paired against exact values on
240 cells: the multi-location raster errs by a median 88 s and p90 355 s, the per-POI minimum by
88 s and 430 s, and both exclude 9-31% of boundary cells. Its `/expansion` search tree does far
better, at a median 69 s, p90 271 s and **zero false inclusions at every threshold**, and the
remaining +66 s conservative bias was a known artifact of charging a whole edge traversal.
`duration` and `distance` are cumulative at the settled end and `pred_edge_id` identifies the near
end, so `traveltime/expansion.py` now reconstructs both endpoint times exactly with no speed
assumption; that corrected version still needs a paired re-measurement.

**The decision:** walk layers from our own graph, drive layers from Valhalla's expansion, bike
pending its measurement. Both paths feed the same `snap.cell_seconds_from_arrival`, so there is one
grid contract, one nodata convention and one interpolation routine whichever engine supplies the
times. Valhalla remains the only source for arbitrary anchors.



*Cost, stated honestly.* Valhalla answers an arbitrary anchor at p95 0.30 s (auto 25 min) at
concurrency 1 and builds an expansion for three POIs in 0.74 s. Our own-graph path spent ~32 s per
mode per category, but 29 s of that is graph load and preparation that **amortises across all
categories of a mode**, so the honest marginal comparison is 0.04 s of Dijkstra against 0.74 s of
expansion — our algorithm is faster, it is the *calibration* we lack. The architectural reason to
choose Valhalla is that it already encodes access rules, one-ways, turn restrictions and a
maintained costing model, not that it is faster per layer.

### D2. Transit needs a second engine, MOTIS, and the surface is not built yet

**[measured]** `transit.md`. Valhalla cannot answer a commuter's question: `multimodal` with
`date_time.type=2` (arrive by) returns **HTTP 501, "Arrive by for multimodal not implemented yet"**.
MOTIS self-hosted does: import of the slice plus seven Triangle GTFS feeds took **4 s** and 130 MB,
the server idles at **80 MiB**, `plan?arriveBy=true` answers in ~0.1 s and `one-to-all?arriveBy=true`
in **0.03 s** returning 478–584 reachable stops with each stop's latest feasible departure. **All 10
valid in-slice pairs matched** the public Transitous instance to the minute.

What that does **not** establish, and Codex is right to insist on it: Transitous runs the same engine
on the same feeds, so exact agreement validates our ingestion and configuration, **not journey
accuracy**; `one-to-all` returns *stops*, and a cell-level arrival surface still needs the legal
street access leg from cell to stop, a direct-walk alternative, and a stated deadline/window policy;
and the generated config carries `onetoall_max_travel_minutes: 90`, whose cap behaviour is untested.
MOTIS is adopted as the transit engine; the transit **surface** is Phase 1 work with its own
acceptance test, including hand-checked journeys against published timetables.

The research budgeted 4–8 GB for a transit router **[research]**; the measured idle footprint is two
orders of magnitude smaller, so transit does not need its own budget tier. Import and query **peaks**
were not sampled, so that is an idle figure, not a budget.

### D3. Overture is the place base; OSM supplies what Overture lacks

**[measured]** `g6-poi-coverage.md`. Overture release 2026-10-21.0 over the slice: 57,719 places,
**160,392 source entries, zero quarantined**, all explicitly allow-listed (CDLA-Permissive-2.0
155,820; Apache-2.0 3,813; CC0-1.0 759) across 13 observed datasets. Note what that does and does
not prove: every row carried an explicit licence, so the per-release manifest fallback was **never
exercised** on this data; its regression test, not this run, is what shows an unknown later source
is rejected. The resolver validates every source entry but returns a single scalar licence, which
cannot represent per-source obligations — Phase 1 should retain the validated set.

Coverage, with one independent check:

| Category | Overture | OSM | independent recall |
|---|---|---|---|
| grocery | 285 | 146 | not yet audited |
| coffee / pharmacy / library | 354 / 235 / 81 | 136 / 58 / 35 | not yet audited |
| **school** | 278 | 221 | **Overture 11/11, OSM 10/11 against NCES EDGE** |
| playground | 22 | **515** | not yet audited |
| transit stop | 51 | **2,462** | not yet audited |
| park | 363 | 545 (only 63 agree within 50 m) | **unresolved** |

Only the school row rests on an independent inventory. Record counts are abundance, not quality:
the selectors do not screen operating status or public access, and a polygon centroid is not an
accessible park entrance. Parks and playgrounds remain unresolved and parks are a headline amenity.

### D4. Street addresses from the Census geocoder; place *names* from our own index, metro-bounded

**[measured]** `geocoding.md`. Census matched **33/40** slice addresses (so **7 failed**, and 4 of
the matches exceeded 250 m) at 0.10 s median, 81 m median error; Nominatim matched 36/40 but is
dev-only under its usage policy. Neither is a name resolver: Census resolved **none** of ten
place-name queries, and unbounded Nominatim returned "UNC Hospitals" in Morganton, 180 km away, and
"Southpoint" in Wisconsin. The decision is the provider split; the **name resolver against our own
metro-bounded place index, the candidate chooser and the correction flow are unbuilt and untested**.

### D5. Candidate grid resolutions are 100 m walk/bike and 200 m drive — not established

**[measured]** that Valhalla emits isochrone GeoTIFFs at 0.001° for pedestrian/bicycle (~90 × 111 m)
and 0.002° for auto (~180 × 223 m), uint16 seconds, re-centred per request. **[assumed]** that a
200 m drive grid is therefore the right product resolution. Codex is right that this does not close
the error budget: a 200 m cell centre is up to 141 m from its corner, and uint8 minute encoding adds
up to 30 s, which is 20% of the whole tolerance at a 25-minute threshold. With the primitive now
being the expansion tree rather than the raster, the pixel-size argument partly dissolves and the
question becomes cell size versus within-cell travel-time variation. Treat 100/200 m as candidates
and measure the encoded surface end to end before freezing the contract.

### D6. Listings handoff stays deep-link-first, and we must always draw the region ourselves

**[measured]** `g4-listings.md`, corrected. Across 20 generated two-anchor regions the portal
bounding box is a median **3.12×** the region area and up to **5.45×**, and several regions are
disconnected (up to 4 parts). A portal link can therefore never stand in for the result. Six of the
20 regions used out-of-slice anchors and are now flagged invalid; they must be regenerated on a
buffered extract before the owner's device sessions. Whether the links themselves survive desktop,
iOS and Android is unmeasured; owner decision 14 already accepts a city/ZIP fallback, so this does
not block Phase 1.

### D7. Every source needs an enforced freshness gate — required, not yet implemented

**[measured]** `transit.md`. Validating each GTFS calendar against the test date reproduced 1,310 /
526 / 1,238 / 2,486 / 870 / 692 active trips for six feeds and **zero for Duke Transit, whose
calendar ended 2025-08-10** at the currently published URL. Chapel Hill's calendar runs to 2099,
which shows a distant end date alone proves nothing. Acquisition currently tolerates download
failures and asserts nothing about age or service on the requested date. This is a requirement with
no implementation yet.

---

## 2. What Phase 0 changed about the plan

| Synthesis position | After the experiments |
|---|---|
| Own-graph precompute "if Gate G1 pays off"; Valhalla as reference | **Per mode:** our graph wins for walking (unbiased, passes), Valhalla for driving; our snapping serves both (D1) |
| Layer = isochrone raster | Layer = expansion edges + snapping; the raster does not meet tolerance (D1) |
| Transit deferred to Phase 3 | Transit engine chosen now (MOTIS); the surface is Phase 1 work (D2) |
| Transit router needs 4–8 GB, own budget tier | 80 MiB idle; no separate tier (D2) |
| 100 m grid throughout | Candidate 100 m walk/bike, 200 m drive, unvalidated (D5) |
| Geocoder "chosen and tested in Phase 0" | Provider split chosen; name resolution unbuilt (D4) |
| Tier 1 ≈ $20–35/month on 8 GB, provisional | Still provisional, and now with a **measured concurrency-8 latency failure** to resolve as well as the NC build |

---

## 3. Gate status

| Gate | Status | What remains |
|---|---|---|
| G6 POI coverage and licence | **partly passed** | Licence partition clean but untested on a hard case; schools audited independently; parks, playgrounds, groceries need inventories |
| Geocoding contract | **partly passed** | Provider split decided; name resolver and correction flow unbuilt |
| G1 engine and primitive | **decided per mode, bike pending** | Walk = own graph (passes); drive = Valhalla expansion + snapping; bike unmeasured. The exact expansion reconstruction needs a paired re-measurement |
| Transit engine | **engine chosen; surface not built** | Street access composition, deadline/window policy, 90-minute cap behaviour, hand-checked journeys |
| G2 Valhalla self-host | **not passed** | NC build on the intended host, **and** the concurrency-8 p95 failure (1.363 s vs 0.8; 2.303 s vs 2.0) |
| G4 listings handoff | **links generated, fixtures contaminated** | Regenerate on a buffered extract; owner device sessions |
| G3 browser rendering | **page and exporter built** | Needs a desktop, throttled-4G and phone run |
| G5a interaction | **in progress** | Prototypes being written; then 3–5 household sessions |

Two gates need the owner (G4 devices, G5a households) and one needs a real phone (G3). Everything
else listed above is machine-addressable and open.

---

## 4. Architecture after Phase 0

```
 PRECOMPUTE (monthly)                             STATIC TIER (Cloudflare, ~$0)
 Geofabrik NC PBF ──> Valhalla tiles              R2: layers/{metro}/{mode}/{category}
 GTFS x7, freshness-gated ──> MOTIS timetable          uint8 minutes + versioned manifest
 Overture 2026-10-21.0, fail-closed licence            places/{metro}.parquet, source-native
   + OSM for playgrounds / transit stops          Pages: SPA (MapLibre; Worker algebra or
 Valhalla /expansion per category                        server-rendered mask, per G3)
   ──> our nearest-edge snapping ──> layers
 MOTIS one-to-all arriveBy + street access        ON-DEMAND (one 8 GB VPS)
   ──> transit arrival surface  [to build]         Valhalla: anchor arrival isochrones
                                                   MOTIS:    transit anchors and surfaces
                                                   FastAPI:  constraint algebra, places, links
                                                   DuckDB:   places, cache, logs
```

`locfinder/traveltime/` is now part of the pipeline, consuming Valhalla's expansion output. Its own
speed model is retained only as a documented fallback.

---

## 5. Open risks, and what is cheapest to close

Ranked by Codex's cheapest-risk-reduction ordering, adjusted for what is already done:

1. **Re-measure the corrected expansion reconstruction**, and run the bike exact-pair comparison to
   settle the third mode. Both are local and need no new infrastructure.
2. **Build one complete inbound transit surface** for an in-slice anchor and hand-check it against
   published timetables, measuring the 90-minute cap and import/query peaks.
3. **Rerun interactive performance cleanly** with valid anchors only, isolating the latency run from
   precompute contention, and separating semantic failures from HTTP 200s.
4. **Widen the extract south to ~35.70** with a routing buffer beyond the evaluation bounds, then
   regenerate the G4 fixtures. This caused three invalid transit rows and six invalid regions.
5. **Finish the independent POI inventories** for parks, playgrounds and groceries.
6. **Then** build North Carolina on the intended host and settle G2.

Remaining uncertainties that no amount of our own measurement will settle: neither engine has
traffic data, so drive times are a model's opinion and the UI must keep saying "estimated, modelled
from road speeds" **[assumed]** to be adequate; and the exact matrix is the engine's reference, not
ground truth, so a small set of hand-timed real journeys would be worth more than another 10,000
synthetic comparisons.

---

## 6. Recommended next step

Do items 1–4 above, which are all local and cheap, before committing to hosting. Phase 1 then starts
from a primitive that meets the tolerance, a transit surface that has been checked against a
timetable, and fixtures that are not contaminated. Phase 1 must also explicitly inherit the
responsibilities the dropped speed model was carrying: legal access and entrances, cutoff and nodata
semantics, stable grid and version metadata, and independent acceptance tests. Removing our costing
model did not remove those requirements.
