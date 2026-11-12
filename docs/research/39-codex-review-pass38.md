# Codex pass 38 — against design revision 13, the exact primitives, and the T0 re-run

**2026-11-12.** Prompt committed before the pass as `39-codex-review-pass38-prompt.md`; report and
nine runnable reproducers in `39-codex-review-pass38-counterexamples/`. Reviewed HEAD `0b7281d`.

**1 High, 5 Medium, 2 Low. All eight reproduced; the High re-derived independently before being
acted on.** Five of them hit claims made in the three commits under review, two of which were
normative sentences in the design.

## What it certified, first

A review that only lists defects hides how much it checked, and the confirmations are what make the
remainder trustworthy.

- **The correctly-rounded root** against an independently written oracle on **2,004** radicands,
  including subnormals and exact ties, by comparing the original radicand with squared midpoints
  between the returned float and its neighbours — not by reproducing the binade algorithm.
- **Every other row of item 7**: the exact endpoint differences and clamp, the degenerate-segment
  zero, the prefix as `RN(sum of the specified rounded terms)`, the traversal fraction as a rounded
  division of rounded operands, the span's orientation and symmetry over 400 checks, and the
  zero-total convention.
- **The one-rounding argument**, precisely as scoped: one correct rounding is nearest to *that
  partial*, so a two-rounding float cannot be closer to it. Explicitly *not* a theorem about later
  prefixes, totals, fractions or selection — which is what revision 13 already says.
- **The refactor equivalence**, twice over: the historical 610-leaf artifact comparison, plus
  **2,005** fresh exact agreements between the pilot's deleted copy and the module, extracted from
  the committed source.
- **The lengths cache** under its documented precondition, with 400 further checks.
- **All three mutation retirements**: the `denom = 1` equivalence, the dead step-up loop, and the
  rounded-scaling retirement, the last with 2,000 more checks showing **224** changed lattice
  indices and **0** changed answers.
- **Both real census witnesses**, including the quadratic corroboration — and the second witness,
  which I had not examined: displacement `6.998565223626435e-6` m against an exact gap of
  `1.3820056210533949e-12` m.
- **Items 5 and 6 must stay open.** It re-ran pass 37's scalar-search reproducer: final rounded
  costs tie at `2**54`, the normative discriminator gives 2 s, scalar-prefix pruning gives 1,001 s.

## F1 — High — a normative guarantee the design does not have

§2.4 item 7 said *"every comparison that decides something made on the exact value"*. §2.2's two
caps and its 0.01 m band are comparisons that decide something, and all three are decided in
binary64 on a correctly-rounded residual.

Re-derived independently: on the admissible segment `(0,-1)→(0,0)` from `(200, 1e-6)` the exact
squared distance is `40000 + ~1e-12`, strictly outside `200**2`, so an exact predicate puts the point
**outside** the 200 m origin cap — while `rational_sqrt` returns exactly `200.0` and the binary64
`<=` admits it. The same arithmetic admits a destination outside the 300 m cap. **That is an
eligibility difference**: answerable against `OFF_NETWORK`, not an intermediate number.

The band carries the same distinction, demonstrated rather than argued: two vertical segments at
`x = 1` and `x = 1.01` queried from the origin both survive A, although the second exact distance
exceeds `1 + Fraction(0.01)` by `5/576460752303423488` — adding the band in binary64 rounds the
excess away. A is an operational *rounded-distance* band. It is not the literal exact-distance band,
and it is not convention B either, which additionally requires §2.2's degree-two normalisation.

**Fixed:** item 7's clause is scoped to the quantities item 7 fixes; the caps and the band are stated
to be decided on the correctly-rounded residual; and the exact-distance cap — `exact_sq <= cap**2`,
no root required — is recorded as a **different convention**, left open in §2.2's terms because it
changes which points are answerable and this design settles conventions by measurement.
`test_an_exact_cap_and_a_rounded_cap_disagree_and_the_difference_is_decidable` holds the witness.

## F4 — Medium — the finding that changed a published result

Two defects in one measurement. `adoption_stats` converted **both** parameters to `float` before
comparing, so "1,333,808 parameters differ" counted unequal *rounded images* of parameters that
differ exactly. And the candidate-level comparison used `coarse_occurrence`, which drops the
parameter — a coarsening I had justified in a docstring as removing noise. §2.2's occurrence key
carries the **unrounded** parameter, so the coarse label is not the normative identity.

Codex demonstrated both on real data, replaying the window geometries of the two recorded census
witnesses: **4** parameter differences under the published test against **6** under exact rational
comparison for the first, **1** against **2** for the second.

**Re-measured over the whole census**, which is why this finding cost a 47-minute re-run rather than
an edit:

| | published 2026-11-12, first run | corrected |
|---|---:|---:|
| parameters differing | 1,333,808 | **2,142,228** (1.61×) |
| retained occurrence identity changing | reported as **0** | **573,107 of 844,685 — 67.8%** |

The corrected reading is a **provenance** finding rather than an answer finding: places, counts,
eligibility and vertex/segment structure are unchanged, the largest displacement anywhere is
`4.7e-10` m, and yet the *recorded identity* of two thirds of retained candidates differs because an
occurrence label contains a parameter. §12 requires the retained candidate set to be persisted by
identity, so two runs differing only in this arithmetic write different manifests and report the
same answers.

## F2 — Medium — an impossibility claim where a measurement was already sufficient

The design said the span is *"the only implementable reading"* and that *"there is no exact prefix to
subtract"*. Wrong twice.

