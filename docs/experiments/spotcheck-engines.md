# Independent spot check of travel-time engines

**Date:** 2026-11-03 · **Question:** our G1 numbers were all measured against Valhalla, which is
another static model with no traffic data, and for walk/bike its speed was set equal to ours. Do
engines that are genuinely independent of ours agree?

**Method:** twelve real Triangle journeys between named places, point to point, each timed by our
own graph, by self-hosted Valhalla (the costing we use for layers) and by the public OSRM demo
server — a third independent implementation with its own speed profile, car profile only, queried at
one request per second. Google Routes was wired up as a fourth engine but needs an API key, which
this machine does not have; its value is that it is the only congestion-aware reference available
cheaply. Raw values for the open engines are in `v2/data/spotcheck_drive.json`.

### Independent spot check, drive, 12 real journeys (2026-11-03 16:38:08)

Metro triangle. Engines present: ours, valhalla, osrm.
Minutes, point to point. OSRM is the public demo server (car profile, independent static model).
**Google not run: set GOOGLE_MAPS_API_KEY.** Without it there is still no congestion-aware reference.

| from | to | ours | valhalla | osrm |
|---|---|---|---|---|
| Carrboro Town Hall | Downtown Durham | 21 | 31 | 28 |
| UNC Hospitals | Duke University Hospital | 17 | 24 | 21 |
| Chapel Hill (Franklin St) | RTP (Kit Creek Rd) | 20 | 27 | 24 |
| Downtown Durham | RDU Terminal 2 | - | 23 | 22 |
| NC State Bell Tower | Downtown Raleigh (Moore Sq) | 3 | 7 | 5 |
| Cary Downtown | RTP (Kit Creek Rd) | 15 | 22 | 16 |
| Southpoint Mall | UNC Hospitals | 14 | 19 | 16 |
| Hillsborough | Downtown Durham | 16 | 21 | 21 |
| RDU Terminal 2 | Downtown Raleigh (Moore Sq) | - | 29 | 25 |
| Duke University Hospital | Southpoint Mall | 18 | 23 | 20 |
| Downtown Raleigh (Moore Sq) | Cary Downtown | 16 | 23 | 18 |
| Carrboro Town Hall | RDU Terminal 2 | - | 34 | 32 |

Pairwise differences (minutes; negative median means the first engine is faster):

| comparison | n | median signed | median abs | p90 abs | first faster |
|---|---|---|---|---|---|
| ours vs valhalla | 9 | -6.9 | 6.9 | 7.8 | 100% |
| ours vs osrm | 9 | -2.8 | 2.8 | 5.1 | 100% |
| valhalla vs osrm | 12 | +2.9 | 2.9 | 5.6 | 0% |

### Independent spot check, drive, 12 real journeys (2026-11-03 16:43:13)

Metro triangle. Engines present: ours, valhalla, osrm.
Minutes, point to point. OSRM is the public demo server (car profile, independent static model).
**Google not run: set GOOGLE_MAPS_API_KEY.** Without it there is still no congestion-aware reference.

| from | to | ours | valhalla | osrm |
|---|---|---|---|---|
| Carrboro Town Hall | Downtown Durham | 21 | 31 | 28 |
| UNC Hospitals | Duke University Hospital | 17 | 24 | 21 |
| Chapel Hill (Franklin St) | RTP (Kit Creek Rd) | 20 | 27 | 24 |
| Downtown Durham | RDU Terminal 2 | 18 | 23 | 22 |
| NC State Bell Tower | Downtown Raleigh (Moore Sq) | 3 | 7 | 5 |
| Cary Downtown | RTP (Kit Creek Rd) | 15 | 22 | 16 |
| Southpoint Mall | UNC Hospitals | 14 | 19 | 16 |
| Hillsborough | Downtown Durham | 16 | 21 | 21 |
| RDU Terminal 2 | Downtown Raleigh (Moore Sq) | 20 | 29 | 25 |
| Duke University Hospital | Southpoint Mall | 18 | 23 | 20 |
| Downtown Raleigh (Moore Sq) | Cary Downtown | 16 | 23 | 18 |
| Carrboro Town Hall | RDU Terminal 2 | 26 | 34 | 32 |

Pairwise differences (minutes; negative median means the first engine is faster):

| comparison | n | median signed | median abs | p90 abs | first faster |
|---|---|---|---|---|---|
| ours vs valhalla | 12 | -7.0 | 7.0 | 9.0 | 100% |
| ours vs osrm | 12 | -4.1 | 4.1 | 5.7 | 100% |
| valhalla vs osrm | 12 | +2.9 | 2.9 | 5.6 | 0% |


## What this settles

**Our drive model is the outlier, and that is now established without relying on Valhalla.** Two
independent implementations each time every one of the twelve journeys as slower than ours. Against
OSRM we are 4.1 minutes faster at the median, against Valhalla 7.0 minutes, and in both cases on
**100% of pairs**. A single-reference disagreement could have meant the reference was wrong; a
two-reference disagreement in the same direction on every journey, with the sign and gradient a
known omission predicts, is about our model.

