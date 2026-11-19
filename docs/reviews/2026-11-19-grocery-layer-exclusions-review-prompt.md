---
name: 2026-11-19-grocery-layer-exclusions-review-prompt
description: "Adversarial review prompt for removing eleven records from the published grocery layer, committed before launch; run against Codex gpt-6.1-sol and Antigravity/Gemini independently"
metadata:
  type: reference
---

# Adversarial review: the fifth pass, and the first change to a PUBLISHED layer

Committed **before** launch, and before either reviewer is started. Two reviewers run
independently and neither sees the other's output: **Codex** (`gpt-6.1-sol`, read-only) and
**Antigravity/Gemini** (`gemini-4-hydrogen-xhigh`). Antigravity can execute Python; Codex cannot.

The three previous reviews each found real defects my own tests had missed, and the last one found
that my strongest claim was *true and irrelevant*. So the items below are **the places I think I
am most likely to be wrong, not the places I am confident**. Two of them are attacks on the
judgement at the centre of this change, which I would rather have demolished now than after
somebody relies on it.

**This is the first change in S3 that removes records a household can actually be sent to.** Weight
product risk over defect severity, per the S3 execution plan §0.

---

## The prompt

Review three commits on branch `v2-rethink` in `C:\Users\arikt\documents\github\distanceFinder`:

* `ae89174` — **removes eleven records from the PUBLISHED `grocery` layer.** 543 → 532. This is the
  one that changes what households see; weight it accordingly.
* `aa1dfb0` — records the owner's four answers, corrects the live count, raises two new asks.
* `9291014` — corrects my own ask from "six missing stores" to five, and records that the grocery
  travel-time rasters are stale.

Read `v2/locfinder/places/exclusions.py` (the eleven entries and their evidence),
`v2/tests/test_place_exclusions.py` (the eight new tests), and the fifth-pass section plus asks
5 and 6 in `docs/engineering-notes/project-phase1-s3-progress.md`. Background on the previous pass
is in `docs/reviews/2026-11-18-name-recovery-review-findings.md`.

**Attack these specifically. Most are mine and several may be wrong; do not accept any of them
because it is stated confidently, and do not soften a finding because I predicted it.**

1. **THE CENTRAL JUDGEMENT, AND THE ONE I LEAST TRUST. I removed eleven destinations knowing it
   leaves five sites with no grocery record at all, and I argue the removal is still right.**
   At five of the ten bay sites there is a real Walmart Supercenter which is absent from the
   published layer (Overture files it `department_store` / `superstore` /
   `warehouse_club_store`, and the `grocery` wedge matches only `grocery_store`). The bay had been
   standing in for the store. After my change those households are told there is **no grocery
   there** — one of them with nothing published inside 2 km.

   **Argue, as strongly as you can, that this change made the product worse and should be
   reverted or held.** The strongest form of the case against me is probably: a Walmart grocery
   pickup bay *is* a way for a household to get a weekly shop — you order the same groceries and
   collect them — so excluding it serves a definition ("a shop you could do a weekly shop at")
   at the direct expense of the thing the definition exists to measure. If that is right, I have
   traded a real household benefit for taxonomic purity and called it correctness. Is it right?

2. **Did I ship the two halves in the wrong order?** The removal and the five missing stores are
   one defect with two signs. I shipped the half that makes coverage worse and filed the half that
   makes it better as an owner ask. Argue that the removal should have been **held** until the
   stores went in, and that "each record removed is removed correctly" is a defence of line-level
   correctness while the system as a whole got worse — which is the exact failure the project's
   own ledger instance 60 describes. If you think holding was right, say what the cost of holding
   would have been.

3. **"Cut by explicit id, never by the heuristic" may be a laundered heuristic.** I claim the
   published layer is cut by an id table with per-record evidence, never by the
   `names_a_service_point` screen, and I added a test asserting an unlisted bay-shaped name is
   still published. **But the eleven ids were SELECTED by running that screen over the layer.** So
   the heuristic did choose what leaves the published layer; the table only records its output and
   the test only prevents the next person from automating it. Is my claim honest? What would have
   to be true for it to be honest, and does the distinction protect anything real?

