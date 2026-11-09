# Phase 0 experiment results

One file per gate. Each file states the question, the method actually run, the raw numbers,
the pass criterion from `../research/08-synthesis.md` §6 and owner decision 12 (median absolute
error at a threshold T ≤ 0.10·T, p90 ≤ 0.20·T), and a verdict. Claims here are measured on this
machine on the dates given; they are not research estimates.

| Gate | File | Status |
|---|---|---|
| G6 POI coverage and licence | g6-poi-coverage.md | generated section done; manual audit pending |
| Geocoding contract | geocoding.md | done (verdict recorded) |
| G2 Valhalla self-host and anchors | g2-valhalla.md | passed — NC build 121 s, serves from 548 MiB on 2 vCPU/8 GB; concurrency-8 target replaced by an anchor cache |
| Transit engine (owner decision 13) | transit.md | done — MOTIS adopted and re-validated on the widened metro (27/28 pairs, Raleigh 0 -> 1,080 stops) |
| G1 engine and layer primitive | g1-routing.md | decided per mode — walk = our graph; bike/drive = Valhalla expansion + our snapping |
| G4 listings handoff | g4-listings.md | links generated; 6 regions invalid, regenerate; owner device sessions pending |
| G3 browser rendering | g3-rendering.md | page + real-data exporter built and self-tested; needs a device run |
| G5a early interaction comparison | g5a-interaction.md | prototypes + protocol built on real G4 regions; needs household sessions |
| Independent engine spot check | spotcheck-engines.md | ours vs Valhalla vs OSRM on 12 real journeys; Google leg needs a key |
| Phase 0 decisions | phase0-decisions.md | revision 2, corrected against Codex pass 4 |
| S3 instrument build | s3-instrument-build.md | measurement apparatus for S3 |
| S3 whole-minute encoding at a threshold | s3-encoding.md | measured — `rint` shows 8.15% of its 10-minute passes wrongly to a minute-only client; `ceil` is exact. Decision pending at plan §0 step 6 |
| Walked-journey audit sheets | audit/ | 21 journeys emitted for grocery/walk; owner columns blank, see audit/README.md |

## Notes for Phase 1

- **MapLibre pinning is inconsistent between the two spikes:** the G3 rendering page pins **5.24.0** (established as the last line shipping a UMD bundle, and verified to have no native colour-mapping for a plain raster layer) while the G5a prototypes pin **3.6.2**. Phase 1 must pick one; prefer the version G3 measured against.
- **Six of the 20 G4 regions are invalid** (anchors south of the slice edge) and the G5a prototypes draw from the same file, so regenerate the regions on a buffered extract before any session uses them.
