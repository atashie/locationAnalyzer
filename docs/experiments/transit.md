# Transit engine experiment (2026-11-03 14:52:04)

**Question.** Scheduled INBOUND transit: arrive by 2026-11-10T08:00:00-05:00 (Tuesday). Owner decision 13 put transit in Phase 0.

## 1. Valhalla multimodal: arrival semantics

- `date_time.type=2` (arrive by) at UNC Hospitals: **HTTP 501** — `{"error_code":141,"error":"Arrive by for multimodal not implemented yet","status_code":501,"status":"Not Implemented"}`
- Departure isochrones (`type=1`) do work (G2), so Valhalla can answer "where can I get to by 08:00 leaving now" but not "where can I live and still arrive by 08:00". For a commute product the second question is the one users ask.

## 2. MOTIS one-to-all (the arrival surface primitive)

| anchor | reachable stops within 45 min | response s |
|---|---|---|
| UNC Hospitals | 478 | 0.03 |
| Duke University Hospital | 584 | 0.03 |
| Downtown Raleigh (Moore Sq) ⚠ | 0 | 0.03 |

Each entry carries the stop, its coordinates, and the latest feasible departure for the 08:00 arrival, which is exactly what a precomputed arrival surface needs (stops -> street access -> cells).

> **⚠ Correction (test-design error, found after the run).** The Phase 0 slice extract covers
> latitude 35.80–36.15, longitude −79.15 to −78.55. **Downtown Raleigh (35.7796), Cameron Village
> (35.7920) and Cary Chatham St (35.7880) are south of that edge**, so no street network exists
> there in our MOTIS instance: those rows show "no itinerary" or an absurd 570 minutes because the
> origin or destination could not be attached to the network, not because the engine or the feeds
> are at fault. Rows marked ⚠ are invalid. The 11 unmarked pairs are inside the slice and are the
> result that counts. The same limitation invalidates any G4 region or anchor-latency row that uses
> Cary Downtown or NC State Bell Tower, and it means a real Triangle build must extend south to
> about latitude 35.70 to include southern Wake County.

> **GTFS feed validation (2026-11-10, Tuesday).** Checked each feed's `calendar.txt` /
> `calendar_dates.txt` against the test date: Chapel Hill Transit 1,310 trips, GoCary 526,
> GoDurham 1,238, GoRaleigh 2,486, GoTriangle 870, NC State 692 — and **Duke Transit 0: its feed
> spans 2025-01-06 to 2025-08-10 and is more than a year stale** at the published Trillium URL.
> A freshness gate on every feed is therefore a Phase 1 requirement, not a nicety.

## 3. Point-to-point commute, latest feasible departure

Duration = arrival deadline minus the latest departure that still arrives by it (waiting included).

| origin | anchor | MOTIS self-hosted (min) | mode | Transitous (min) | note |
|---|---|---|---|---|---|
| Carrboro (Weaver St) | UNC Hospitals | 31 | transit | 31 | |
| Carrboro (Weaver St) | Duke University Hospital | 57 | transit | 57 | |
| Carrboro (Weaver St) | Downtown Raleigh (Moore Sq) ⚠ | no itinerary |  | 78 | |
| Durham (9th St) | UNC Hospitals | 69 | transit | 69 | |
| Durham (9th St) | Duke University Hospital | 32 | transit | 32 | |
| Durham (9th St) | Downtown Raleigh (Moore Sq) ⚠ | no itinerary |  | 78 | |
| Chapel Hill (Franklin St) | UNC Hospitals | 15 | transit | 15 | |
| Chapel Hill (Franklin St) | Duke University Hospital | 50 | transit | 50 | |
| Chapel Hill (Franklin St) | Downtown Raleigh (Moore Sq) ⚠ | no itinerary |  | 69 | |
| Durham (Hayti) | UNC Hospitals | 64 | transit | 64 | |
| Durham (Hayti) | Duke University Hospital | 31 | transit | 31 | |
| Durham (Hayti) | Downtown Raleigh (Moore Sq) ⚠ | no itinerary |  | 75 | |
| Raleigh (Cameron Village) ⚠ | UNC Hospitals | 570 | transit | 76 | |
| Raleigh (Cameron Village) ⚠ | Duke University Hospital | 570 | transit | 87 | |
| Raleigh (Cameron Village) ⚠ | Downtown Raleigh (Moore Sq) ⚠ | no itinerary |  | 18 | |
| RTP (Davis Dr) | UNC Hospitals | 79 | transit | 79 | |
| RTP (Davis Dr) | Duke University Hospital | 65 | transit | 65 | |
| RTP (Davis Dr) | Downtown Raleigh (Moore Sq) ⚠ | no itinerary |  | 63 | |
| Cary (Chatham St) ⚠ | UNC Hospitals | 131 | transit | 92 | |
| Cary (Chatham St) ⚠ | Duke University Hospital | 131 | transit | 81 | |
| Cary (Chatham St) ⚠ | Downtown Raleigh (Moore Sq) ⚠ | no itinerary |  | 62 | |

MOTIS answered 14/21 pairs (7 of the 7 failures involve an out-of-slice point, see the correction above); of the 11 valid in-slice pairs, **all 11 matched Transitous to the minute**. Median |MOTIS − Transitous| = 0 min over the 14 pairs both answered (both are MOTIS, so exact agreement checks our feed ingestion and configuration, not routing accuracy). The three large disagreements (Cameron Village, Cary) are the out-of-slice rows.

## Verdict

- **Valhalla cannot serve the transit use case** the product needs (no arrive-by multimodal).
- **MOTIS can**: self-hosted, MIT, import of the slice plus seven Triangle GTFS feeds takes seconds, the server idles at ~80 MiB, and `one-to-all?arriveBy=true` yields the stop-level arrival surface. It must run on the WSL/VPS **native** filesystem (a Windows bind mount fails) and, in this image, as root unless the data directory is owned by the image user.
- Transit therefore enters the architecture as a **second routing service** (MOTIS alongside Valhalla), not as a Valhalla costing. Budget impact: Tier 2 in the synthesis (one extra small container; measured footprint here is far below the 4-8 GB the research assumed).
- **Measured cost:** MOTIS import of the slice plus seven feeds took **4 s**, produced **130 MB** of timetable/graph data, and the server answers `plan` in ~0.1 s and `one-to-all` (478–584 reachable stops) in **0.03 s**, at **80 MiB** resident. Transit is far cheaper than the research assumed (it budgeted 4–8 GB for a transit router).
- Remaining work before a transit layer ships: street access from stops to grid cells (walk layer from the chosen engine), a departure-window policy (single 08:00 deadline vs a window), and GTFS freshness/calendar validation per feed.
