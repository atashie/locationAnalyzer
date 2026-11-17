# A walked journey took 25 minutes where the model said 13.5, down a private track

> ## RESOLVED 2026-11-17, in the model's favour. The owner confirmed the track is walkable.
>
> Verbatim: *"Yes those dirt-tracks exist and they are walkable; your estimates are correct (even
> google maps misses these, great work!)"*
>
> **So the 13.5-minute answer was right and the 25-minute walk was a different route.** This note
> was written on the assumption that a gap between the two meant the model was wrong. It meant the
> owner took the public way round. The audit README said exactly this would happen -- *"a walk can
> confirm a PASS but cannot refute one"* -- and it is the first time that caveat has had to do any
> work.
>
> **What this settles.** The disputed stretch, OSM way 1254722641, is `highway=track`,
> `access=private`, `surface=dirt`, `tracktype=grade4`. It is walked in practice. Routing over it
> is therefore legitimate, the published PASS for `band15min_pass-03` is correct, and the
> `RESTRICTED_PENALTY_S = 120 s` the owner declined to raise did not need raising. If anything this
> is evidence the penalty is too HIGH rather than too low, since the deterrent it models is not
> deterring anybody here.
>
> **What it does not settle.** There is still **no stopwatch time** for this journey, so the E3
> record holds no admissible timed observation and the 14-minute figure itself is unverified. What
> is verified is the thing that was actually in dispute: whether a household may and does use that
> ground.
>
> **And one claim this earns, carefully.** Our OSM-derived graph found a walkable connection that
> Google Maps does not route over. That is a genuine strength of using OSM plus local tagging
> rather than a commercial routing product, and it is worth knowing. It rests on **one** case
> confirmed by **one** local person, so it is a point in favour and not a general result.
>
> Everything below is kept as written, because the reasoning is still the reasoning and the
> measurements are still the measurements. Only the verdict moved.

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
3. **120 s over the 3 restricted hops is 360 s of cost, and the detour it must beat is 968 s**
   (782.7 s via the track against 1,750.4 s on public roads). Counted, not estimated: the
   explainer's `RESTRICTED EDGES` line reports **3 of 29 hops, 159 m, 360 s of cost penalty**.

   > **The 360 s is an artefact of where junctions are mapped — found 2026-11-16, pass 56.** The
   > penalty is a flat 120 s charged **per edge** (`speeds.py:133`), and those 3 hops lie on only
   > **two** OSM ways. The same 159 m of private track mapped as one graph edge would be charged
   > **120 s**. So the exchange rate a journey actually pays is 120 s x (number of restricted
   > segments it crosses), which is a property of the mapping's node density and not of the
   > journey. The owner declined to raise `RESTRICTED_PENALTY_S` from 120 s on the ground that it
   > is an unmeasured behavioural quantity; the effective penalty was never 120 s per journey, and
   > a decision about its value should probably be a decision about whether it is per edge at all.
   > See [[project-phase1-s3-donut-holes]].

   > **Pass 57, 2026-11-16: per-stretch at 120 s makes this very shortcut CHEAPER. Both
   > reviewers reached that independently and it cuts against the owner's leaning.** If the
   > penalty becomes one charge per continuous restricted run, this journey's 360 s falls to
   > **120 s** — so the rule that removes the segmentation artefact also *weakens* the deterrent
   > that this walk showed was already too weak. Per-stretch is a decision about the **unit**; it
   > does not carry the old calibration across, and changing the unit while keeping the value is
   > the one combination that is strictly worse than today.
   >
   > Two further corrections to what is written above. The three hops are on two OSM ways, but
   > **"one OSM way" does not imply one graph edge** — `simplify=True` removes only degree-two
   > nodes, so a single way crossing retained junctions still incurs three penalties. Codex
   > executed both halves: three same-way geometry segments collapse to **one** penalised edge,
   > and adding junction branches to that same way restores **three edges and 360 s**. So the
   > dependence is on **junction density**, not on arbitrary geometry-node density. Origin partial
   > edges are prorated (`snap.py:194-197`), which the bare per-edge description also misses.
   >
   > **What the reviewers measured, where I had only argued.** Exposure is large: the selected
   > route touches restricted ground for **67,676 park/walk OK cells (20.48% of the published
   > grid)**, 57,193 grocery/walk and 55,927 school/walk. Conditional on touching it, the
   > restricted-**edge** count is median 1, p90 3, p99 8, max 25, while the restricted-**run**
   > count is median 1, p90 1-2, max 6-7 — so the two rules differ on a real minority, not on
   > nobody. My fear that the median was 1 and the distinction therefore noise was **half right
   > and the wrong half**: the median *is* 1, and the tail is substantial.
   >
   > A grocery/walk per-stretch prototype keeping 120 s changed **5,690 published minute values**,
   > **189 threshold decisions at 20 minutes**, and gained **38 finite journeys while losing 0**.
   > That retires "it changes almost nothing" and "it changes a fifth of the answers" together.
   > Antigravity's independent run put it at 2.2-3.7% of OK cells with flips running +170/-6 —
   > overwhelmingly toward admitting more households onto private tracks — and found that
   > per-stretch **at 600 s still leaves the walked cell unfixed at 810.8 s**, while per-metre
   > moves it.
   >
   > **The cost objection is retired.** A full two-state expansion — `(node, was the preceding
   > edge restricted)` — costs **0.089 s -> 0.196 s** of Dijkstra and **37.81 MB -> 75.76 MB** of
   > CSR at Triangle scale, measured. An exact compressed form needs extra labels only at mixed
   > boundaries: Codex counts **46,043** such walk vertices, Antigravity **94,881** under a wider
   > definition and verified **0 diffs** against the full expansion. Two implementation traps
   > both flagged: parallel edges must not be collapsed under today's per-edge cost, because the
   > winner can change once a run is already open; and the **time** horizon must survive a cost
   > search, since a cost cutoff cannot stand in for a reported-time cutoff. `min_possible_s`
   > remains a valid lower bound either way — every physical journey still obeys the speed bound.
   >
   > **The reviewers split on the verdict.** Codex: **SUPPORTED** — it removes a dependence on
   > mapping accident, has effects beyond the median, and is affordable. Antigravity:
   > **PREMATURE** — the measurable effect is small, points the wrong way, and the walked ground
   > truth that would price any of the three units does not exist yet. Both agree the unit and the
   > value are separate decisions and that **neither reviewer can supply the behavioural number**;
   > only timed walks across `route_flag == 1` journeys can. The decision is the owner's and is
   > not taken.
   Earlier revisions said "~4 edges, 480 s" from a reading of the route rather than a count; the
   real figure is smaller, which makes the penalty further from sufficient, not closer.
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

