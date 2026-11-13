# Codex adversarial review, pass 42 — the suffix-aware band

You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at commit
`e0c699c`. Python: `v2/.venv/Scripts/python.exe`. **Do not create temporary directories inside the
repository** — pass pytest an explicit `--basetemp` outside it, or skip the full suite and say so.

## What to review: phase 4b.0 part two, the band

* `v2/scripts/spike_suffix_band.py` — the band
* `docs/experiments/suffix-band.md` and `.json` — the report and the numbers
* `v2/tests/test_suffix_band.py` — 11 fixtures
* the 4b.0 outcome blocks in `docs/plans/2026-11-11-step4-comparator-plan.md`
* §12 amendment item 6 in `docs/plans/2026-11-04-s3-measurement-design.md`

Your pass 41 refuted the previous spike's recommendation and the gate was retained. The plan then
owed one of two things before 4b could start: build the band it had described, or specify an
amendment. This builds the band and recommends taking it. **That recommendation is what I want
attacked.**

## The claim

§2.4 ranks the once-rounded total of all terms a journey forms. Two prefixes at one node with exact
costs `a < b` give totals `rnd(a + S)` and `rnd(b + S)`; if those round to one value `T` they lie
in one rounding interval, at most `ulp(T)` wide. So a gap wider than `ulp(U)`, for an upper bound
`U` on every reachable total, can never rejoin the final tie. The band retains every label within
`W(v) = ulp(2·U(v))` of the node's **exact** minimum prefix cost, with a binade of headroom.

Reported results:

| | |
|---|---|
| item 6's witness | band 5.0 s, pair label 1,004.0 s, oracle 5.0 s — PASS against FAIL |
| 144 generic graphs | band: no quantity wrong; pair label: cost 22, time 22, unformable 28 |
| 150 planted near-tie graphs | band: no quantity wrong; pair label: time 86, route 46, unformable 40 |
| labels per node | generic 1.0 mean and max; planted 1.30 mean, 1.4 max |
| adversarial, k one-ulp diamonds | linear per node, 8.84 at k=16, capacity 16,384 |
| order independence | band 1 distinct answer over 6 permutations; first-arrival control 2 |
| precondition violated (363 graphs) | route wrong 8, numbers wrong 0, unformable 0 |

## The claims to attack, hardest first

**A. Is the soundness argument actually sound?** It rests on: (i) `rnd(x) == rnd(y)` implies
`|y − x| ≤ ulp(rnd(x))`; (ii) `ulp` is non-decreasing in magnitude; (iii) therefore a width taken
at an upper bound covers every actual total. Attack each. Consider subnormals, the binade
boundaries where the rounding interval is asymmetric, overflow, and the exact ties that round-half-
even resolves. Is `2·U` really enough headroom, or can you construct a case where the band is still
too narrow? Does `_ceiling` — twice every edge cost plus the largest terminal term — actually bound
a node-simple suffix in this journey model, including an out-and-back over one edge and the
same-edge direct journeys that bypass the search entirely?

**B. The dominance is where I would look for a counterexample.** The band bounds its label count by
keeping, per node:

* pass one: one label per **exact prefix cost**, the one with the smallest `(exact time, route)`;
* pass two: one label per **(exact cost, exact time)** pair within a time band, smallest route.

I argue pass one is sound for the reported numbers because reported time is non-decreasing in exact
prefix time once the cost is fixed, and that route dominance is sound because of your pass 41 F4 —
two node-simple prefixes from one root to one merge cannot be proper prefixes of each other.
**Attack both.** In particular: the search carries **no visited set**, so it searches walks while
the oracle enumerates node-simple paths. I claim positive costs make them agree. Construct a graph
where they do not, or show the claim needs a condition I have not stated. The zero-cost case is
already measured; I am asking about the positive one.

**C. Does the time band actually settle route identity, or only in my one fixture?** `--route-witness`
is hand-built. The sweeps found **zero** route disagreements for the one-band variant, which means
the populations never exercise the miss — so the only evidence that the second band is needed, and
the only evidence that it is sufficient, is one constructed graph. Find a case the two-band variant
still gets wrong, or show the fixture does not demonstrate what it claims.

**D. The price claims.** "Free on generic weights, 1.0 labels per node, mean and max" and "the
retained count is bounded by `W / g`". Attack the generator: are the generic graphs so small
(5–6 nodes) or so coarse that the band could not have retained anything regardless? Is `capacity`
computed correctly — it divides the width by `ulp(1.0)`, which assumes the family's edges are 1
second. Is the label-setting claim right, that `(cost, time, route)` is non-decreasing along any
path so a key is final when first popped? Route tuples of different lengths and mixed element
types are compared; show a graph where that comparison raises, or orders two routes in a way §2.4
does not.

**E. Is the order-independence check real?** Six permutations of one graph, plus three per sweep
graph. The positive control moves and the band does not. Is the control strong enough to
demonstrate the check discriminates? Does permuting `graph.edges` actually change anything the band
depends on, given identities are index-free — or is the check tautological?

**F. The precondition.** "No cycle may cost less than the band width", checked by the sufficient
test that there is no zero-cost edge and the smallest positive edge cost exceeds the width. Is that
test sufficient? Is the measured asymmetry — route wrong 8, numbers wrong 0 — explained by the
reason I give (a zero-cost cycle cannot lower a time), or did I get lucky in 363 graphs? Construct
a zero-cost cycle that moves a reported **number**.

**G. Exactness.** The band carries `Fraction` prefix sums and the oracle sums terms with
`math.fsum`. I claim `float()` of the exact sum equals `fsum` of the same terms because both are
the correctly rounded exact sum, and that grouping the origin connector into the start labels and
the destination connector into the end labels does not change the total. Verify or refute, with
attention to the same-edge direct journeys and `_partial_route`.

**H. Is "item 6 is not repealed" honest, or word-play?** I claim the band is not a prefix-pruning
search because it retains strictly more expensive prefixes. Is that a real distinction, or is a
band with a bounded width just a prefix-pruning search with a wider threshold — in which case item
6 as written is false and should be restated again?

**I. The recommendation itself.** "Take the band, size its width from the query ceiling, carry the
second band only if the named route must be normative." Is that supported by what was measured, or
does it reach past the evidence the way pass 41 F1 found the last recommendation did? In
particular: nothing here was run on a real road graph, and the generic population is the one where
the band is free.

## What I claim to have caught myself, which you should verify rather than take

1. The band's `pops` were exponential under a DFS worklist (655,354 for 442 labels at k=16) and
   became 884 with a priority queue, with the retained set **identical**. Check that claim.
2. The precondition docstring asserted a sub-width cycle makes the retained set "not finite";
   measurement contradicted it. Check the replacement mechanism is the right one.
3. The width was `ulp(nextafter(bound))` and could be an underestimate by a binade, because a
   retained label's own excess can push its total past the bound. Check that `ulp(2·bound)` fixes
   it and that nothing else in the file depends on the old width.

## Output

For each finding: severity, the exact file and line, a **runnable reproducer**, and what it costs —
a number that moves, or a claim that must be withdrawn. Say plainly which of my claims you checked
and could **not** break; that is as useful as a finding. If the recommendation in §I is wrong,
say so in those words.
