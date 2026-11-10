---
name: feedback-decide-by-measurement-not-by-argument
description: "Five rounds of choosing a rule by reasoning produced one that lasted an hour; the failure was not the rules but describing an argument as a measurement, and the exit is to measure prevalence on real data before choosing"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-06T21:24:14.637Z
---

Learned 2026-11-06 on S3's attachment rule, across Codex passes 19–26. Four passes had already
diagnosed the *process* (see [[feedback-fix-the-domain-not-the-example]]) and I built an invariant
layer in response (see [[feedback-a-relative-invariant-cannot-see-an-absence]]). **It did not stop
the pattern.** Pass 24 then refuted a rule I had recommended and the owner had adopted an hour
earlier, and pass 26 refuted three claims in my proposal to revert it.

The failure was never in the rules:

> **I kept deciding by argument and then describing the argument as a measurement.**

Every rule choice was settled by reasoning over synthetic counterexamples, then reported with real
numbers attached — which made it *look* empirical. The numbers were real. The **inference** from them
was the argument, and that is what kept being wrong.

**The three symptoms, all in one 90-minute stretch.**

1. **Scope inflation.** "The two readings never disagree across the domain" and "the residues are a
   zero-length count and 1.4e-14 s" were true of my **31 scenarios** and reported as properties of
   the rule. Pass 24 confirmed the scenario measurements and refuted the inference. I had written
   *"'measured across the domain' is a lie if you measured the scenarios"* into a memory note hours
   before breaking it.
2. **Fixing the step that was not the cause.** The subdivision flip came from the **projection
   arithmetic**; I amended the **band**. The amendment therefore did not fix its own motivating case,
   while introducing a record-segmentation dependence that the rule it replaced did not have. Two
   arms at exact rational squared distance **1** computed one ulp apart (0.9999999999999999 vs 1.0),
   so an "exact minimum" filter discarded a genuine tie: **996.764 s FAIL** against **16.912 s PASS**.
3. **Overstating the reversal too.** Proposing the revert I said the amendment "bought nothing" and
   was "strictly worse". It **had** fixed its motivating case; agreement on two representations does
   not make a rule generally better. I also used the product's 60 s accuracy tolerance as a licence —
   it is an **aggregate real-world target**, not a budget the attachment rule may spend.

**How to apply.**
- **Before choosing a rule, measure how often the phenomenon occurs on real data.** Every
  counterexample in eight review passes was synthetic. The real graph (539,814 nodes) was on disk the
  whole time. If the phenomenon is rare, pick the simplest rule and declare it; if common, the
  measurement says which option matters. Argument cannot tell you which world you are in.
- **Distinguish "specified" from "justified".** Pass 26: *"Calling this a convention makes the result
  specified, not physically justified."* Declaring a convention and listing its consequences is an
  honest, bounded move. Claiming the convention is *right* needs evidence.
- **Allocate the sensitivity budget before seeing the results**, from existing requirements. Inventing
  a tolerance from the data is how a measurement gets talked into agreeing with you.
- **A small pilot cannot establish rarity.** Zero events in 1,000 observations per frame bounds the
  rate at about **0.30%** one-sided 95% — not "essentially never". It *can* establish that a problem
  is common.
- **State what a replacement does not fix, in the same breath as what it does.** Had I written "this
  does not address projection arithmetic" when amending the band, the defect would have been obvious.
- **The decision procedure** (pass 26, now in the execution plan): one page naming the decision,
  scope, required claims, sensitivity budget and time box → run the paired pilot → inspect the
  **consequential cases**, not the aggregate → choose the simplest convention the evidence supports →
  version it → proceed. **Reopen only** for a measured budget breach, a reproducible consequential
  error, or a scope change. A new *synthetic* witness updates the declared limitation; it does not
  reopen the choice.
- **Keep a withdrawn estimand executable as a mutant.** Revision 9 was live for sixty minutes and is
  now `revision9-per-record-exact-minimum`. A withdrawn estimand needs a guard as much as a fixed
  defect does.

**The related fitness finding, from the same pair of reviews.** Eleven adversarial passes and ~11,000
lines of apparatus had gone into the instrument while the grid and encoding decisions S3 exists to
make were unstarted, and the estimand carrying nearly all the rigour (E1) compares our pipeline to our
own engine. Worse, E1b measures `Pr(product PASS and comparator FAIL)` over the whole frame, not
`Pr(wrong | displayed)` — so a 1% frame-wide rate can coexist with 10% of *shown* results being wrong.
**Check that the quantity under measurement is the one a user is harmed by.**

## 2026-11-10: the measurements were right and every inference from them was wrong

The owner walked one audited journey and found 25 minutes where the layer said 13.5. Everything that
followed was measured on real data, and **six of the eight things Codex pass 34 corrected were in
what the numbers were numbers *of*** — not in the arithmetic, which reproduced:

- a **ratio between two different journeys**: our 1,131 m against the owner's 1.3 miles, presented
  as "the route is half the real distance" when the two are lengths of journeys that need not be
  the same one;
- a **bracket across two destinations**: the no-track counterfactual routed to a different shop, so
  "the observation sits between the two bounds" compared three things, not two;
- a **class exclusion standing in for a usability question**: removing `track`+`path` costs 0.39% of
  15-minute PASS buildings, removing `footway` costs 3.775% and `service` 9.004%, and none of them
  measures whether a way exists on the ground — the tag that would (`surface`) was never extracted;
- a **net change reported as a gross one**: "10,010 cells into UNKNOWN" was a net movement in
  non-finite times, of which 1,773 became `BEYOND_HORIZON`, which are *known FAILs*;
- **two differently-defined rates compared directly**: "3 of 16 sheet rows" counted any time change
  against a metro-wide rate counting buildings that lose a PASS. One row loses a PASS;
- a **print limit read as a population**: my tool showed the nearest 14 edges and I wrote "every one
  of the 14 edges within 120 m". There are 19.

**The rule: when a number is produced to inform a decision, the thing most likely to be wrong is
what it is a number of.** Checking the computation does not touch this class of error at all, and
every one of these passed that check. The question that catches them is *"what exactly is in the
numerator and what exactly is in the denominator, and are they the same population"* — the same
question E1b failed in the fitness finding below, which is why this note is where it belongs.

**The corollary, and the reason it mattered here.** Framing the question wrongly stopped me finding
the cause. I measured highway-class sensitivity for two rounds; the actual mechanism was that the
approach is tagged **`access=private`**, is correctly penalised at 120 s per edge, and wins anyway
because 480 s of penalty cannot beat a 968 s detour. That is a **calibration** finding with a cheap
fix — 600 s fixes the cell for 1.10% of 15-minute PASS buildings — and it was reachable only once
the framing correction forced "what is causing this" in place of "which class should we delete".
See [[project-phase1-s3-soft-way-dependence]] and [[35-codex-review-pass34]].

Related: [[feedback-experiments-over-priors]], [[feedback-fix-the-domain-not-the-example]],
[[feedback-a-relative-invariant-cannot-see-an-absence]],
[[feedback-computable-property-is-not-the-claim]],
[[feedback-a-fixture-is-exact-only-where-you-point-it]], [[project-phase1-s3-design]].
