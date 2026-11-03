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

| from | to | ours | valhalla | osrm |
|---|---|---|---|---|

> The two Google columns that the generator wrote here have been removed: keeping a complete
> per-pair table of Google values in the repository contradicts this file's own stated
> discipline. Codex pass 5 (H5) caught it. Aggregates and two illustrative rows are kept
> below; the generator no longer writes Google columns to a results file.

Pairwise differences (minutes; negative median means the first engine is faster):

| comparison | n | median signed | median abs | p90 abs | first faster |
|---|---|---|---|---|---|
| ours vs valhalla | 12 | -7.0 | 7.0 | 9.0 | 100% |
| ours vs osrm | 12 | -4.1 | 4.1 | 5.7 | 100% |
| valhalla vs osrm | 12 | +2.9 | 2.9 | 5.6 | 0% |
| from | to | ours | valhalla | osrm |
|---|---|---|---|---|

> The two Google columns that the generator wrote here have been removed: keeping a complete
> per-pair table of Google values in the repository contradicts this file's own stated
> discipline. Codex pass 5 (H5) caught it. Aggregates and two illustrative rows are kept
> below; the generator no longer writes Google columns to a results file.
| from | to | ours | valhalla | osrm |
|---|---|---|---|---|

> The two Google columns that the generator wrote here have been removed: keeping a complete
> per-pair table of Google values in the repository contradicts this file's own stated
> discipline. Codex pass 5 (H5) caught it. Aggregates and two illustrative rows are kept
> below; the generator no longer writes Google columns to a results file.
| from | to | ours | valhalla | osrm |
|---|---|---|---|---|

> The two Google columns that the generator wrote here have been removed: keeping a complete
> per-pair table of Google values in the repository contradicts this file's own stated
> discipline. Codex pass 5 (H5) caught it. Aggregates and two illustrative rows are kept
> below; the generator no longer writes Google columns to a results file.
| from | to | ours | valhalla | osrm |
|---|---|---|---|---|

> The two Google columns that the generator wrote here have been removed: keeping a complete
> per-pair table of Google values in the repository contradicts this file's own stated
> discipline. Codex pass 5 (H5) caught it. Aggregates and two illustrative rows are kept
> below; the generator no longer writes Google columns to a results file.

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

---

## Walking was never independently checked, even by accident

Measured 2026-11-03, prompted by the question of what our references actually are. Five journeys of
1.9 to 17.8 km were timed with Valhalla's **default** pedestrian costing, with no `costing_options`
of ours applied, and the implied speed was recovered from the returned length and duration:

| Journey length | Implied speed |
|---|---|
| 1.86 km | 1.407 m/s |
| 2.49 km | 1.400 m/s |
| 12.55 km | 1.411 m/s |
| 12.99 km | 1.414 m/s |
| 17.79 km | 1.414 m/s |
| **median** | **1.411 m/s = 5.08 km/h** |

Our own assumption is **1.400 m/s = 5.04 km/h**. The two differ by **0.8%**.

Two things follow, and both weaken the walk result reported in `g1-routing.md`.

**The explicit speed-matching was beside the point.** Earlier documents noted that we had set
Valhalla's `walking_speed` to 5.04 km/h, making the walk comparison circular. It turns out the
comparison would have been nearly circular anyway: Valhalla's default is 5.08 km/h. There was never
a version of this test that could have detected a wrong walking speed, because both engines
independently chose essentially the same number for an adult on level ground.

**For walking, the two engines are barely two models.** The implied speed is almost constant across
a tenfold range of journey length (1.400 to 1.414 m/s), which means Valhalla's pedestrian costing
adds essentially no delay for crossings, signals or turns — it is distance over a constant speed,
which is also what ours is. So the walk comparison tested the **network layer** (graph construction,
access filtering, snapping, within-edge interpolation) and that layer agreed to within 2–3% at the
median, which is a genuine and useful result. It tested the **timing model** not at all.

