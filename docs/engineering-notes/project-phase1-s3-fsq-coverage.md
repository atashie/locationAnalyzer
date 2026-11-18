# Foursquare reaches the records OSM cannot, but it confirms rather than decides

**2026-11-17.** Owner: *"3) yes, that sounds great, proceed"* — run the measurement named in
[[reference-places-provider-needed]]. Done. `v2/scripts/measure_fsq_coverage.py`, sheets in
`docs/experiments/audit/{grocery,pharmacy}-fsq-coverage.csv`.

**The objection it was built to test:** Foursquare contributes to Overture, and our places come
*from* Overture, so FSQ might add nothing for exactly the records that need it.

**The objection is refuted.** FSQ holds a place within 120 m for **321 of the 334** records where
OSM is silent. But the measurement found two things that matter more than that number, and one of
them corrects a claim I made before taking it.

## The headline

| | grocery | pharmacy |
|---|---|---|
| records OSM could not reach (no feature within 120 m) | 154 | 180 |
| have an FSQ place within 120 m | **143** | **178** |
| got a category proposal | **58** | **122** |
| …and the names also agree (≥ 0.34) | 49 | 104 |
| both sources silent | 11 | 2 |
| marked **closed** by FSQ | 12 | 13 |

The name-agreeing matches sit at a **median 4.4 m (grocery) and 13.8 m (pharmacy)** from our
record. These are the same business, not a neighbour in the same strip mall — which was the failure
mode the OSM pass was built to guard against, and the guard holds here.

Comparability was deliberate: this reuses `prefill_from_osm`'s own `name_agreement`, its score
formula (`agreement × 2 + proximity`) and its 0.34 threshold, at the same 120 m radius. A second
scoring rule would have made the two passes incomparable.

## Finding 1: FSQ's categories are reliable in one direction only

**16 of the 26 "not a retail pharmacy" proposals deny what the record's own name asserts.**

| our record | FSQ's category |
|---|---|
| Fuquay Pharmacy | Health and Medicine > **Dentist** |
| Aspirar Pharmacy | Health and Medicine > **Dentist** |
| Kroger Pharmacy | Physician > **Doctor's Office** |
| White Dove Pharmacy, LLC | Physician > **Doctor's Office** |
| UNC Pharmacy at Panther Creek | **Medical Center** |

A proposal that denies what the name asserts is evidence against **the provider's category**, not
against the record. The positives, by contrast, are corroborated: 53 of the 72 `pharmacy`
proposals land on records whose own name says pharmacy, and the rest are CVS, Walgreens and Rite
Aid — brands that are pharmacies.

**So the rule for any future use: FSQ confirms, it never rejects.** That is the same shape as the
lesson already recorded for brand fields, where a brand naming a vendor *inside* a shop is not
evidence about the shop. The check is now in the script and prints on every run, so this cannot be
rediscovered by spot-check next time.

> **SUPERSEDED 2026-11-18.** This rule is drawn in the wrong place. The accuracy run found a case
> -- `Cameron Village ABC Store` -- where FSQ's **negative** is right and OSM's positive came from
> a neighbour at name agreement 0.00, and two cases where FSQ's negative is wrong because it denies
> what the record's own name asserts. One rule covers all three, for either source: **a proposal is
> worth what its match is worth, and a proposal that denies what the record's own name asserts is
> evidence against the proposal.** See [[project-phase1-s3-fsq-accuracy]].

### Corroborated in aggregate is not corroborated one by one

Added 2026-11-17, found while restating this result for the owner. **The sentence above is true of
the set and false of the members, and the difference decides whether the 72 can be accepted as a
batch.**

* **Three of the 72 match on proximity alone**, `name_agreement` below the 0.34 threshold. One is
  `Myra Greene`, matched to a **Walgreens 26 m away at agreement 0.00** — the strip-mall failure
  mode, sitting inside the confirmations.
* **One match is perfect and still wrong.** `KBI Biopharma`: 0.0 m, agreement **1.00**, FSQ
  category **`Retail > Pharmacy`**. KBI Biopharma is a biologics contract development and
  manufacturing organisation in RTP. No household fills a prescription there.
* **Both sources carry the same error.** Our own candidate list already holds that record
  (`a6a8f2de`, in `pharmacy-prefill-from-osm.csv`, OSM silent). Foursquare contributes to Overture
  and our places are Overture-derived, so FSQ agreeing with our record can be FSQ agreeing with
  itself.
  **MEASURED AND REFUTED, 2026-11-18.** That last sentence generalised one case into a mechanism,
  and the mechanism is not there. [[project-phase1-s3-fsq-accuracy]] gave it two falsifiable tests
  and it failed both: only **7.0% (grocery) and 4.9% (pharmacy)** of FSQ matches sit within 0.5 m
  of our record, where a shared upstream record would put most of them; and the branded/brandless
  agreement gap is **+6.7 points for grocery but -2.7 for pharmacy**, not the consistent positive
  the echo reading predicts. The agreement is largely real. `KBI Biopharma` remains a genuine
  false positive at maximum confidence -- it is simply not a symptom of lineage.

