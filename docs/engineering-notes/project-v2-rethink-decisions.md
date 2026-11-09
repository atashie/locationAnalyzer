---
name: project-v2-rethink-decisions
description: "Decisions and status for the ground-up rethink (V2) of the Distance Finder / location-finder product, kicked off 2026-11-03"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-03T18:01:06.205Z
---

On 2026-11-03 the user restarted the location-finder product from first
principles, reusing existing algorithms. Kickoff decisions:
- Wedge: home-search region finder (hotel/trip and site selection later).
- Geography: tiered - precompute the Research Triangle; approximate elsewhere.
- Reuse CHCCS_geospatial and localUpdates code; rebuild lives in this repo in a
  new top-level directory (planned `v2/`); V1 code kept for reference.
- Intent: friends and family first, documented for later public/monetized use.
- Listings linkage must-have via legal/free means only (deep links; no scraping).
- Branch `v2-rethink`; research in docs/research/ (00-09), plans in docs/plans/.

Round-2 decisions (2026-11-03, after research + two Codex passes):
- Budget Tier 1 (~$20-35/mo: one 8 GB VPS w/ self-hosted Valhalla + Cloudflare static).
- Acceptable commute-boundary error ~10% of the limit (median <=10%, p90 <=20%).
- Transit must be included EARLY (complex case worth learning); transit
  scheduled-anchor experiment is in Phase 0.
- City/ZIP listings fallback acceptable if bbox deep links are fragile.
- Privacy not a priority now (share URLs may carry anchors; revisit pre-public).
- Routing engine (Valhalla vs ported CHCCS gridded Dijkstra): decide by
  experiment. Trust order the user stated: experimental results > research > priors.

Key research-settled facts: CHCCS engine forces roads bidirectional (wrong for
drive; must use transposed graph); TripAdvisor dropped (deprecated API, ToS);
Google Places store place_id only; Overture + separable OSM as POI base;
interaction = map-first editable criteria cards (NL prominence to be tested).

**Why:** V1 UI was clunky and had a live minutes-as-miles bug; AI advances allow
rethinking. **How to apply:** When a design question arises, prefer running a
cheap experiment over arguing from research or priors. Next step: Phase 0
implementation plan (docs/plans/), Codex pass 3 on it, then run the experiments.
See [[reference-sibling-repos]], [[feedback-codex-adversarial-review]],
[[reference-codex-runtime-quirks]], [[feedback-experiments-over-priors]].
