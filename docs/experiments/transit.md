# Transit engine experiment (2026-11-03 15:34:37)

**Question.** Scheduled INBOUND transit: arrive by 2026-11-10T08:00:00-05:00 (Tuesday). Owner decision 13 put transit in Phase 0.
Metro **triangle**, evaluation bbox -79.2,35.7,-78.5,36.15, routing data buffered to -79.35,35.55,-78.35,36.3. Every point below is asserted inside the evaluation bbox.

## 1. Valhalla multimodal: arrival semantics

- `date_time.type=2` (arrive by) at UNC Hospitals: **HTTP 501** — `{"error_code":141,"error":"Arrive by for multimodal not implemented yet","status_code":501,"status":"Not Implemented"}`
- Departure isochrones (`type=1`) do work (G2), so Valhalla can answer "where can I get to by 08:00 leaving now" but not "where can I live and still arrive by 08:00". For a commute product the second question is the one users ask.

## 2. MOTIS one-to-all (the arrival surface primitive)

| anchor | reachable stops within 45 min | response s |
|---|---|---|
| UNC Hospitals | 478 | 0.03 |
| Duke University Hospital | 584 | 0.02 |
| Downtown Raleigh (Moore Sq) | 1080 | 0.04 |
| NC State Bell Tower | 896 | 0.04 |

Each entry carries the stop, its coordinates, and the latest feasible departure for the 08:00 arrival, which is exactly what a precomputed arrival surface needs (stops -> street access -> cells).

## 3. Point-to-point commute, latest feasible departure

Duration = arrival deadline minus the latest departure that still arrives by it (waiting included).

| origin | anchor | MOTIS self-hosted (min) | mode | Transitous (min) | note |
|---|---|---|---|---|---|
| Carrboro (Weaver St) | UNC Hospitals | 31 | transit | 31 | |
| Carrboro (Weaver St) | Duke University Hospital | 57 | transit | 57 | |
| Carrboro (Weaver St) | Downtown Raleigh (Moore Sq) | 78 | transit | 78 | |
| Carrboro (Weaver St) | NC State Bell Tower | 78 | transit | 78 | |
| Durham (9th St) | UNC Hospitals | 69 | transit | 69 | |
| Durham (9th St) | Duke University Hospital | 32 | transit | 32 | |
| Durham (9th St) | Downtown Raleigh (Moore Sq) | 78 | transit | 78 | |
| Durham (9th St) | NC State Bell Tower | 78 | transit | 78 | |
| Chapel Hill (Franklin St) | UNC Hospitals | 15 | transit | 15 | |
| Chapel Hill (Franklin St) | Duke University Hospital | 50 | transit | 50 | |
| Chapel Hill (Franklin St) | Downtown Raleigh (Moore Sq) | 69 | transit | 69 | |
| Chapel Hill (Franklin St) | NC State Bell Tower | 69 | transit | 69 | |
| Durham (Hayti) | UNC Hospitals | 64 | transit | 64 | |
| Durham (Hayti) | Duke University Hospital | 31 | transit | 31 | |
| Durham (Hayti) | Downtown Raleigh (Moore Sq) | 75 | transit | 75 | |
| Durham (Hayti) | NC State Bell Tower | 75 | transit | 75 | |
| Raleigh (Cameron Village) | UNC Hospitals | 76 | transit | 76 | |
| Raleigh (Cameron Village) | Duke University Hospital | 87 | transit | 87 | |
| Raleigh (Cameron Village) | Downtown Raleigh (Moore Sq) | 18 | transit | 18 | |
| Raleigh (Cameron Village) | NC State Bell Tower | no itinerary |  | no itinerary | |
| RTP (Davis Dr) | UNC Hospitals | 79 | transit | 79 | |
| RTP (Davis Dr) | Duke University Hospital | 65 | transit | 65 | |
| RTP (Davis Dr) | Downtown Raleigh (Moore Sq) | 63 | transit | 63 | |
| RTP (Davis Dr) | NC State Bell Tower | 46 | transit | 46 | |
| Cary (Chatham St) | UNC Hospitals | 92 | transit | 92 | |
| Cary (Chatham St) | Duke University Hospital | 92 | transit | 81 | |
| Cary (Chatham St) | Downtown Raleigh (Moore Sq) | 62 | transit | 62 | |
| Cary (Chatham St) | NC State Bell Tower | 62 | transit | 62 | |

