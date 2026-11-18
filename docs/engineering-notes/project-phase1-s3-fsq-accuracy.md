# FSQ wins on identity and loses on category, and OSM is the opposite

**2026-11-18.** Owner: *"proceed with 1-3"* — the first of which is the measurement
[[project-phase1-s3-fsq-coverage]] named as "the right next measurement if anyone wants to trust
FSQ further". Script `v2/scripts/measure_fsq_accuracy.py`, sheets in
`docs/experiments/audit/{grocery,pharmacy}-fsq-accuracy.csv`.

**What it does.** The coverage run asked what FSQ holds where OSM is silent. This inverts the
selection: the records OSM **did** reach, where both sources propose a class for the same record
and can be put side by side. Same 120 m radius, same scoring, same thresholds, so the two runs
stay comparable.

| | grocery | pharmacy |
|---|---|---|
| records OSM reached | 373 | 223 |
| got a proposal from OSM | 322 | 90 |
| got a proposal from FSQ | 279 | 173 |
| **both, the comparable set** | **256** | **82** |
| same class | 101 | 74 |
| compatible, coarser | 137 | 6 |
| differ | 17 | 0 |
| **contradict** | **1** | **2** |
| agree or compatible | 93.0% | 97.6% |

## My own prediction was wrong, in both of its tests

I predicted this run would show that FSQ's agreement is an **echo**: Foursquare feeds Overture, our
places are Overture-derived, so FSQ agreeing with our record might be FSQ agreeing with itself.
That was written into [[project-phase1-s3-fsq-coverage]] after `KBI Biopharma` came back from FSQ as
`Retail > Pharmacy` at 0.0 m with name agreement 1.00. I gave it two falsifiable tests and it
failed both.

* **Coordinate coincidence: 7.0% grocery, 4.9% pharmacy.** Two independently surveyed datasets do
  not place a storefront at the same point to the centimetre; a shared upstream record does. If
  FSQ were largely echoing our extract this share would be high. It is small.
* **The brand split went the wrong way for pharmacy.** The prediction was that branded records
  agree *more*, because those are the chains every source holds. Grocery: +6.7 points (95.0%
  branded vs 88.3% brandless), in the predicted direction but modest. Pharmacy: **−2.7 points**
  (95.7% branded vs 98.3% brandless), the opposite direction.

So the shared-lineage reading is not supported. `KBI Biopharma` is still a real false positive at
maximum confidence, but it is **not** the symptom of a systematic echo, and `785e76a` overstated it
by generalising one case into a mechanism. The agreement is largely real.

## What the measurement actually found, which is better than what it went looking for

**OSM's proposals rest on a wrong-business match far more often than FSQ's.**

| name agreement of the match the proposal came from | grocery | pharmacy | combined |
|---|---|---|---|
| OSM proposal built on agreement **0.00** | 28 / 256 | 14 / 82 | **42 / 338 (12.4%)** |
| FSQ proposal built on agreement **0.00** | 2 / 256 | 1 / 82 | **3 / 338 (0.9%)** |

A zero name agreement at 35 m means the nearest tagged thing is a *different business*. OSM's POI
coverage is sparser than FSQ's, so the nearest tagged feature is often a neighbour in the same
strip mall — the exact failure mode `prefill_from_osm` was built to guard against, which it
discloses per row but which nobody had counted. **This is in the half of the data that was treated
as the good half.** Where the two sources differ, FSQ has the closer name match 7 times and OSM
once.

**But FSQ's categories are worse than OSM's, and not marginally.** Among the 17 grocery rows that
differ, FSQ calls three separate `Walmart Neighborhood Market` records `Organic Grocery`, `Lidl`
and `Ray's Supermarket` `Convenience Store`, `Sprouts Farmers Market` a `Farmers Market` and
`Casablanca Market` a `Butcher`. Those are not boundary judgements; they are wrong, at name
agreement 1.00.

So the two sources are complementary in a specific, usable way:

> **FSQ is the better source for *which business this is*. OSM is the better source for *what kind
> of thing it is*.** Use FSQ to fix the identity of a record, then read OSM's tag — but only once
> FSQ has confirmed the OSM feature is the same business.

That is the opposite of how the project has been using them, with OSM as the primary pass and FSQ
as an optional corroborator.

## "FSQ confirms, never rejects" needs replacing, not keeping

