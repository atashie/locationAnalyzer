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

Related: [[feedback-experiments-over-priors]], [[feedback-fix-the-domain-not-the-example]],
[[feedback-a-relative-invariant-cannot-see-an-absence]],
[[feedback-computable-property-is-not-the-claim]],
[[feedback-a-fixture-is-exact-only-where-you-point-it]], [[project-phase1-s3-design]].
