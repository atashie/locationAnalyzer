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
speeds, and our model uses friction speeds by road class. The congestion-aware leg needs
`GOOGLE_MAPS_API_KEY` set, after which the same script adds two columns per journey —
`TRAFFIC_UNAWARE` for a fourth model-to-model reading and `TRAFFIC_AWARE` at 08:00 local, which is
the only number in this project that would reflect a real commute.