**Re-measured 2026-11-10 on the re-extracted graph** (with `surface` and `vehicle` retained), after
the layer rebuild: every figure in this table is **byte-identical** to the first run — the same
126,197 restricted edges, the same walked-cell seconds in all four variants, the same lost-PASS
counts and the same UNKNOWN movement. Only the wall-clock timings differ. The owner's decision was
taken against this table and the table still describes the extract we now have.

> **One result in that table is not explained.** Removing restricted edges entirely loses *fewer*
> 15-minute PASS buildings (0.81%) than penalising them at 600 s (1.10%), which is backwards for a
> limit case. A plausible mechanism is that `symmetrise` runs after `add_travel_times`, so the
> removal variant symmetrises a different graph than the penalty variants do — but that is a
> hypothesis, not a verified explanation, and it is recorded unverified rather than asserted. I
> made the opposite mistake earlier the same day with the staleness monotonicity claim.

## The approach, way by way, with the tags read from OSM — 2026-11-16

The owner asked: *"I wonder if you are again routing to Edwards Street across property boundaries
instead of linking to Dogwood or Westwood Drive — it is not possible to walk directly to Edwards St
or S Merritt Mill rd."*

**Edwards Street is not in the route.** It is 262.9 m west of the query point and the model never
uses it. Neither is the route reaching South Merritt Mill Road directly: it joins that road at a
normal junction about 250 m north of the cell, by way of Raintree Lane and Locust Court.