So the 72 are a **shortlist to review**, not a set to accept. The defensible claim is that FSQ's
positives are far better than its negatives, not that they are clean. `date_closed` is not exposed
to this, because Overture does not carry the field at all — there is nothing for FSQ to echo.

## Finding 2: I was wrong that FSQ supplies the missing "range" signal

Before running this I wrote that FSQ "separates Supermarket from Grocery Store from Convenience
Store — exactly the range distinction OSM's single `shop=supermarket` cannot make." **The taxonomy
makes that distinction. The data does not apply it consistently.**

Taking only the unambiguous big chains in our bbox — Harris Teeter, Food Lion, Lidl, ALDI, Kroger,
Publix, Wegmans, Trader Joe's, Whole Foods — FSQ labels them:

| label | n |
|---|---|
| Supermarket | 155 |
| other or none | 108 |
| **Grocery Store** | **38** |
| **Convenience Store** | **1** |

**Trader Joe's, Publix and Wegmans appear in both the Supermarket and the Grocery Store buckets.
Lidl appears as Grocery Store and as Convenience Store.** In our own unreached set, Harris Teeter
and Lidl both came back as "Grocery Store".

So the 44 `grocery store` proposals — 76% of the grocery yield — carry **no information about
store size**, and a `Grocery Store` label must not be read as "smaller than a supermarket". The
script's proposal text says "needs a human" for exactly this reason, and that wording is now
load-bearing rather than cautious. `OSM_CONFIRMED_SPECIALTY`'s holding position stands: **nothing
available to us measures range.**

Counting only proposals that actually decide something, grocery yields **13** (4 supermarket,
5 convenience, 4 specialty) of 154, not 58. Pharmacy yields **72**, or 94 counting `drugstore`.

## Finding 3: the closure dates are the part neither OSM nor Overture has

**25 records are marked closed, 12 of them name-agreeing and within 60 m.** `date_closed` is a
field our existing sources simply do not carry, and the closures list was opened as something to
build over time.

Two of them corroborate a decision already made: **Kroger, closed 2013-06-25** and **Kroger
Pharmacy, closed 2019-08-02** — Kroger was dropped from the grocery list on the owner's
instruction, from independent evidence. Also: Harris Teeter closed 2017, two Walgreens closed 2021,
Rite Aid closed 2020 and 2024, Family Market and El Atoron closed 2024.

This may be the most useful thing FSQ offers us, and it is not the thing we went looking for.

## What this does not establish

* **The grocery contradiction check never fired, because FSQ made zero "not a grocery" proposals
  for that set.** Grocery looking clean is therefore *not* evidence that it is; the gate was never
  exercised. Only the pharmacy half of Finding 1 is measured.
* **The snapshot is `2025-01-10`, about ten months old.** Closure dates are a lower bound and
  recent closures are missing. Newer releases exist through Foursquare's own catalog and a gated
  Hugging Face dataset, both of which want an account — the owner's to create, not a session's.
  The public Source Cooperative mirror needs no credentials and exposes only this release.
* **No proposal has been accepted.** Both sheets have a blank `verdict` column and no table was
  edited. 334 records remain exactly as classified as they were this morning.
* **One pharmacy confirmation is wrong at maximum confidence** (`KBI Biopharma`) and three rest
  on proximity alone. See the subsection added under Finding 1. The stronger claim made here on
  2026-11-17 -- that the confirmations are *not independent* because FSQ feeds Overture -- was
  measured on 2026-11-18 and does not hold; see [[project-phase1-s3-fsq-accuracy]].
* **It does not test FSQ against the records OSM *did* reach**, where the two could be compared
  for agreement. That would measure FSQ's accuracy rather than its coverage, and would be the
  right next measurement if anyone wants to trust it further.

## Licence, and the Decision 17 question

FSQ OS Places is **Apache 2.0** with attribution. Unlike Yelp — whose terms cap storage of Yelp
content at 24 hours and so cannot source a committed, published classification — FSQ can be
persisted, derived from and published, which is what the V2 job needs.

**One boundary to keep.** This clears FSQ for *our* ODbL-published layers. It does **not** clear
uploading FSQ data into OpenStreetMap: OSM requires explicit permission for imports and has its own
process, and Decision 17 already forbids sourcing OSM contributions from Overture. Nothing here
changes that.

## Recommendation

Adopt FSQ OS Places as a **corroborating source**, on the same footing as the `OSM_CONFIRMED_*`
tables: a regenerable derivation kept apart from hand-curated judgements, used to confirm existence,
identity and closure, and never used to reject a destination or to decide supermarket-versus-grocer.

Do not open a Yelp account for the V2 job; the terms forbid it.

Related: [[reference-places-provider-needed]], [[project-phase1-s3-destination-identity]],
[[project-v2-rethink-decisions]], [[project-phase1-s3-progress]].
