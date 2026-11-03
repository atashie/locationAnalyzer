# V2 Rethink — Research Program

**Started:** 2026-11-03 · **Branch:** `v2-rethink` · **Status:** research complete; synthesis v0.3 awaiting owner decisions (see 08 §11)

## Why this exists

V1 of Distance Finder works but its interface (criteria form → Leaflet map → polygon)
is clunky and not fit for purpose. Before rebuilding, we are doing a thorough review
of comparable tools, open-source building blocks, data sources and their licenses,
compute/serving architectures, and interaction models, so that the V2 design rests
on evidence rather than on the assumptions baked into V1.

The product idea in one sentence: **a user describes where they want to be, with
proximity constraints (travel time or distance to specific places and to categories
of amenities), and gets a region plus the real things inside it (listings, places).**

Use cases, in build order:
1. **Home-search region finder** (the wedge). Two commutes, parks, groceries, airport,
   a specific school, a relative's house.
2. **Hotel / trip stay finder.** Near a WeWork, a stadium, a client; by bus, tram,
   metro, car, bike, walk; near coffee and wine bars.
3. **Business site selection.** Demographics (children, elderly, traffic counts)
   plus proximity, linked to commercial property.

Decisions already made are in [`../plans/2026-11-03-v2-rethink-decisions.md`](../plans/2026-11-03-v2-rethink-decisions.md).

## Method

Seven parallel research streams, each producing one document below. Every document
follows the same skeleton: executive summary → tables → detailed notes → implications
for our build → open questions → dated sources. Claims that could not be confirmed
are marked "(unverified)". After the streams land, the set is reviewed adversarially
by Codex (a different model family) and the findings are synthesized into a single
recommendation document, which is itself Codex-reviewed before any planning begins.

## Documents

| # | Document | Stream | Status |
|---|----------|--------|--------|
| 00 | [Existing assets audit](00-existing-assets-audit.md) | What is reusable from this repo, CHCCS_geospatial, and localUpdates | complete |
| 01 | [Consumer landscape: home search](01-consumer-landscape-home-search.md) | Zillow/Redfin/Walk Score/TravelTime/isochrone house-hunting tools | complete |
| 02 | [Hotel and site-selection landscape](02-landscape-hotel-and-site-selection.md) | Google Hotels/Booking; Esri BA/Placer/SiteZeus; free-data floor | complete |
| 03 | [Open-source landscape](03-open-source-landscape.md) | Routing engines, accessibility projects, precompute/serving, LLM-to-GIS agents | complete |
| 04 | [Data sources and legal](04-data-sources-and-legal.md) | Listings access, POIs, Census, traffic, GTFS, quality-of-place layers, ToS verdicts | complete |
| 05 | [Routing and precompute architecture](05-routing-and-precompute-architecture.md) | Hosted vs self-hosted routing, gridded travel-time precompute, cheap serving | complete |
| 06 | [UX and interaction model](06-ux-and-interaction-model.md) | User needs, reception of existing tools, HCI principles, recommended model | complete |
| 07 | [Codex adversarial review](07-codex-adversarial-review.md) | Cross-model critique of 00–06 | complete (pass 1: 00–05, gpt-5.6-sol) |
| 08 | [Synthesis and recommendation](08-synthesis.md) | What we are building and why | v0.3, ready for owner review |
| 09 | [Codex adversarial review, pass 2](09-codex-adversarial-review-pass2.md) | Cross-model critique of 06 and 08 (gpt-6.1-sol) | complete |

## Prior in-house research this builds on

- `../../../localUpdates/docs/research-findings.md` — Phase 0 survey (2026-06-28) with
  verified ToS verdicts for Google Places, Yelp, TripAdvisor, Foursquare, Overture,
  and the Census geocoder; PostGIS/pgvector stack; legal posture for scraping.
- `../../../localUpdates/docs/legal-and-data-use.md`
- `../../../CHCCS_geospatial/src/school_desert.py` — gridded multi-source Dijkstra
  travel-time method with documented speed model.
