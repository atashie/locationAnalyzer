# A walked journey took 25 minutes where the model said 13.5, down a private track

**2026-11-10.** The first finding produced by the walked audit, and it came from the owner, not from
the instrument. **Revision 2**, after Codex pass 34 corrected six claims in revision 1 — including
the central framing. See [[35-codex-review-pass34]].

## What the owner reported

> "some of the longer walks are projected to be a bit faster than in reality: e.g.
> band15min_pass-03 is closer to 25 mins of walking (1.3 miles with a few intersections; check to
> see if the location snapped to dogwood dr or to edwards st or merrit mill rd, the latter two of
> which would give artificially short travel times)"

Published: **810.8 s = 13.5 min**. Observed: **~25 min, 1.3 miles**.

## The model's journey, decomposed

| part | time | model distance |
|---|---|---|
| access leg at 1.26 m/s | 28.1508 s | 35.4700 m |
| network at 1.40 m/s | 782.6677 s | 1,095.7348 m |
| **total** | **810.8186 s** | **1,131.2049 m = 0.703 mi** |

**That is 54.1% of the owner's 1.3 miles.** The honest statement of this is *"the model represents a
substantially shorter journey than the owner described"* — not "the route is half the real
distance", which revision 1 said. The two numbers are lengths of **potentially different
journeys**, and nothing here rules out intersection delay or a pace difference on its own.

What does rule the speed parameter out is the owner's own arithmetic: **1.3 miles in 25 minutes is
1.39 m/s against our 1.40 m/s.** Their pace matches the model. That comes from the observation, not
from me.

## What it snapped to

Not Dogwood Dr, Edwards St or Merritt Mill Rd. It snapped to **OSM way 430448289**, an unnamed
`track`, 35.5 m from the cell centre — and **19** graph edges qualify within 120 m of that centre,
of which the nearest 14 are all `track`, `path`, `footway` or `service`. (Revision 1 said "every one
of the 14", which was my tool's print limit read as the population, and named way 1254722642, which
is the *next* full segment rather than the matched one.)

The track-and-path approach is **305.44 m** including the 7.56 m partial first edge, after which the
route reaches Raintree Lane, Locust Court and 573 m of South Merritt Mill Road. The owner's instinct
about Merritt Mill was right: that stretch is real and it is most of the distance. The short answer
comes from the approach.

Distance from the cell centre to the nearest edge of each class — the reason there is no good
option:

| class | distance |
|---|---|
| `track` | 35.5 m |
| `footway` | 46.0 m |
| `service` | 57.4 m |
| `path` | 70.4 m |
| `residential` | **142.8 m** |
| `tertiary` | **287.5 m** |

## The cause: a private track, penalised, and the penalty is too small

OSM way **1254722641**, carrying 298 m of the approach, is tagged **`access=private`**. The whole
chain, established rather than inferred:

1. `classify_access` labels it **`restricted`** — correctly.
2. `add_travel_times` applies the penalty: `cost = travel_time + RESTRICTED_PENALTY_S["walk"]`,
   which is **120 s**.
3. **120 s over the ~4 restricted edges is 480 s of cost, and the detour it must beat is 968 s**
   (782.7 s via the track against 1,750.4 s on public roads).
4. So the private track still wins on cost — and because *selection is by cost, reporting is by
   time*, the household is shown **782.7 s**: the real time of a walk down a private track.

**This is a calibration finding, not a missing-mechanism one.** 120 s buys 168 m of tolerated detour
at 1.40 m/s — less than one block. Revision 1 framed the whole thing as an OSM highway-class
problem and offered "penalise rather than exclude" as a future option; the penalty is already there,
already firing on this edge, and simply too small.

`v2/scripts/measure_restricted_walk_policy.py` measures what a bigger one costs. There are 126,197
restricted walk edges.