What it does instead is leave the cell on **297.9 m of unnamed dirt**, and `explain_journey.py`
could not previously name the ways, so this could not be checked against the ground or against
osm.org. It prints the OSM way id on every hop now, plus an approach section with coordinates.

| hop | m | way | highway | tags | penalty |
|---|---|---|---|---|---|
| 1 | 50.2 | 1254722642 | `track` | `access=private` `motor_vehicle=no` `surface=dirt` `tracktype=grade4` | +120 s |
| 2 | 17.7 | 1254722641 | `track` | same | +120 s |
| 3 | 91.6 | 1254722641 | `track` | same | +120 s |
| 4 | 138.4 | 1343881800 | `path` | `informal=yes` `trail_visibility=bad` `smoothness=bad` `surface=dirt` `width=1` | **none** |
| 5 | 77.1 | 16707130 | Raintree Lane `residential` | — | none |

Walking order, from the matched point: **35.902606/-79.062699** west, then north along the track to
**35.903565/-79.063239**, then north-west on the path to Raintree Lane at
**35.904141/-79.064191**.

**The 138.4 m that completes the shortcut costs nothing.** Way 1343881800 carries no access tag, so
`classify_access` returns OPEN and `access_penalty_s` returns 0. It is tagged `informal=yes` —
OSM's word for a trail worn by use rather than built — with `trail_visibility=bad`, `smoothness=bad`
and `width=1`. **None of those four tags is in `EXTRA_WAY_TAGS`**, so no rule in this project can
read any of them; to the model it is an ordinary path. The 2026-11-10 revision of this note flagged
`informal` as the tag we had not extracted (449 ways). This is that gap, on the one journey anybody
has walked, carrying 46% of the approach for free. Only **159.5 m of the 297.9 m is penalised at
all.**

**A locked gate exists on this track network, and it is not on the route.** Way 1254722641 carries
node 11663898537, tagged `barrier=gate` `locked=yes` `material=metal`, at 35.904322/-79.062641. The
route traverses that way between its node indices 7 and 11; the gate is at index 17, about 200 m
further north, past the point where the route turns off onto the informal path. Two `ford=yes`
nodes on the same way, and one on way 430448289, are likewise off the traversed stretch. **The gate
does not block this journey.** It is recorded because checking the node order rather than the way
is the only reason this is not written the other way round — an OSM way is not a route, and ledger
instance 52 was exactly this mistake made in the opposite direction.

**Remove the tracks and the model goes where the owner says it must.** `--drop track`, keeping
paths, re-snaps the cell to a footway 46.0 m out and routes **Chase Park Road → Dogwood Drive →
Woodland Avenue → Westwood Drive** and onward. Both streets the owner named, in order. The informal
path is no shortcut on its own, because it is only reachable across the tracks: dropping `track`
alone is enough to end it. **The private dirt tracks are the whole mechanism.** That run is not a
like-for-like comparison of times — it also changes the destination to Seal The Seasons and totals
29.8 min — and the comparable figure remains the one below: **1.3297 miles, 25.55 minutes** holding
Hill's Family Asian Markets fixed, against the owner's 1.3 miles and about 25 minutes.

**What this does not establish.** Whether a person can walk hops 1 to 4 on the ground. OSM says
three of them are private dirt and the fourth is a faint informal trail, and the owner says the
link is not walkable. Both are consistent with the model being wrong here, and neither is a
measurement. The walk is still the thing that settles it, and the approach above is what to check,
hop by hop.

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

**What pass 34 confirmed about these numbers, as against what it corrected.** The corrections above
are easy to read as "the whole table is doubtful", and that would be the wrong conclusion. Three
independent checks came back clean:

- **No destination contamination.** The baseline, no-track and no-track-or-path variants retain
  539,814 / 538,178 / 534,949 nodes, yet all three keep exactly the **same 510 destination
  identities, POI snaps and admission decisions**. Removing those classes does not quietly change
  what the layer is routing to.
- **Component pruning causes none of the losses.** Holding the baseline nodes and destinations fixed
  while disabling pruning gives **446** lost 15-minute PASSes against 414 — so pruning introduces
  zero of them and in fact *rescues* 32.
- **The losses are attributable.** Across all four thresholds, **every one of the 5,287 distinct
  lost cells uses `track` or `path` on its baseline route.**

So the figures do measure what removing those classes does. The objection to them is about what that
*means* — a class is not a usability judgement — not about whether they were computed on comparable
populations.

**The tag that would settle it was absent — and now is not.** `EXTRA_WAY_TAGS` in `speeds.py` did
not request `surface`, so unpaved-versus-paved was not knowable from the extracted graph at all,
which is why two rounds of measurement could only ask about highway class. **Added 2026-11-10 with
`vehicle`, and the graph re-extracted** (`55b2749`, `5bbdcfb`): 165,549 ways carry `surface`, and
the walk layer is unchanged by the addition — the rebuild differs from the stored raster by exactly
the 7,246 cells the `symmetrise` fix predicts and no more. **No rule reads `surface` yet**, so the
question is now answerable rather than answered; `informal` (449 ways) is still not extracted. See
[[project-phase1-s3-extract-tag-gap]] and [[project-phase1-s3-stale-walk-raster]].

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
   1.10% of 15-minute PASS buildings. The cheapest option, no new data, a mechanism already in
   production. **Priced, and not taken.**
2. **Add `surface` to `EXTRA_WAY_TAGS` and re-extract**, so unpaved ways can be penalised on their
   own evidence rather than by class. **Taken 2026-11-10**, together with the layer rebuild the
   staleness needed anyway. Extraction only: no rule reads the tag yet.
3. **Keep 120 s and disclose.** Defensible only with the walked evidence stated: we know of at
   least one cell whose PASS depends on a private track and is wrong by about eleven minutes.
   **Taken.**

**The owner decided 3 and 2 on 2026-11-10, and declined 1 for a reason worth keeping.** One walked
journey prices the candidates but does not identify the right one. The penalty is an exchange rate
— how much detour a household is assumed to accept rather than walk down a private way — and that
is a behavioural quantity nothing in this project has measured. Setting it from a single observation
would be calibrating to an anecdote, and it would do so in the direction that makes the product
look more careful while resting on no more evidence than the number it replaced. So the gap is
carried, with the **signed error on restricted-route journeys** as the statistic to accumulate and
disclosure owed to households when estimates are delivered. Both are **specified and manual**:
`explain_journey.py` now prints each hop's access class and penalty and a per-journey
`RESTRICTED EDGES` line, so membership is computable one journey at a time, but no per-cell flag is
recorded in the layer bundle, no aggregation is defined, and nothing computes the statistic. Codex
pass 35 was right to call the first wording a commitment described as a mechanism.

**Superseded 2026-11-13.** The aggregation exists (`scripts/flag_restricted_routes.py`,
`arrival_with_route_flag`, `cell_route_flag`) and the per-cell flag **is** recorded in the layer
bundle and shipped in the wire format as `published-v3`'s optional third plane. The paragraph
above is kept as the record of what was true when it was written. What it says about the
*statistic* still holds in full: the signed error on restricted-route journeys needs walked
journeys, and nothing computes it, because the record holds no admissible observation.
**Do not quote the 600 s row as a plan.** Marking the cells whose route depends on a restricted way
is a candidate for step 8 and needs no new data — `access_restricted` is already on the edges and
the per-cell destination is now recovered.

Option 2 grew by one tag in the doing. `vehicle` is read by `access.classify_access` for drive and
bike and was never extracted, so that branch has never fired on any layer we have built. See
[[project-phase1-s3-extract-tag-gap]].

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