The risk this leaves is shared, not relative: if 5.05 km/h overstates how fast people actually get
from door to door on foot — and real walking includes waiting at crossings, gradients, and not
walking at a brisk clip — then our layers and Valhalla's are wrong *together* by the same amount and
no comparison between them will ever reveal it. Driving had an independent, congestion-aware
reference available for twenty dollars of free tier; walking has had none at all.

**The cheap fix is the same script with `--mode walk` and a Google key**, which adds a genuinely
independent pedestrian model, and then a handful of hand-timed walks, which is the only way to learn
whether either model describes a person. Until one of those happens, no claim about walk-time
accuracy in this project rests on anything but two engines agreeing because they share an
assumption.

---

## Corrections after Codex pass 5

`../research/12-codex-adversarial-review-pass5-spotcheck.md` audited the arithmetic above and the
conclusions drawn from it. The arithmetic reproduces. Several conclusions do not, and are withdrawn
here rather than left standing above.

### Withdrawn: "our six-minute error splits cleanly in half"

Not supported. The per-journey identity holds exactly, but **medians do not preserve it**: the
unrounded summaries give 2.9 + 2.7 = 5.6 against a total of 5.5, so the clean split is an artefact
of whole-minute rounding. Per journey the share attributed to the static gap ranges from 0% to
100%, and only one of the twelve splits evenly. Nor does a comparison against Google-static
*identify* intersection penalties: the two models differ in speeds, topology, turn restrictions,
snapping and route choice simultaneously, and the two Google legs may follow different paths, so
their difference is not a fixed-route congestion measurement either.

The claim that nothing static can close the traffic gap is also too absolute, and the Valhalla
result in this very file is the counterexample: a static profile *can* encode typical delay. What
remains is a hypothesis worth testing by **ablation on our own graph** — add the CHCCS intersection
penalties, change nothing else, and re-measure — not by attributing minutes to causes we did not
control.

### Withdrawn: "the first evidence that owner decision 12 is achievable"

Not supported, because the denominator was wrong. Decision 12 is about **the threshold a user
sets**, with median ≤ 10% of T and p90 ≤ 20% of T evaluated on cells *near that boundary*. No
threshold was assigned to these twelve journeys. The "21-minute median journey" is OSRM's median,
not the reference's (23.5). At T=10 the budgets are 1.0 and 2.0 minutes and the pooled p90 of 3.0
already exceeds the second — which does not prove a ten-minute boundary fails, since nothing was
sampled there, but does prevent claiming it passes.

Engine agreement is also only one term in the final error. Expansion reconstruction, cell access
legs, destination entrances, grid resolution and minute encoding all contribute, and their medians
cannot simply be added. Decision 12 remains untested.

### Withdrawn: the label "typical weekday morning"

Not supported by one predicted Tuesday at one hour. The defensible label now is Codex's:

> **"Estimated drive time from a static road model; traffic and departure time are not included."**

The observation that Valhalla's static output sat closest to an 08:00 forecast belongs in research
notes, not in a promise to users. Adopting the morning label would fix one error and create another:
an off-peak errand would look further away than it is, and this sample cannot quantify by how much.

### Qualified: what the spot check measured

Two methodological gaps, both of which flatter our engine:

- **Our point-to-point path is not the product's path.** `ours_point_to_point` snaps both endpoints
  to nearest **nodes** with no distance bound and no access-leg charge, while the layer pipeline
  snaps to nearest **edges**, adds a modal access leg and caps it at 200 m. The comparison therefore
  gave our engine a free endpoint advantage it does not have in production.
- **Named anchors are not residential cells.** Hospitals, town centres and an airport sit on
  well-connected major roads. The product computes from residential cell centres, including
  cul-de-sacs, gated access, coordinates off-network and locations behind barriers. Twelve pairs, one
  direction each, one timestamp, no journey under three or over thirty-five minutes.

Also uncontrolled: the OSRM demo server's profile, customisation and data vintage were never
captured, so calling its speeds "free-flow" exceeds the record, and all three of our engines share
OSM ancestry, so implementation diversity is not independence of input data.