| variant | the walked cell | lost PASS buildings, *T*=10 | *T*=15 | *T*=25 | *T*=45 |
|---|---|---|---|---|---|
| as published, 120 s | 13.5 min, **PASS** | — | — | — | — |
| penalty 600 s | 31.5 min, FAIL | 1,423 (1.78%) | 1,803 (**1.10%**) | 1,709 (0.57%) | 541 (0.13%) |
| penalty 1800 s | 31.5 min, FAIL | 2,223 (2.78%) | 3,308 (2.02%) | 4,091 (1.37%) | 1,729 (0.41%) |
| restricted removed | 29.8 min, FAIL | 1,003 (1.25%) | 1,333 (0.81%) | 1,528 (0.51%) | 1,547 (0.36%) |
| **observed** | **~25 min** | | | | |

**600 s fixes the walked cell and costs 1.10% of 15-minute PASS buildings.** 1800 s costs roughly
double and does not change this cell further, so 600 s already captures the effect here. UNKNOWN
cells barely move at 600 s: 73,750 → 73,968.

> **One result in that table is not explained.** Removing restricted edges entirely loses *fewer*
> 15-minute PASS buildings (0.81%) than penalising them at 600 s (1.10%), which is backwards for a
> limit case. A plausible mechanism is that `symmetrise` runs after `add_travel_times`, so the
> removal variant symmetrises a different graph than the penalty variants do — but that is a
> hypothesis, not a verified explanation, and it is recorded unverified rather than asserted. I
> made the opposite mistake earlier the same day with the staleness monotonicity claim.

## Removing highway classes measures tag sensitivity, not usability

Revision 1 presented a `{track, path}` exclusion as measuring dependence on "ways whose existence on
the ground is unverified". **It does not.** Highway class establishes neither surface nor permission
nor verification: tracks can be paved, and informal footways exist. Other splits give far larger
numbers, measured on the full surface:

| classes removed | lost 15-min PASS cells | lost PASS buildings |
|---|---|---|
| `track` + `path` | 414 | **0.393%** |
| `footway` | 2,049 | **3.775%** |
| `service` | 5,975 | **9.004%** |
| `footway` + `service` | 6,373 | **8.964%** |
| unnamed `footway` + `service` | 6,195 | **9.147%** |
| unnamed `track`/`path`/`footway`/`service` (880,775 edges) | — | **9.20%** |

**None of these is an error rate.** They are full-pipeline policy sensitivities: the larger
deletions also change destination snapping, so they do not isolate a route-only effect. And
excluding `footway` or `service` wholesale is not a candidate policy — unnamed footways are
sidewalks and crossings and unnamed service ways are driveways, which is why the last row removes
60% of the graph. The spread from 0.39% to 9.2% is the measure of **how little the class tag
settles**, not a range the true exposure lies in.

**The tag that would settle it is absent.** `EXTRA_WAY_TAGS` in `speeds.py` requests `foot`,
`bicycle`, `motor_vehicle`, `motorcar`, `oneway:bicycle` and `sidewalk`. It does **not** request
`surface`, so unpaved-versus-paved is not knowable from the extracted graph at all. Adding
`surface` (and `informal`) and re-extracting is cheap, and the layer needs rebuilding anyway — see
[[project-phase1-s3-stale-walk-raster]]. That is the single change that would turn this question
from a guess into a measurement.

## What the sheet rows actually show

Revision 1 wrote "the sheet hit it 3 times in 16" against a metro-wide 0.39% and explained the gap
by stratum enrichment. The enrichment is real and now measured — among baseline PASS cells within
90 s below a threshold, the loss rate is **1.164% against 0.429%** at ten minutes and **2.651%
against 0.871%** at fifteen, so **2.72× and 3.04×**.

**But the comparison was still wrong**, because the two sides count different things. The three
changed rows are:

| row | published | no track | outcome |
|---|---|---|---|
| `band15min_pass-01` | 847.3 s | 863.8 s | still PASS |
| `band15min_pass-03` | 810.8 s | 1,786.9 s | **loses PASS** |
| `band15min_fail-03` | 962.6 s | 1,011.0 s | still FAIL |