MOTIS answered 27/28 pairs; 27 used at least one transit leg. Median |MOTIS - Transitous| = 0 min over 27 comparable pairs (both are MOTIS, so agreement checks feed coverage, not accuracy).

## Verdict

**Valhalla cannot serve the transit use case** the product needs: `multimodal` with
`date_time.type=2` (arrive by) returns HTTP 501. Departure isochrones work, but "where can I get to
leaving now" is not the question a commuter asks.

**MOTIS can, and it is cheap.** On the widened Triangle metro (evaluation bbox -79.20,35.70 to
-78.50,36.15; routing data buffered ~15 km):

| Measurement | Value |
|---|---|
| Import, buffered Triangle OSM + seven GTFS feeds | **7 s**, 203 MB |
| Resident memory serving, capped at 2 vCPU / 2 GB | **117 MiB** |
| `one-to-all?arriveBy=true`, 45 min | **0.02-0.04 s**, 478-1,080 reachable stops per anchor |
| `plan?arriveBy=true` | ~0.1 s |
| Pairs answered | **27 of 28**, every one using a transit leg |
| Agreement with the public Transitous instance | **26 of 27 identical to the minute** |

Each `one-to-all` entry carries a stop, its coordinates and the latest feasible departure for the
08:00 arrival, which is the primitive a precomputed arrival surface needs.

**The widening fixed the Phase 0 defect, and the fix is verified rather than assumed.** On the old
slice, downtown Raleigh returned **0** reachable stops and every Raleigh and Cary pair failed or
returned an absurd 570 minutes, because those points lay south of the extract edge. On the widened
metro the same anchors return **1,080** (Moore Square) and **896** (NC State) reachable stops, and
all seven previously-failing pairs now answer with real journeys. `transit_compare.py` now asserts
every test point is inside the metro's evaluation bbox, so this class of error fails loudly instead
of looking like a travel-time result.

### What is still not established

- **Transitous is the same engine on the same feeds.** Exact agreement validates our ingestion and
  configuration, not journey accuracy. Independent validation needs hand-checked journeys against
  published timetables. The one disagreement (Cary to Duke: ours 92 min, Transitous 81) is worth
  chasing first, since it is most likely a feed-version difference.
- **`one-to-all` returns stops, not cells.** A cell-level arrival surface still needs the legal
  street access leg from each cell to nearby stops, composed with the walk layer.
- **Direct walking alternatives are missing.** Cameron Village to NC State, about 1.5 km apart,
  returns "no itinerary" from both instances because the query asks for transit and no transit
  itinerary exists. A commute surface must take the minimum of transit and direct walking, so the
  query needs explicit direct modes.
- **The horizon cap is untested.** The generated config carries `onetoall_max_travel_minutes: 90`;
  cap behaviour must be distinguished from genuine unreachability.
- **Feed freshness is not enforced.** Duke Transit's published feed spans 2025-01-06 to 2025-08-10
  and contributes **zero** trips on the test date, while the other six carry 526-2,486. A freshness
  assertion at ingest is a Phase 1 requirement.

### Operational notes

MOTIS must run on the **native** Linux filesystem; a Windows bind mount fails with a resize error.
In this image the binary is `/motis` (not on `PATH`), the `tiles:` block must be removed from the
generated `config.yml` because the vector-tile profile only exists at the image root, and the
container needs to run as root unless the data directory is owned by the image's unprivileged user.