### Qualified: the component fix

Pruning to the largest **weakly** connected component addresses the demonstrated airport mechanism
but is a policy choice, not a general reachability repair. Weak connectivity ignores edge direction,
so a retained one-way branch can still fail origin-to-anchor reachability; keeping only the largest
*strongly* connected component is not a universal fix either, since it would discard legitimate
one-way approaches. Separate valid networks — islands, campuses, local path networks — can support
real journeys, and a small share of nodes may contain a household's entire neighbourhood, so the
10% guard is a **useful alarm, not a correctness bound**.

The claim that layer coverage was "pessimistic and should improve" is withdrawn pending measurement:
after pruning, a formerly stub-snapped cell may find a reachable road, or may now exceed the 200 m
access cap, or may reach it only by crossing a barrier in a straight line. Coverage need not move
monotonically, and an increase would not by itself establish correctness. The honest next step is to
publish the finite-to-missing and missing-to-finite transition counts with snap displacement.

Finally, `test_the_airport_failure_mode_is_what_this_prevents` asserts only that a synthetic node
disappears. It exercises a necessary mechanism, not the real failure-and-recovery chain: it never
snaps an airport coordinate, routes, bounds displacement or checks access legality.

---

## Follow-up: the airport stub was not an OpenStreetMap gap, and what it did reveal

Checked 2026-11-03, prompted by asking whether the RDU failure was a data defect we could fix
upstream. It was not.

In the **raw** extract, before any mode filter, the airport node sits in the single 551,375-node
component — the whole graph. After our drive filter it sits in a 4-node stub. So the fragmentation
is ours, not OSM's. But the filter is not wrong either: **every way leading out of that stub is
tagged `access=no`**, which genuinely means closed to the public. The coordinate I picked for "RDU
Terminal 2" lands on an interior service area reachable only through those ways.

Three conclusions, in increasing order of importance.

**The pruning fix was the right remedy** for the symptom, and `components.py` stays as it is.

**The real defect is anchor routability, and it is a product requirement.** A user who types "RDU
Airport" must be geocoded to a *routable* point, not to whichever node happens to be nearest.
Valhalla answered all three airport journeys without trouble because it snaps to its own routable
network with a tolerance. Our pipeline must do the same: after geocoding an anchor, verify it can
reach the network and otherwise nudge it to the nearest point that can, surfacing the adjustment
rather than silently returning "unreachable". This belongs in the Phase 1 anchor path.

**And the diagnostic found a systematic coverage hole that matters for a home-search product.**
Across the Triangle extract, `access=private` appears on **118,035 edges** and `access=customers` on
**8,003**, and our filter blocks both outright for driving. That is correct for *through* traffic and
wrong for *reaching a destination*: a house at the end of a private drive is still a house someone
drives to. Mainstream routers draw that distinction — Valhalla penalises private access rather than
forbidding it, so it will still use a private driveway to reach an endpoint. We implemented a single
boolean and so would make every home on a private drive unreachable.

This is one more reason the per-mode decision (D1) landed where it did, and it is the first thing to
fix if our own engine is ever revived for driving: access must distinguish through-routing from
start/end access, not be a single allow/deny.

### Candidate contributions back to OpenStreetMap

From comparisons already run, with the import constraint above firmly in mind:

- **Scroggs Elementary** was the one school of eleven that OSM missed where Overture had it (the
  NCES recall check in `g6-poi-coverage.md`). NCES EDGE is public-domain US federal data, so it is a
  plausible source, but any addition must follow OSM's import guidelines and ideally be confirmed on
  the ground rather than bulk-loaded.
- OSM is clearly **stronger** than Overture on playgrounds (515 vs 22) and transit stops (2,462 vs
  51), so there is nothing to give back there.
- The park disagreement (OSM 545, Overture 363, only 63 agreeing within 50 m) is unresolved in both
  directions and would need the manual audit before anyone could say which source is wrong.
