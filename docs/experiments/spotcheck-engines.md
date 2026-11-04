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

### Independent spot check, drive, 12 real journeys (2026-11-03 17:36:07)

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

---

## Fixed: restricted access is now reachable, and penalised rather than prohibited (2026-11-03)

> Read this section together with the corrections at the end of the file: it originally
> claimed more than the evidence supported, and the cell stage contained a correctness bug
> that Codex pass 6 found and that is now fixed.

The hole found above — a single allow/deny rule that deleted every `access=private` edge and so made
every home on a private drive unreachable — is fixed. The fix is the one mainstream engines use, and
it required a change to the weighting model rather than to the access list alone.

### Why a penalty alone was not enough

The obvious fix, "penalise restricted edges instead of deleting them", breaks the product if the
penalty goes into the weight the Dijkstra reports: a cell on a private driveway would then be shown
as 7.5 minutes further from the shops than it is. Routers avoid this by carrying **two weights** —
a cost for choosing paths and a time for reporting them — and that is now what we do:

| Weight | Used for | Restricted edges |
|---|---|---|
| `cost` | path selection | real time **+ penalty** (drive 450 s, walk/bike 120 s; priors, from Valhalla's documented default) |
| `travel_time` | what a user is shown | real time, **never penalised** |

`csr.graph_to_cost_time_csr` builds both matrices over identical sparsity, taking the cost-minimal
edge and carrying *its* time, so the reported figure always belongs to the path actually chosen.
`arrival.arrival_seconds_two_weight` runs the search on cost with scipy's predecessor tree, then
reconstructs real time by sweeping the tree in increasing-cost order. The cutoff is applied to the
reconstructed time, not to cost, so a penalised path inside the time budget is not discarded.

Access classification moved to `locfinder/traveltime/access.py` and is three-valued:

| Class | Values | Treatment | Edges in the Triangle extract |
|---|---|---|---|
| open | everything else | normal | 1,291,042 |
| restricted | `private`, `customers`, `delivery`, `permit`, `agricultural`, `forestry` | kept, cost penalty | **126,157** |
| forbidden | `no`, `military` | removed | 1,278 |

Mode-specific tags override the generic one, as OSM intends: `access=private` with `foot=yes` is
open to walkers and restricted to drivers.

### Measured effect

| | Before (restricted deleted) | After (restricted penalised) |
|---|---|---|
| Walk graph | 504,457 nodes / 1,321,416 edges | **539,814 / 1,424,670** |
| Cells with a travel time | 72.7% | **77.3%** |
| Twelve-journey spot check vs Valhalla and OSRM | — | **identical on all twelve** |
| Reported times inflated by the penalty | — | none detectable |
| Dijkstra | 0.07 s | 3.89 s (the tree reconstruction) |

**Coverage rose 4.6 percentage points, about 15,200 of 330,502 cells** that previously had no answer
at all. The composition of that gain is measured in the corrections below and is **not** what this
section first claimed: only 4,662 reachable cells have a restricted edge as their nearest edge, so
most of the gain is cells reachable *through* restricted roads rather than homes *on* them.

**The twelve open-road journeys were unchanged**, byte-identical. That is a useful regression
control — restricted-access handling should not touch routes between well-connected named places —
but it is not a positive test of the fix, because no journey in that set exercises restricted
access. A journey that does is still missing from the set.

**Penalty leak: the original test was inadequate** and has been replaced; see the corrections at
the end of this file. A leak shows up as a per-cell offset, which the histogram it used could not
have detected.

### What this cost and what it did not fix

The tree reconstruction adds about 3.8 s per layer, a Python sweep over half a million nodes. Total
layer build is 91 s including a 35 s graph load, so the marginal cost per category is unchanged in
practice and the two-weight machinery is now available for the *other* thing our drive model lacks:
intersection penalties fit the same cost channel without touching reported time.

Still not fixed, and still the reason Valhalla owns the drive path: turn restrictions, which a
node-state graph cannot express at all. Pruning now drops 13,608 nodes (2.5%); the component counts
quoted in an earlier draft compared drive to walk and were withdrawn.

Twenty-eight new tests cover the classification and the two-weight behaviour, including that a
private shortcut is rejected when an open detour is cheaper, taken when it is the only way, that the
reported time is the chosen path's real time in both cases, and that the one-way regression from
Codex pass 1 still holds on the two-weight path.

## Corrections after Codex pass 6

`../research/13-codex-adversarial-review-pass6-access.md` reviewed the section above and found a
**real correctness bug in the cell stage**, plus three claims that were not supported. The node-level
two-weight reconstruction survived review, with 2,940 randomized predecessor-chain checks agreeing.

### Fixed: the cell layer contradicted the node layer

`cell_seconds_from_arrival` chose its branch by **time** while the node search chose by **cost**, so
a cell could take a penalised shortcut the search had deliberately rejected. Codex's executed
counterexample: with a fast private link and an open alternative, node reconstruction correctly gave
**200 s** at a node while snapping returned **20 s at the very same point**.

The fix carries node costs and per-direction edge costs into the cell stage, selects the branch on
cost, and reports that branch's time. `EdgeIndex` now holds `fwd_cost`/`rev_cost` and reduces
parallel edges by cost (carrying the chosen edge's own time), matching `graph_to_cost_time_csr` so
the two stages cannot disagree about which edge a path uses.

A second bug in the same area: the cutoff was applied only to node times, so a cell could exceed the
advertised budget once its off-network access leg was added. It is now applied once, to the final
time.

Writing the test for this taught me something I had wrong too. I first asserted that a cell anywhere
on a private edge should prefer the open route. That is false: a cell *on* the edge must use part of
it regardless, so past a crossover it is genuinely correct to continue to the far end. With this
fixture the crossover is at 29% along the edge, and the test now encodes that rather than my
mistaken expectation. The bug was specifically at the **exact node**, where the open road is
available without touching the private edge at all.

### Fixed: `access=destination` was unpenalised

It was classified open with zero penalty, which made an explicit "no through traffic" road behave
like an ordinary shortcut — the clearest possible case for a penalty, and I had written a test
asserting the mistake. It is now restricted. 550 edges in the extract carry it.

### Fixed: mode-tag precedence and list aggregation

`motor_vehicle` was consulted before `motorcar`, so `motor_vehicle=no` with `motorcar=yes` read as
forbidden despite the narrower allowance. The order is now narrowest-first
(`motorcar` → `motor_vehicle` → `vehicle` → `access`), and `vehicle` is handled at all. Separately,
specific and generic tags aggregated differently: `foot=[yes, private]` came out open while
`access=[yes, private]` came out restricted. Both are now restricted, with the strictest value in
any one tag winning.

### Withdrawn: "not a through-route"

A finite penalty **discourages** through traffic; it does not prohibit it. With the drive penalty at
450 s, a 60-second private cut-through beats a 600-second open detour and is selected. The honest
description is "penalised, not prohibited", and the section heading above should be read that way.

Two consequences worth stating plainly. The penalty is charged **per simplified edge**, so splitting
one physical private link into two doubles its penalty without any physical change — an artifact of
per-edge rather than per-entry charging. And permission depends on the traveller: reaching your own
driveway is not the same right as cutting through someone else's estate, and a single scalar penalty
cannot express that difference.

### Withdrawn: "those are overwhelmingly homes on driveways"

Asserted, not measured, and the measurement does not support it. Of 272,961 reachable cells, only
**4,662** have a restricted edge as their nearest edge (4,424 `private`, 236 `customers`, 1
`forestry` — so the "agricultural tracks" worry is empirically nil). That is far short of the
~15,200-cell coverage gain, which means **most of the gain is cells nearest an open edge that became
reachable because restricted edges reconnected the network** — reachable *through* private roads,
not homes *on* them. That is a legitimate routing mechanism and it is not the story I told. Whether
those routes are ones a person may lawfully drive is exactly the question the per-edge penalty cannot
answer.

Also withdrawn: the before/after component comparison, which compared **1,685 drive** components to
**3,046 walk** components. Those are different modes and not a controlled comparison.

### Replaced: the penalty-leak test

The original check looked for a histogram spike at the penalty value. A leak would appear as a
per-cell offset, which a histogram cannot see, so that test could not have failed. The replacement
brackets the reported value between two independently computed bounds, time-only Dijkstra below and
cost-based Dijkstra above, and then — this part matters — restricts the leak check to the nodes where
cost and time actually differ. On the ~88% of nodes untouched by a restricted edge all three
computations coincide by arithmetic, and my first verdict logic mistook that for a leak and reported
a false FAIL.

### Penalty sensitivity, measured — **superseded 2026-11-04, see the re-run at the end of this file**

> The coverage and median columns below are **not the product's**: this run called
> `cell_seconds_from_arrival` without `node_cost` or the final `cutoff_s` (Codex pass-7 M2), so it
> measured a pipeline we do not ship. Phase 1 S2.5 re-ran it through the production path. The
> replacement numbers are at the end of this file; the diverted-node counts also changed because
> this earliest run predates a graph rebuild. **Quote the re-run, not this.**

| penalty (s) | cells with a time | median reported | nodes whose path the penalty diverted |
|---|---|---|---|
| 0 | ~~77.35%~~ | ~~34.4 min~~ | 0 |
| 60 | ~~77.35%~~ | ~~34.4 min~~ | 40,197 |
| **120 (adopted)** | ~~77.32%~~ | ~~34.4 min~~ | 46,613 |
| 240 | ~~77.27%~~ | ~~34.4 min~~ | 49,063 |
| 960 | ~~77.25%~~ | ~~34.6 min~~ | 52,868 |

**Coverage is almost completely insensitive to the penalty** — 0.1 points across a 16× range —
because a finite penalty never removes reachability, only changes which path is chosen. So the
coverage gain comes from *admitting* restricted edges at all, not from the magnitude, and the
magnitude is a route-choice knob affecting 8–10% of nodes. **That conclusion survives the re-run**
(0.10 points across the same range), which is why it is left standing here. The 450/120 s values
remain **priors** from Valhalla's documented default, not measurements.

### Still open

- Whether the recovered cells are residential and lawfully reachable. Codex is right that no
  defensible spurious-rate estimate exists, and that assigning a percentage now would repeat the
  error. It needs a paired audit with a preserved before-array, legal entrances and transition
  counts in both directions.
- Per-entry rather than per-edge penalty charging, which would remove the segmentation artifact.
- Physical intersection delay, if we ever add it, belongs in **time as well as cost**: only a
  preference belongs to cost alone. The current machinery would put it in the wrong place.
- The reconstruction's O(R log R) sort plus R Python sparse lookups could be an O(V+E) dependency
  walk with aligned CSR indices.

### Withdrawn: two FAIL verdicts on the penalty leak, both from the test, not the code

Two runs of `spikes/verify_two_weight.py` appended a **"Verdict: FAIL — the penalty is leaking into
reported time"** to this file, at 17:45 and 18:01 on 2026-11-03. **Both are withdrawn. Neither was
evidence of a leak**, and the second was committed, so this is a correction to the record and not
just to a draft.

The first verdict counted every node where `reported == cost-based` as a leak. That is arithmetic on
roughly 88% of the network: wherever no restricted edge is involved, cost and time are the same
number and all three computations coincide by construction.

The second verdict restricted the count to the 119,537 nodes where cost and time genuinely differ,
which sounds like the fix and is not. **`reported == cost-based` is still not a leak signature.** It
means the cost-optimal path carries no penalised edge, so that path's time equals its cost
necessarily — which is the penalty having *successfully* diverted the route onto an open road. The
43.08% that run reported as leaking is the share of penalty-affected nodes that ended up on a clean
path, which is the outcome we want.

The demonstration is Codex's own pass-6 H1 fixture, which `tests/test_cost_aware_snapping.py`
independently certifies: at node S the open road is chosen, `time-only = 20`, `reported = 200` and
`cost-based = 200`. The rule flags S as a leak while the suite asserts 200 is correct.

**The valid test is the exact identity.** Accumulating the penalty over the same cost-optimal forest
must reconcile the two bounds edge for edge:

    cost-based  ==  reported time  +  penalty accumulated on that path

A genuine leak breaks it, because the report would equal the upper bound while the accumulated
penalty is non-zero. That identity shares the reconstruction's arithmetic, so it cannot detect a
wrong *path*; an independent predecessor walk that re-sums `travel_time` and `cost` from the graph
itself covers that. Both are now in the script, and
`tests/test_two_weight.py::test_penalty_identity_is_the_valid_leak_test_not_equality_with_cost`
guards the verdict rule so this cannot regress a third time.

The bracket test itself was sound and passed in both runs: **zero** violations of
`time-only <= reported <= cost-based` on 539,814 nodes. A bracket alone cannot detect a leak, which
is what both verdicts got wrong; it bounds the error without localising it.


### Two-weight verification on the real network (2026-11-03 18:14:42): walk / grocery

539,814 nodes, 417 destinations, 539,814 nodes finite in all three computations.

**Bracket test.** The reported value must satisfy `time-only <= reported <= cost-based`; a penalty leak makes the upper bound tight everywhere.

| check | nodes | share of finite |
|---|---|---|
| reported **below** the time-only lower bound (must be 0) | **0** | 0.0000% |
| reported **above** the cost-based upper bound (must be 0) | **0** | 0.0000% |
| reported **equals** the time-only bound (no penalty in effect) | 471,928 | 87.42% |
| reported equals the cost-based value **overall** (expected where cost==time) | 471,776 | 87.40% |
| reported **above** time-only, i.e. the penalty diverted the path | 68,023 | 12.60% |

Of the **119,537** nodes the penalty actually affected, both outcomes below are correct; the split is descriptive, not a verdict. `reported == cost-based` means the chosen path carries no penalised edge, so its time equals its cost necessarily:

| outcome | nodes | share of those |
|---|---|---|
| diverted onto a penalty-free path (reported == cost-based) | 51,499 | 43.08% |
| still uses a penalised edge, penalty stripped from the report | 68,038 | 56.92% |

**The decisive test is the exact identity.** Accumulating the penalty over the same cost-optimal forest must reconcile the two bounds edge for edge: `cost-based == reported time + penalty accumulated on that path`. A leak breaks it, because the report would equal the upper bound while the accumulated penalty is non-zero.

| check | value |
|---|---|
| nodes tested | 539,814 |
| of those, carrying a non-zero accumulated penalty | 68,038 (12.60%) |
| identity violations above 1 ms (must be 0) | **0** |
| largest residual | 3.64e-12 s |

**Verdict: PASS.** The reported times sit inside the bracket and the penalty identity holds exactly on every node, so the reported figure is the real travel time along the cost-optimal path and the penalty is not leaking into it.

**Independent path walk.** The identity shares the reconstruction's arithmetic, so it cannot detect a wrong path. This re-sums `travel_time` and `cost` from the graph along the explicit predecessor chain, for a random sample of nodes whose path carries a penalty.

| check | value |
|---|---|
| nodes walked (of 68,038 eligible) | 500 |
| total hops re-summed | 36,802 |
| reported time != re-summed graph time (must be 0) | **0** |
| accumulated penalty != re-summed graph penalty (must be 0) | **0** |

**Penalty sensitivity.** Same graph and destinations, penalty varied. The adopted value is 120 s.

> **Superseded 2026-11-04 by the re-run at the end of this file. Do not quote this coverage
> column.** Codex pass 7 (M2) found that the sweep called `cell_seconds_from_arrival` without
> `node_cost` or the final `cutoff_s`, so it measured a pipeline we do not ship -- which is exactly
> why its coverage reads 77.3% where the production rebuild of the same layer reads **76.8%**. The
> script was then changed to call the production path; this run predates that change. Phase 1 S2.5
> re-ran it, and the comparison is instructive: the **diverted-node counts are identical** between
> this run and the re-run (0 / 42,849 / 49,363 / 51,843 / 55,694), because those come from the
> node-level search, which the omission did not touch -- while every coverage and median figure
> moved, because those come from the cell stage, which it did.

| penalty s | cells with a time | median reported min | nodes diverted by the penalty |
|---|---|---|---|
| 0 | 77.35% | 34.4 | 0 |
| 60 | 77.35% | 34.4 | 42,849 |
| 120 | 77.32% | 34.4 | 49,363 |
| 240 | 77.27% | 34.5 | 51,843 |
| 960 | 77.25% | 34.7 | 55,694 |

**Provenance of reachable cells whose nearest edge is restricted** (by that edge's `access` value; a length-keyed approximation, so read it as indicative):

| access value | reachable cells snapped to it |
|---|---|
| private | 4,424 |
| customers | 236 |
| destination | 11 |
| forestry | 1 |
| None | 1 |

Total reachable cells nearest a restricted edge: 4,673 of 272,961 reachable.

### Two-weight verification on the real network (2026-11-04 11:38:26): walk / grocery

539,814 nodes, 417 destinations, 539,814 nodes finite in all three computations.

**Bracket test.** The reported value must satisfy `time-only <= reported <= cost-based`; a penalty leak makes the upper bound tight everywhere.

| check | nodes | share of finite |
|---|---|---|
| reported **below** the time-only lower bound (must be 0) | **0** | 0.0000% |
| reported **above** the cost-based upper bound (must be 0) | **0** | 0.0000% |
| reported **equals** the time-only bound (no penalty in effect) | 471,928 | 87.42% |
| reported equals the cost-based value **overall** (expected where cost==time) | 471,776 | 87.40% |
| reported **above** time-only, i.e. the penalty diverted the path | 68,023 | 12.60% |

Of the **119,537** nodes the penalty actually affected, both outcomes below are correct; the split is descriptive, not a verdict. `reported == cost-based` means the chosen path carries no penalised edge, so its time equals its cost necessarily:

| outcome | nodes | share of those |
|---|---|---|
| diverted onto a penalty-free path (reported == cost-based) | 51,499 | 43.08% |
| still uses a penalised edge, penalty stripped from the report | 68,038 | 56.92% |

**The decisive test is the exact identity.** Accumulating the penalty over the same cost-optimal forest must reconcile the two bounds edge for edge: `cost-based == reported time + penalty accumulated on that path`. A leak breaks it, because the report would equal the upper bound while the accumulated penalty is non-zero.

| check | value |
|---|---|
| nodes tested | 539,814 |
| of those, carrying a non-zero accumulated penalty | 68,038 (12.60%) |
| identity violations above 1 ms (must be 0) | **0** |
| largest residual | 3.64e-12 s |

**Verdict: PASS.** The reported times sit inside the bracket and the penalty identity holds exactly on every node, so the reported figure is the real travel time along the cost-optimal path and the penalty is not leaking into it.

**Independent path walk.** The identity shares the reconstruction's arithmetic, so it cannot detect a wrong path. This re-sums `travel_time` and `cost` from the graph along the explicit predecessor chain, for a random sample of nodes whose path carries a penalty.

| check | value |
|---|---|
| nodes walked (of 68,038 eligible) | 500 |
| total hops re-summed | 36,802 |
| reported time != re-summed graph time (must be 0) | **0** |
| accumulated penalty != re-summed graph penalty (must be 0) | **0** |

**Penalty sensitivity.** Same graph and destinations, penalty varied. The adopted value is 120 s.

| penalty s | cells with a time | median reported min | nodes diverted by the penalty |
|---|---|---|---|
| 0 | 76.77% | 34.1 | 0 |
| 60 | 76.77% | 34.1 | 42,849 |
| 120 | 76.76% | 34.2 | 49,363 |
| 240 | 76.71% | 34.2 | 51,843 |
| 960 | 76.67% | 34.4 | 55,694 |

**Provenance of reachable cells whose nearest edge is restricted** (by that edge's `access` value; a length-keyed approximation, so read it as indicative):

| access value | reachable cells snapped to it |
|---|---|
| private | 4,125 |
| customers | 230 |
| destination | 10 |
| forestry | 1 |
| None | 1 |

Total reachable cells nearest a restricted edge: 4,367 of 253,679 reachable.

#### S2.5: what the re-run settles

This is the production-path run that supersedes both tables above (Phase 1 S2.5). Three things come
out of it.

**The supersession is confirmed.** Coverage at the adopted 120 s penalty is **76.76%**, against the
superseded 77.32%, and it matches the independently rebuilt production layer's **76.7557%**. The
medians also fell by about 0.3 min. The diverted-node counts are unchanged from the previous run,
which localises the defect exactly: it was in the cell stage, not the node search.

**The unvalidated prior turns out not to matter much for what we publish.** Across a 16× range of
penalty — 0 s to 960 s — coverage moves 76.77% → 76.67% (0.10 points) and the median reported time
moves 34.1 → 34.4 minutes, while the number of nodes whose chosen path changes goes from 0 to
**55,694**. So the penalty is almost entirely a *route-choice* knob: it changes which way the search
goes for about 10% of nodes while barely moving the number a household is shown. `access.py` flags
450/120 s as priors rather than measurements, and this bounds how much that matters — for the
own-graph **walk** layer. It says nothing about drive, which uses Valhalla's own penalties, and
nothing about whether either value is *right*.

**The access fix is worth about 1.7% of reachable cells.** 4,367 of 253,679 reachable cells have a
restricted edge as their nearest, 4,125 of them `access=private` — driveways, which is where people
live. That is the population a blanket block would have removed, and it is a bounded number rather
than the "every home on a private drive" framing used earlier.