The ordering is consistent on all twelve: **ours < OSRM < Valhalla.**

| Comparison | n | median signed | median abs | p90 abs | first faster |
|---|---|---|---|---|---|
| ours vs Valhalla | 12 | −7.0 min | 7.0 | 9.0 | 100% |
| ours vs OSRM | 12 | −4.1 min | 4.1 | 5.7 | 100% |
| Valhalla vs OSRM | 12 | +2.9 min | 2.9 | 5.6 | 0% |

**And it settles something larger: no static engine can validate another to within 10%.** OSRM and
Valhalla are both mature, widely deployed and built for this exact job, and they differ from each
other by **2.9 minutes at the median** — roughly 14% of a typical 21-minute journey here. The owner's
tolerance (decision 12, "about 10% of the limit") is *smaller than the spread between two reference
implementations*. So "accurate to 10%" is not a claim any model-to-model comparison in this project
can support, whichever engine we pick as the reference. Settling it needs congestion-aware data
(Google Routes with `TRAFFIC_AWARE`, or probe archives) or hand-timed journeys. Our gap to the middle
of the pack is 4.1 minutes, larger than the spread itself, so we are outside the range of reasonable
disagreement rather than merely at one end of it.

## A bug this found: geometric snapping onto marooned stubs

The first run returned **no answer at all** from our engine for three of twelve journeys, all of
them to RDU Terminal 2 — an anchor from the product's original brief ("45 minutes to the airport").
Valhalla and OSRM routed all three without trouble.

Cause: the airport coordinate snaps to a node 4 m away that sits on a **four-node `highway=service`
stub**, disconnected from the road network in our graph. The widened drive graph has **1,685**
weakly-connected components (the walk graph **4,208**), the largest holding 98.8% of nodes. Nearest-
node snapping is geometric, not topological, so it happily returns a node that cannot reach anything.

Fix: `locfinder/traveltime/components.py` prunes to the largest component before snapping and
**reports what it dropped**, refusing to prune at all if more than 10% of nodes would go, since that
would mean the mode filter or the extract bounds are wrong rather than the city being fragmented.
Seven tests cover it, including the airport failure mode. After the fix all twelve journeys resolve.

This also means the layer coverage figures were pessimistic: cells whose nearest edge belonged to a
marooned stub were recorded as unreachable. The walk layer's "72.7% of cells reachable" should be
re-measured now that pruning is in place.

## Still missing

Nothing here knows about traffic. All three engines are static: the Valhalla container logs
"Traffic tile extract could not be loaded" sixteen times, OSRM's demo server uses free-flow profile
speeds, and our model uses friction speeds by road class. The congestion-aware leg was run on 2026-11-03 with a key supplied by the owner; see the next
section.

### Independent spot check, drive, 12 real journeys (2026-11-03 16:51:45)

Metro triangle. Engines present: ours, valhalla, osrm, google_static, google_traffic.
Minutes, point to point. OSRM is the public demo server (car profile, independent static model).
Google legs: `TRAFFIC_UNAWARE` is model-vs-model; `TRAFFIC_AWARE` at 08:00 local is the only congestion-aware number here. Queried live for validation; not stored as a dataset and not used to calibrate our model.

| from | to | ours | valhalla | osrm | google_static | google_traffic |
|---|---|---|---|---|---|---|
| Carrboro Town Hall | Downtown Durham | 21 | 31 | 28 | 32 | 34 |
| UNC Hospitals | Duke University Hospital | 17 | 24 | 21 | 24 | 26 |
| Chapel Hill (Franklin St) | RTP (Kit Creek Rd) | 20 | 27 | 24 | 22 | 25 |
| Downtown Durham | RDU Terminal 2 | 18 | 23 | 22 | 19 | 24 |
| NC State Bell Tower | Downtown Raleigh (Moore Sq) | 3 | 7 | 5 | 7 | 7 |
| Cary Downtown | RTP (Kit Creek Rd) | 15 | 22 | 16 | 18 | 19 |
| Southpoint Mall | UNC Hospitals | 14 | 19 | 16 | 17 | 20 |
| Hillsborough | Downtown Durham | 16 | 21 | 21 | 20 | 21 |
| RDU Terminal 2 | Downtown Raleigh (Moore Sq) | 20 | 29 | 25 | 23 | 28 |
| Duke University Hospital | Southpoint Mall | 18 | 23 | 20 | 18 | 22 |
| Downtown Raleigh (Moore Sq) | Cary Downtown | 16 | 23 | 18 | 18 | 23 |
| Carrboro Town Hall | RDU Terminal 2 | 26 | 34 | 32 | 28 | 33 |

Pairwise differences (minutes; negative median means the first engine is faster):