4. **The three records I deliberately left in.** `Weaver Street Market Administration`,
   `Food Line Distribution Center` and `Variety Pick-Up` are all flagged by the same screen and all
   still published. My reason is that the owner decided eleven records and extending an answer
   past what was asked makes a table unreviewable. Attack that: `Food Line Distribution Center` is
   **already classified `not_a_grocery` by our own classifier and published anyway**, so I have
   knowingly left a wrong destination in a layer households use, on a process argument. Is
   deference the right call here, or is it process theatre protecting me from a judgement call?

5. **Every number in the three commits.** Verify independently rather than reproducing my method:
   `grocery` 543 → 532; `supermarket` 242 unchanged; ten bays plus the Food House; 1,720 passed /
   24 skipped; and each bay entry's "nearest surviving grocery record N m" figure — those evidence
   strings are load-bearing, a test asserts each one is present, and **nothing checks that any of
   them is true.** Find one that is wrong. Note `pyproject.toml` sets `addopts = "-q"`, so plain
   `pytest -q` becomes `-qq` and prints no summary at all; use `--junitxml`.

6. **Ask 5, which I already corrected once.** I wrote "six missing Walmart Supercenters", then
   found one was a duplicate of a published record 33.3 m away and corrected it to five. **Find
   another duplicate among the five**, or a store I missed entirely. My search required the name to
   contain "supercenter" or "neighborhood market", which would miss a store recorded as plain
   "Walmart", and I excluded anything `names_a_service_point` rejects — which would also discard a
   real store whose name happens to contain a screened word. Separately: I report an upper bound of
   26 store-shaped records across all brands (`department_store` 13, `discount_store` 7,
   `superstore` 5, `warehouse_club_store` 1, no-primary 6) which I have **not** deduplicated. How
   many of those 26 are real missing shops?

7. **`Family Fare` sits in `SUPERMARKET_BRANDS` and appears 28 times as `convenience_store`.** In
   North Carolina, Family Fare is a petrol-station convenience chain, not the Michigan supermarket
   of the same name. If that is right, the brand table is promoting corner shops to `supermarket`
   and the whole brand-lookup approach has a collision problem it does not acknowledge. Check the
   other entries in `SUPERMARKET_BRANDS` for the same failure.

8. **The licence claim, which I verified thinly.** I assert that nothing published depends on an
   ODbL building footprint, so the source registry's *"authorised, not yet exercised"* still holds
   after `ae89174`. My entire check was `grep -c "m2" exclusions.py` returning 0. That is a proxy
   for the real question, not an answer to it. Is the claim actually true — does any published
   layer now depend, by any path, on footprint-derived evidence?

9. **The stale rasters.** I claim every `own_*grocery*` layer under `v2/data/layers/` predates the
   destination decisions, that removing destinations can only lengthen time-to-grocery, and that
   the rasters therefore understate it. Check the monotonicity claim properly — is there any way
   removing a destination shortens a computed travel time, or changes a cell's reachability
   classification in the other direction?

10. **Anything in the three commit messages or the progress note that overstates.** The previous
    two reviews each caught me conflating populations or asserting a consequence I had not
    measured, and the countermeasure — writing the attack into the prompt — has worked twice.
    Assume it has failed somewhere here and find where.

Report findings as a numbered list, most serious first: file and line, what breaks, and the
smallest input or command that demonstrates it. Separate **what is wrong** from **what is merely
overstated**, and say which findings would change what a household sees. **If a claim is correct,
say so** — a review that finds nothing is a useful result and I would rather have it than a
manufactured finding. Where you disagree with my judgement rather than my facts, say that too, and
make the strongest version of the case.
