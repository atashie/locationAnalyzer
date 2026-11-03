# Phase 0 experiment results

One file per gate. Each file states the question, the method actually run, the raw numbers,
the pass criterion from `../research/08-synthesis.md` §6 and owner decision 12 (median absolute
error at a threshold T ≤ 0.10·T, p90 ≤ 0.20·T), and a verdict. Claims here are measured on this
machine on the dates given; they are not research estimates.

| Gate | File | Status |
|---|---|---|
| G6 POI coverage and licence | g6-poi-coverage.md | generated section done; manual audit pending |
| Geocoding contract | geocoding.md | done (verdict recorded) |
| G2 Valhalla self-host and anchors | g2-valhalla.md | slice build + anchor latency measured; NC build on the VPS still blocking |
| Transit engine (owner decision 13) | transit.md | done — MOTIS adopted, Valhalla cannot arrive-by |
| G1 engine and layer primitive | g1-routing.md | decided — Valhalla costing + its expansion tree + our snapping |
| G4 listings handoff | g4-listings.md | links generated; 6 regions invalid, regenerate; owner device sessions pending |
| G3 browser rendering | g3-rendering.md | pending |
| G5a early interaction comparison | g5a-interaction.md | pending |
| Phase 0 decisions | phase0-decisions.md | revision 2, corrected against Codex pass 4 |