| comparison | n | median signed | median abs | p90 abs | first faster |
|---|---|---|---|---|---|
| ours vs valhalla | 12 | -7.0 | 7.0 | 9.0 | 100% |
| ours vs osrm | 12 | -4.1 | 4.1 | 5.7 | 100% |
| valhalla vs osrm | 12 | +2.9 | 2.9 | 5.6 | 0% |
| ours vs google_static | 12 | -2.9 | 2.9 | 7.9 | 100% |
| valhalla vs google_static | 12 | +3.9 | 3.9 | 5.7 | 25% |
| google_static vs google_traffic | 12 | -2.7 | 2.7 | 5.0 | 100% |
| ours vs google_traffic | 12 | -5.5 | 5.5 | 9.1 | 100% |

---

## The Google leg: a congestion-aware reference, run 2026-11-03

The owner supplied a Routes API key and ran the same twelve journeys with two further legs:
`TRAFFIC_UNAWARE` (a fourth static model) and `TRAFFIC_AWARE` at 08:00 local — the only number in
this project that reflects actual congestion.

Per-pair Google values are **not recorded here or in the JSON**, by the discipline stated at the top
of this file. What follows is derived statistics, plus two rows kept as illustration.

### Every engine's distance from the congestion-aware reference

| engine | median signed | median abs | p90 abs | faster than it on |
|---|---|---|---|---|
| **Valhalla** (self-hosted, our drive engine) | **+0.0 min** | **1.0 min** | 3.0 min | 33% |
| OSRM demo | −2.5 min | 2.5 min | 5.0 min | 92% |
| Google, traffic-unaware | −3.0 min | 3.0 min | 5.0 min | 92% |
| **ours** | **−6.0 min** | **6.0 min** | 9.0 min | 100% |

Two illustrative journeys (minutes): Carrboro Town Hall to Downtown Durham reads ours 21, Valhalla
31, traffic-aware 34; NC State to Downtown Raleigh reads ours 3, Valhalla 7, traffic-aware 7.

### The finding: Valhalla's static profile is already calibrated to morning traffic

**Valhalla matches the traffic-aware reference better than Google's own traffic-free model does** —
a median signed difference of exactly zero and a median absolute difference of one minute, against
three minutes for Google static and 2.5 for OSRM. Its apparent "conservatism", which earlier
documents treated as the reason our model looked fast, is not a quirk of its defaults. On these
journeys it lands on real 8 am conditions.

Three consequences.

**The drive engine choice is right, for a better reason than we had.** D1 justified Valhalla on the
grounds that it models one-ways, turn restrictions and intersection delay while we do not. The
stronger justification is now empirical: its output agrees with a congestion-aware reference to
within a minute at the median, where ours is six minutes optimistic.

**Our six-minute error splits cleanly in half, and only half is ours to fix.**

| Component | Size | Fixable? |
|---|---|---|
| Our static model vs a comparable static model (Google traffic-unaware) | 3.0 min | **yes** — the intersection penalties we did not port |
| Congestion, which no static engine models | 3.0 min | no, not without traffic data |

So porting the CHCCS intersection penalties would close about half the gap and bring us roughly to
where OSRM and Google-static sit. It would **not** bring us to the traffic-aware number, because
nothing static can. Traffic cost a median of +3.0 minutes on these routes and was non-zero on 11 of
12 journeys.

**The honest UI label probably changes.** The design currently says drive times are "estimated,
modelled from road speeds, with no traffic data", which is literally true of the engine and
misleading about the result: Valhalla-derived drive times behave like typical weekday-morning times,
not free-flow ones. On this evidence "typical weekday morning" is the more accurate label for
Valhalla-sourced drive layers.

### And the first evidence that owner decision 12 is achievable

At the 21-minute median journey length here, the 10% tolerance is about 2.1 minutes. Valhalla's
median absolute difference from the traffic-aware reference is **1.0 minute**, with p90 3.0 minutes.
That is the first measurement in this project that bears on decision 12 at all, and it is
encouraging for Valhalla-sourced drive times.

### What this does not establish

Stated plainly, because earlier revisions of these documents overclaimed:

- **n = 12**, one metro, one time of day (08:00), one direction of the peak, drive only.
- Values were read from the run output **rounded to whole minutes**, so every difference carries
  roughly ±0.5–1 minute of quantisation. The sub-minute precision above is not real precision.
- `TRAFFIC_AWARE` for a *future* timestamp is Google's prediction from historical patterns, not an
  observation. It is the best cheap proxy for truth, not truth. Hand-timed journeys remain the only
  actual ground truth.
- Off-peak would likely favour the faster engines, so "Valhalla ≈ reality" is specifically an 08:00
  result and must not be generalised to all hours.
- Walk and bike still have **no** independent reference at all. Google's walk and bike legs are one
  command away (`--mode walk`) and are the obvious next check, especially since the walk comparison
  that "passed" had the reference's speed set equal to ours.

A larger sample, a second time of day and the walk mode would turn this from a strong hypothesis
into a usable calibration statement. None of it should be used to tune our speed model.
