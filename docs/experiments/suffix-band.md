# The suffix-aware band, built and measured

**2026-11-13.** Phase 4b.0, part two. `v2/scripts/spike_suffix_band.py`,
`docs/experiments/suffix-band.json`, `v2/tests/test_suffix_band.py`.

The comparator plan listed three repairs for design §12 amendment item 6 and priced none of them.
The first spike measured a band that was not the one the plan proposed, and Codex pass 41 F5 found
that implementation order-dependent as well. This builds the band the plan actually described —
**width sized from the largest reachable suffix ulp** — on the journey model rather than on a plain
weighted digraph, and reports what it costs and what it still misses.

## The rule, and why the width is what it is

§2.4 ranks the once-rounded total of all the terms a journey forms. Two prefixes at one node with
exact costs `a < b` give totals `rnd(a + S)` and `rnd(b + S)` for a suffix of exact cost `S`. If
those round to one binary64 value `T`, both lie in one rounding interval, and that interval is at
most `ulp(T)` wide. So:

> if `b − a > ulp(U)` for an upper bound `U` on every total reachable through this node, the two
> can never share a final cost, whatever the suffix follows.

That is the band. At node `v`, retain any label whose exact prefix cost exceeds the node's exact
minimum by at most `W(v) = ulp(U(v))`, and discard the rest. The width comes from the **suffix**,
which is what lets it keep a **strictly more expensive** prefix — the thing item 6 is about, and
the thing the first spike's band could not do.

Prefix sums are exact rationals, so the comparisons that decide retention are exact and the width
is measured from a quantity computed before the search starts. That is where order-independence
comes from.

## It selects item 6's own witness

| | cost argmin | reported seconds | verdict at 600 s |
|---|---|---|---|
| §2.4, by exhaustive enumeration | 2003 | **5.0** | PASS |
| the band | 2003 | **5.0** | PASS |
| a `(cost, time)` pair label | 2003 | 1,004.0 | **FAIL** |

The band keeps 7 labels across 5 nodes on that graph — 1.4 per node.

## Against the exhaustive oracle

150 graphs per population, every answer checked for **membership** (is this a journey the model can
form?) as well as agreement, and each quantity counted separately.

| population | compared | with a cost tie | one band wrong | two bands wrong | pair label wrong |
|---|---|---|---|---|---|
| generic | 144 | 44 | nothing | nothing | cost 22, time 22 |
| planted near-ties | 150 | 129 | nothing | nothing | time 86, route 46 |

The pair label also returned an answer **no journey in the model has** on 28 generic and 40 planted
graphs: it left-accumulates, so its reported totals are not the `fsum` of any journey's terms. The
band did that zero times in both populations.

"Generic" is 5–6 node graphs with seconds drawn from a continuum; "planted" is diamonds whose arms
differ by a few ulps of cost behind a long shared suffix. **A zero in the generic population means
only that the band had nothing to do there** — that population does not exercise the mechanism.

## What it costs

| population | labels per node, mean | max |
|---|---|---|
| generic | 1.0 | 1.0 |
| planted near-ties | 1.30 | 1.4 |

With weights drawn from a continuum the band is **free**: distinct prefix costs are nowhere near an
ulp of the total apart, so it keeps one label per node, exactly as a scalar search would. Exactly
equal prefix costs cost nothing either, because they share a key and the dominance collapses them.
Only prefixes differing by *less than an ulp of the total* buy another label.

That is not a bound, and the adversarial family says why. With `k` diamonds whose arms are one ulp
of cost apart:

| diamonds | labels | per node | expansions |
|---|---|---|---|
| 1 | 7 | 1.40 | 14 |
| 4 | 40 | 2.86 | 80 |
| 8 | 126 | 4.85 | 252 |
| 16 | 442 | 8.84 | 884 |

Growth is linear per node and the work is proportional — the search is label-setting, ordered by
`(cost, time, route)`, which is non-decreasing along any path. The retained count at a node is
bounded by `W / g`, the width over the smallest non-zero gap between distinct prefix costs. On this
family that bound — `capacity` in the artifact — is **8,192**, and the measured counts are small
only because the family supplies `k` distinct costs rather than 8,192.

## The width depends on what bounds the suffix, and the difference is large

| bound on the total | width | in ulps of the total | selects the normative answer |
|---|---|---|---|
| the graph's own total (twice every edge cost) | 1.82e-12 s | 8 | yes |
| the query's own ceiling | 2.27e-13 s | 1 | yes |

A search that is told nothing about the query can only use the graph. On a city graph of 10⁷
seconds of edge cost against a 2,000-second journey that ratio is **16,384×** — arithmetic, not a
measurement, and stated as such. A comparator that already carries a threshold should size the
band from it.

## What the band does not settle: route identity

The dominance that bounds the label count keeps the smallest exact prefix time per exact cost. That
is sound for the reported numbers — once the cost is fixed, reported time is non-decreasing in
exact prefix time — and **unsound for §2.4's route key**. Two prefix times under an ulp apart round
to one reported time, and §2.4 then decides on the route sequence, which the dominance has already
chosen on a different criterion.

`--route-witness` is that graph: both arms cost exactly the same, the arm through node 1 is one ulp
of 500 slower and carries the smaller identity `(0, 1, …)`, both totals round to 1,004 s. The
single band reports the right seconds and names the wrong route. A second band on time, sized the
same way, fixes it — 5 labels become 7.

## The precondition, and what violating it actually costs

The soundness argument needs **no cycle costing less than the band width**. Pass 41 F4's reason the
route dominance is safe is that two node-simple prefixes from one root to one merge cannot be
proper prefixes of each other; a cycle at or below `W` breaks exactly that. A zero-cost edge
permitting both directions is already such a cycle.

Measured rather than assumed, over 400 graphs each with a zero-cost two-way edge planted:

| | |
|---|---|
| graphs the oracle could answer | 363 |
| flagged by the precondition check | **363** |
| band wrong on cost, time or destination | **0** |
| band wrong on the route sequence | 8 |
| band returned an unformable journey | 0 |

So the violation costs the **route sequence only**. The numbers are safe for a reason, not by luck:
a zero-cost cycle of zero time changes neither total, and one of positive time can only raise the
time, so the minimum-time label at a given exact cost still dominates.

## Order independence

Six permutations of the witness graph's edge list: the band gives **one** distinct answer, and the
`first_arrival` positive control gives two. Across both sweep populations, zero of 294 graphs moved
under three permutations each. The control is there because a check that has never caught anything
is not evidence.

## What this means for item 6

**Item 6 stands exactly as written.** It says §2.4's ranking is not implementable by any
prefix-pruning search, and the band is not one: it retains prefixes that are strictly more
expensive, which is precisely what pruning on a prefix order cannot do.

What has changed is that **one of the three repairs is now built, measured and cheap on this
evidence**: correct on every graph tried, order-independent against a control, free on generic
weights, and with a stated precondition that is checkable in one pass over the edges. Its two real
costs are a width that must be sized from a bound on the total — loose by four orders of magnitude
if taken from the graph instead of the query — and a second band if the **named route** must be
normative as well as the reported number.