The step 4 plan's rule had defined its two prefixes as the **exactly-rounded** ones two lines
earlier, and a binary64 is a rational, so `Fraction(s_d) - Fraction(s_o)` implements the rule
immediately. And "not a `Fraction`" is not "not representable": a finite sum of rational radicals is
an exact algebraic expression. Codex represented `sqrt(2) + 20000000*t` as a sparse radical
expression, cancelled the common irrational part symbolically, and recovered W3's
`1.862645149230957e-9` m gap exactly.

**The span is still right, and the reason was already in hand:** on W3 both rounded prefixes are
`20000000`, so the subtraction gives `0.0` and the traversal vanishes, against 558.7935 s for the
span at weight `6e18`. I had measured that and then replaced it with a stronger argument that is
false. Recorded as a **tenth** instance in `feedback-verify-the-shape-of-the-risk`, and a new shape:
the first nine over-generalised a measurement, this one reached past a sufficient one.

## F3 — Medium — a crashing mutant counted as caught, and two rules with no mutation at all

The mutation *"compare the midpoint against the floored scaling"* referenced `scaled`, a local of
`rational_sqrt`, from inside `_decide`. It raised `NameError`, the subprocess failed, and the harness
counted a failing suite as a catch. **It had never exercised the arithmetic it was named after.**
Repaired to compute the floor locally, it fails three fixtures as it always should have.

Two executable mutants then passed **all 40** fixtures:

| mutation | wrong result | required |
|---|---:|---:|
| drop the `y` interpolation in `exact_position` | squared residual **4** | **0** |
| take `1 - t_d` for a cross-segment destination | fraction **0.625** | **0.375** |

The second is **625 s against 375 s** at weight 1000, and it survived because the only multi-segment
span fixture put the destination at a segment **midpoint**, where `t_d` and `1 - t_d` coincide. A
fixture chosen for roundness tested less than it looked like.

**Fixed:** both mutations added and both gaps covered by new fixtures; the harness now **smoke-runs
every mutant** on ordinary input and reports `INVALID` for one raising `NameError`,
`AttributeError`, `TypeError` and the like, so a crash can no longer be banked as a catch; and
`--self-test` plants such a mutant to prove the detector fires, because a crash-detector that cannot
fire is the same defect one level up. **24 mutations, all caught.**

## F5 — Medium — the sentinel bypassed the path it guarded

The sentinel called `raw_positions` directly. Codex changed only `measure_point`'s dispatch in
memory, forcing both arithmetic requests to the float branch: the sentinel still passed **2 of 2**
while `adoption_stats` compared one position and reported **zero for every raw difference** —
exactly the failed-adoption shape the sentinel exists to reject.

**Fixed:** each witness now runs through `adoption_stats` itself, and a **control** case was added
that must *not* fire, since two witnesses cannot distinguish a live counter from one stuck at 1. The
sentinel also asserts the counters move, not merely that two labels differ.

## F8 — Medium — a third step 4 row contradicts the adopted contract

The supersession block marked two rows superseded and left the zero-total row active, which says a
zero-length record *"contributes `cost_base + penalty` once with no apportionment"* and that distinct
structural vertices on it are **one** occurrence. Revision 13 requires fraction **0.0** for every
occurrence pair and §2.2 preserves the structural keys. Measured on `(5,5),(5,5),(5,5)`: the adopted
primitive gives **0** at weight 1000 against the row's **1000**, and the exact pilot retains **two**
vertex occurrences against the row's instruction to merge them. Marked superseded, with the
distinction it was reaching for — a full topological traversal against a partial one — named as a
separate §2.2 question rather than left inside a fraction rule.

## F6 and F7 — Low

**F6.** `explain_adoption_diff.py` asserted the design record **count** matched the artifact's
808,433. Two record sets can hold that count and differ in the geometry being queried: the
reproducer moved a measured residual from **1.0 m to 95.005 m** with no count change. Now a digest
of every coordinate of every record plus its forward and reverse times, recorded in the artifact as
`design_records_fingerprint` and checked before the script claims to describe a measured run.

**F7.** The artifact comparator flattened the document to dotted paths, so `{"x": []}` matched
`{"x": [{}]}`, `{"x": {}}` matched `{}`, and a literal `"a.b"` key collided with a nested one;
Python equality also matched `False` to `0` and `-0.0` to `0.0`. Rewritten as a recursive typed
comparison with a **13-case self-test** covering all four. **The historical 610-leaf refactor claim
was re-checked under the stronger tool and survives.**

## The pattern, and what this pass cost

Pass 37 reviewed a plan and cost a document rewrite. This pass reviewed **built and published**
work, and the price shows: F4 alone cost a 47-minute census re-run and the correction of a headline
figure that had already been reported. That is the argument for pass 37's lesson rather than against
it — the cheap pass is the one before the build.

Four of the eight are the same error in different clothes, and all four are mine:

- **F1** stated a guarantee over a domain nobody had enumerated. "Every comparison that decides
  something" was never checked against the two §2.2 predicates that decide eligibility.
- **F4** named a counter after a quantity and measured its image, then coarsened a comparison and
  reported the coarse answer as the answer.
- **F3** accepted an exit code as evidence about arithmetic.
- **F6** asserted a guard over a scalar summary of the thing it meant to bind.

The common form: **a claim whose subject is wider than the evidence that was gathered for it.** The
counter to it is not more care in prose, it is making each claim name what was varied — which is
what `feedback-verify-the-shape-of-the-risk` already says, now at ten instances.

Related: [[feedback-verify-the-shape-of-the-risk]], [[feedback-codex-adversarial-review]],
[[feedback-decide-by-measurement-not-by-argument]],
[[project-phase1-s3-step4a-exact-geometry]], [[project-phase1-s3-design]].