So 3-in-16 counts *any time change* while 0.39% counts *buildings losing PASS*. **One sampled row
loses a PASS, not three.** Different outcomes, weights and strata; the comparison should not have
been made.

Also corrected: the "10,010 cells into UNKNOWN" figure is a **net change in non-finite times**, not
a count of new unknowns. Gross, 10,080 go finite → non-finite and 70 the other way; of the 10,080,
**8,307 become `OFF_NETWORK` and 1,773 become `BEYOND_HORIZON`**, and the latter are *known FAILs*
at every published threshold, not unknowns. At fifteen minutes the deletion also **gains** 245 PASS
cells, leaving a net reduction of 169 cells and 493 buildings.

## A route matching the owner's report

Codex pass 34 found one, and this replaces revision 1's "the observation sits between the two
bounds" framing. That bracket was not a clean comparison: the no-track rebuild also **changed the
destination**, to Seal The Seasons rather than Hill's Family Asian Markets, so it compared two
different journeys.

Holding Hill's Family Asian Markets fixed and entering the network through the **`service` way
57.4 m out**, with neither `track` nor `path`:

**2,139.9 m = 1.3297 miles, 1,533.1 s = 25.55 minutes.**

Against the owner's 1.3 miles and ~25 minutes. It is a **reproducible candidate, not proof** of the
route they walked — their access connector is unknown and a straight-line 57.4 m leg is an
assumption. But it is a far better account than the bracket, and it says the real journey is
reachable in our own graph once the private track is out of the way.

## What this says about the estimands

E1 and E2 cannot see any of it. Both sides read the same road graph, so a route down a private track
is agreement, not error — the same structural blind spot as a closed grocery, which is why
[[project-phase1-s3-step2-conditional-estimand]] records destination validity as E1c's declared
blind spot. **One walked journey found what eleven adversarial passes on the instrument could not.**
Plan §0 ranks the walked audit first by risk retired; this is the first evidence that the ranking
was right.

## The decision, and what it is not

1. **Raise `RESTRICTED_PENALTY_S["walk"]` from 120 s.** At 600 s it fixes the walked cell for
   1.10% of 15-minute PASS buildings. This is the cheapest option, it needs no new data, and it
   uses a mechanism already in production. **Recommended.**
2. **Add `surface` to `EXTRA_WAY_TAGS` and re-extract**, so unpaved ways can be penalised on their
   own evidence rather than by class. The layer needs rebuilding anyway.
3. **Keep 120 s and disclose.** Defensible only with the walked evidence stated: we know of at
   least one cell whose PASS depends on a private track and is wrong by about eleven minutes.

**Not available as stated:** revision 1 claimed a penalised track "would lose to any paved
alternative". That is false for any finite penalty — Codex's counterexample selects a 100 s track
plus a 120 s penalty over a 1,000 s paved alternative, and this journey's own private tracks are
already penalised and still win. A penalty changes the exchange rate; it does not establish a
preference order.

Also withdrawn from revision 1: the words **"unmapped", "artificial" and "impassable"**. These are
mapped ways whose real-world usability this work has not established. What is established is that
one of them is tagged `access=private` and that walking the journey took nearly twice as long as the
model said.

## Tools

- `scripts/explain_journey.py <sheet> <id> [--drop track,path]` — the edges near the cell, the
  matched way, the route segment by segment, and a reconciliation of the segment sum against the
  authoritative on-network time.
- `scripts/measure_restricted_walk_policy.py` — the penalty table above, to
  `data/restricted_walk_policy_grocery_walk.json`.
- `scripts/measure_soft_way_dependence.py` — the class-sensitivity table, to
  `data/soft_way_dependence_grocery_walk.json`.
- `scripts/diagnose_track_dependence.py <sheet>` — per-sheet counterfactuals.

Related: [[project-phase1-s3-stale-walk-raster]],
[[project-phase1-s3-audit-destination-recovery]], [[project-phase1-s3-step0-audit-harness]],
[[feedback-decide-by-measurement-not-by-argument]].
