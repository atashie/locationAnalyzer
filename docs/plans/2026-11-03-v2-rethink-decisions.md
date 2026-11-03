# V2 Rethink — Decision Log

**Date:** 2026-11-03 · **Participants:** project owner, Claude (Fable 5.1) · **Branch:** `v2-rethink`

These decisions were made in the kickoff interrogation and bound the research and
planning that follow. Items marked *deferred* are to be settled by the research.

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Wedge use case | **Home-search region finder.** Hotel/trip and business site selection are researched now, built later. | Data is mostly free (OSM/Overture, Census, routing); original motivation; listings linkage is the only hard part. |
| 2 | Geographic scope | **Tiered.** Precompute a few metros (Research Triangle, NC first); on-demand, approximate elsewhere in the US. | Rich and fast where we live; still usable for travel. |
| 3 | Interaction model | ***Deferred to research*** (stream 06 must recommend). Candidates: chat-first; hybrid chat-builds-editable-query; structured UI with AI assist. | V1's form UI was judged clunky; AI capability has moved. |
| 4 | Budget / infrastructure | ***Deferred until research lands.*** | Need cost tables from stream 05 first. |
| 5 | Code reuse | **Reuse this repo, CHCCS_geospatial, and localUpdates.** Rebuild lives in this repo in a new top-level directory; V1 code stays for reference. | Keep old algorithms referenceable; avoid repo sprawl. |
| 6 | Product intent | **Friends and family first**, but document research, notes, and design so it can later serve a wider audience and be monetized. | Licensing and architecture choices must not foreclose a public product. |
| 7 | Listings linkage | **Must-have, within legal and free means.** Deep links bounded to the result region, free/official APIs; no scraping. | Legal exposure and ToS; monetization path. |
| 8 | Git autonomy | **Branch and commit freely; never push.** Owner merges. | Long autonomous runs with reviewable history. |
| 9 | Review process | **Codex as adversarial reviewer** after every major plan and after every analyzed result set. | Different model family catches different errors. |
| 10 | Autonomy | Launch subagents, build test cases, trial tooling without asking; pause only when a decision is genuinely the owner's. | Owner is not watching in real time. |

## Non-goals for now
- Rebuilding V1's UI incrementally.
- Any scraping of listing sites.
- Global coverage.

## Open items the research must close
- Interaction model (decision 3).
- Budget tier and hosting (decision 4).
- Whether transit travel time should be precomputed, on-demand, or deferred.
- Which listings deep-link schemes actually accept a region/bounds.