The coverage run's rule was: FSQ's positives are corroborated, its negatives are not. The three
contradictions here show the rule is drawn in the wrong place.

| record | OSM | FSQ | who is right |
|---|---|---|---|
| Cameron Village **ABC Store** | `shop=supermarket` on *The Fresh Market*, 35 m, **agr 0.00** | *ABC Store*, 13 m, agr 0.33, **Liquor Store** | **FSQ.** An ABC Store is a state liquor store. OSM matched a neighbour. |
| **HealthSmart Pharmacy** | `amenity=pharmacy` on *Healthsmart Pharmacy*, 6.4 m, agr 1.00 | *HealthSmart Pharmacy*, 39.4 m, agr 1.00, **Doctor's Office** | **OSM.** FSQ agrees on identity and still gets the category wrong. |
| **Southpoint Pharmacy** | `amenity=pharmacy` on *Southpoint Pharmacy*, 19.2 m, agr 1.00 | *Southpoint **Medicine***, 15.7 m, agr 0.50, **Doctor's Office** | **OSM.** FSQ matched a different business. |

One rule explains all three, and it is not about which source the proposal came from:

> **A proposal is worth what its match is worth, and a proposal that denies what the record's own
> name asserts is evidence against the proposal.** Check the name agreement of the match first,
> then check whether the proposal contradicts the record's own name. Either test failing is enough
> to set the proposal aside — whichever source produced it.

The ABC Store case is the one the old rule got backwards: FSQ's *negative* was right there, because
it was consistent with the record's own name. The old rule would have discarded it.

## The specialty signal exists; the size signal still does not

[[project-phase1-s3-fsq-coverage]] found that FSQ's `Supermarket` / `Grocery Store` split carries
no information about store size, and that stands. But `Health Food Store` and `Organic Grocery` are
different labels, and they land on `Earth Fare`, `The Grain Mill Grocery Co-op` and
`Whole Foods Market` — which is the `OSM_CONFIRMED_SPECIALTY` boundary the owner has an open
decision about. The three `Walmart Neighborhood Market` rows show the same labels misfiring, so
this is a lead rather than a rule. **Nothing available to us measures range.**

## Gates, and reporting their reach

Every diagnostic now prints how many times it was **reached**, not only what it found — the lesson
from [[feedback-a-predeclared-gate-must-be-shown-reachable]], enforced in the script instead of
remembered. It earned itself immediately:

* *FSQ denies what OSM proposes*: reached 1 (grocery), 2 (pharmacy). The half the coverage run
  could never exercise for grocery has now fired exactly once.
* *OSM denies what FSQ proposes*: **never reached, 0 opportunities, in both categories.** Printed
  as "this says nothing about the data; it says the check could not run" — which is the whole
  point, because a blank line here previously read as a clean result.
* *FSQ dates a record closed that OSM still tags as trading*: reached 15 grocery / 24 pharmacy,
  found 10 / 2. Those rows bound how far `date_closed` can be trusted in bulk, and are not the ten
  accepted on 2026-11-18, which were all records OSM could not reach at all.

## What this does not establish

* **Neither source is ground truth.** This measures agreement. Where they differ the sheet says
  which way and the script does not rule.
* **No table was edited.** Both sheets carry a blank `verdict` column.
* **The 12.4% figure is about the comparable set**, not about the whole prefill: it counts
  proposals where both sources spoke.
* **It does not re-run the prefill.** The 42 OSM proposals resting on a 0.00 name agreement are
  identified but not withdrawn; whether to re-derive `OSM_CONFIRMED_SUPERMARKETS` with a name-
  agreement floor is a decision, not a cleanup.

## Recommendation

1. **Put a name-agreement floor on the OSM prefill**, or at least report the count, because 12.4%
   is high enough to matter and the sheets already carry the number per row.
2. **Promote FSQ from corroborator to the identity pass**, keeping OSM's tag as the category
   signal. The order the project uses now is backwards.
3. **Replace "FSQ confirms, never rejects"** with the match-quality and self-description rule
   above, which is one rule for both sources and explains all three contradictions.

Related: [[project-phase1-s3-fsq-coverage]], [[reference-places-provider-needed]],
[[feedback-a-predeclared-gate-must-be-shown-reachable]], [[project-phase1-s3-destination-identity]],
[[project-phase1-s3-progress]].
