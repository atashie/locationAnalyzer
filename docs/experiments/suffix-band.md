# The suffix-aware band, built and measured

**2026-11-13, revised the same day after Codex pass 42.** Phase 4b.0, part two.
`v2/scripts/spike_suffix_band.py`, `docs/experiments/suffix-band.json`,
`v2/tests/test_suffix_band.py` (14 fixtures), review in
`docs/research/43-codex-review-pass42-counterexamples/`.

The comparator plan listed three repairs for design §12 amendment item 6 and priced none. This
builds the first one — a band whose width is sized from the reachable suffix — on the journey model
rather than on a plain weighted digraph.

**Pass 42 refuted the recommendation this report first carried, and three of its claims.** Those are
marked below where they stood, not quietly deleted.

## The rule, and why the width is what it is

§2.4 ranks the once-rounded total of all the terms a journey forms. Suppose a label `Q` at node `v`,
with exact cost `σ(v) + g`, ends up at the final cost argmin `T` through some suffix `S`. The
minimum label `P` takes the same suffix to `rnd(σ(v) + S) ≤ T`, and it cannot be strictly below `T`
without contradicting `T` being the argmin — so both round to `T`, both lie in one rounding
interval, and that interval is at most `ulp(T)` wide. With `B` a float bound satisfying
`σ(v) + S ≤ B`, we get `T ≤ B` and so `g ≤ ulp(T) ≤ ulp(B)`.

> Retain at node `v` every label whose exact prefix cost exceeds the node's exact minimum by at
> most `W(v) = ulp(B)`. The bound is on the value the two **tie at**, never on the costlier label's
> own total.

The width comes from the suffix, which is what lets it keep a **strictly more expensive** prefix —
the thing item 6 is about, and the thing the first spike's band could not do.

The premise was checked, not assumed: over 240,000 exact pairs across binades, subnormals and
half-even ties, the worst `|y − x| / ulp(T)` is exactly **1.000000**, and `ulp` monotonicity had no
violations in 250,000 sorted samples. At a power of two the interval is only `0.75 · ulp(T)` wide.

> **Withdrawn (pass 42 F2).** An earlier version doubled the width, arguing that a retained label's
> own excess could push *its* total past `B` and across a binade. That is the wrong quantity to
> bound — see the argument above — so the doubling was never necessary, and it was the direct cause
> of an overflow: `2 × 3e307` is infinite on a graph the oracle answers.

## It selects item 6's own witness

| | cost argmin | reported seconds | verdict at 600 s |
|---|---|---|---|
| §2.4, by exhaustive enumeration | 2003 | **5.0** | PASS |
| the band | 2003 | **5.0** | PASS |
| a `(cost, time)` pair label | 2003 | 1,004.0 | **FAIL** |

7 labels across 5 nodes — an average of 1.4, with one node holding 2.

## Against the exhaustive oracle

150 graphs per population, every answer checked for **membership** (is this a journey the model can
form?) as well as agreement, and each quantity counted separately.

| population | compared | with a cost tie | one band wrong | two bands wrong | pair label wrong |
|---|---|---|---|---|---|
| generic | 144 | 44 | nothing | nothing | cost 22, time 22 |
| planted near-ties | 150 | 129 | nothing | nothing | time 86, route 46 |

The pair label also returned an answer **no journey in the model has** on 28 generic and 40 planted
graphs: it left-accumulates, so its totals are not the `fsum` of any journey's terms. The band did
that zero times.

"Generic" is 5–6 node graphs with seconds drawn from a continuum; "planted" is diamonds whose arms
differ by a few ulps of cost behind a long shared suffix. **A zero in the generic population means
only that the band had nothing to do there.**

## What it costs

| population | labels per node, mean | max graph average |
|---|---|---|
| generic | 1.0 | 1.0 |
| planted near-ties | 1.30 | 1.4 |

With weights drawn from a continuum the band keeps one label per node: no more than a scalar search
would. That is a statement about **retained labels**, not about runtime or memory.

> **Corrected (pass 42 F3).** The "max" column is the largest graph *average*, not the most labels
> at any one node. The witness averages 1.4 and has a node holding 2. `most_labels_at_one_node` is
> now reported separately.

The one-band count at a node is `floor(W / g) + 1` — the width over the smallest non-zero gap,
inclusive. On `k` diamonds whose arms are one ulp of cost apart:

| diamonds | labels | per node | expansions |
|---|---|---|---|
| 1 | 7 | 1.40 | 14 |
| 4 | 40 | 2.86 | 80 |
| 8 | 126 | 4.85 | 252 |
| 16 | 442 | 8.84 | 884 |

Growth is linear per node and the work is proportional: the search is label-setting, ordered by
`(cost, time, route)`, which is non-decreasing along any path. Capacity on that family — `W` in
ulps of a one-second edge — is 8,192, so the counts are small because the family supplies `k`
distinct costs, not because the band is intrinsically cheap.

## The route repair is exponential, and that changes the recommendation

A single band settles cost and travel time. It does **not** settle §2.4's route key: the dominance
that bounds the label count keeps the smallest exact prefix time per exact cost, and two prefix
times under an ulp apart round to one reported time, after which §2.4 decides on the route.
`--route-witness` is that graph — both arms cost the same, the arm through node 1 is one ulp of 500
slower and carries the smaller identity, both totals round to 1,004 s. The single band reports the
right seconds and names the wrong route. A second band on time fixes it there: 5 labels become 7.

**It does not fix it affordably.** Give every arm the same exact cost and a time that differs by a
different tiny amount in each diamond, and one cost bucket holds `2^k` distinct exact times, all
inside the time band:

| diamonds | one band | two bands |
|---|---|---|
| 2 | 8 | 17 |
| 6 | 20 | 317 |
| 8 | 26 | 1,277 |
| 10 | 32 | 5,117 |
| 12 | 38 | **20,477** |

`5·2^k − 3`, with every cost and time positive, the graph acyclic and the precondition holding.

> **Withdrawn (pass 42 F3).** "Exact cost ties cost the band nothing" is true of the one band and
> false of the two. And `W / g` does not bound the two-band count at all — the distinct times
> inside a cost bucket dominate it. The published diamond chain concealed this by giving each cost
> bucket a single time.

## The bound has to be a bound on cost

| bound on the cost the argmin ties at | width | in ulps of the total | selects correctly |
|---|---|---|---|
| the graph's own total (twice every edge cost) | 1.82e-12 s | 8 | yes |
| the cost of a journey that exists | 2.27e-13 s | 1 | yes |
| **the query's 600 s travel-time threshold** | — | — | **no** |

> **Withdrawn (pass 42 F1).** This report first recommended sizing the width from "the query's own
> ceiling". Cost is travel time **plus access penalties**, so a threshold on the reported time
> bounds neither. Scale the witness's costs by 16 and leave its times alone: the normative answer
> is still 5 s at cost 32,018, and a band sized from 600 s returns **1,004 s** — PASS becomes FAIL,
> from a band sized by a number that was never a bound.

`feasible_cost_bound()` is the tight bound that *is* sound: the cost of a journey that was actually
found, which the argmin cannot exceed. On the witness it gives 2003.0 and a width of exactly one
ulp. On a city graph of 10⁷ seconds of edge cost against a 2,000-second journey, the graph bound is
**16,384×** wider than needed — arithmetic, not a measurement.

An admissible graph can also overflow the bound: `ToyGraph` accepts a single edge of cost `7e307`
and the oracle answers it, while twice the graph total is infinite. The bound now saturates at the
largest finite binary64 instead of raising (pass 42 F2), which makes the band degenerate rather
than absent — the right direction, since a wider band retains more and never fewer.

## The precondition, and what violating it costs

The dominance that bounds the label count needs **no cycle costing less than the band width**. Pass
41 F4's reason the route dominance is safe is that two node-simple prefixes from one root to one
merge cannot be proper prefixes of each other; a cycle at or below `W` breaks exactly that. A
zero-cost edge permitting both directions is already such a cycle.

The precondition also delivers node-simplicity, which is otherwise an assumption: the search keeps
no visited set, but a repeated node means a cycle, and a cycle costs at least one edge, so the
second arrival is outside its own band and is dropped. **Positive costs alone are not enough** —
pass 42 built a two-way edge costing `2^-46` with zero time and got a winner containing two
out-and-back cycles, a journey the model cannot form. The precondition correctly reported false
there.

Measured over 400 graphs with a zero-cost two-way edge planted, half of them carrying a small
positive time:

| | |
|---|---|
| graphs the oracle could answer | 371 |
| flagged by the precondition check | **371** |
| band wrong on cost, time or destination | **0** |
| band wrong on the route sequence | 1 |
| band returned an unformable journey | 0 |

The numbers are safe for a reason, not by luck: a zero-cost cycle of zero time changes neither
total, and one of positive time can only raise the time, so the minimum-time label at a given exact
cost still dominates. Pass 42 reported an unformable **second-band** winner from a zero-cost edge
with positive time; this population did not reproduce one in 371 draws, which is a gap in the
population, not evidence against the finding.

## Order independence

Six permutations of the witness graph: the band gives **one** distinct answer, and the
`first_arrival` positive control gives two. Zero of 294 sweep graphs moved under three permutations
each. The control is there because a check that has never caught anything is not evidence.

## What this means for item 6

> **Withdrawn (pass 42 F4).** This report first said "item 6 stands exactly as written" because
> the band "is not a prefix-pruning search". It is one. It prunes prefixes — on a threshold that
> happens to be suffix-aware — and two lines of its own code drop a cost-2 prefix next to a cost-1
> one. Retaining *some* strictly costlier prefixes does not change the classification.

The defensible statement is narrower and more useful than an impossibility:

> §2.4's ranking cannot be implemented by a search that keeps **one** label per node, nor by any
> search whose pruning uses prefix information alone — the final rounding can make a strictly
> costlier prefix tie at the argmin. It **can** be implemented by a search that prunes on a
> threshold derived from a bound on the suffix.

So item 6 becomes a requirement rather than a wall, and the band is its constructive form:

* **take the one band.** Correct on every graph tried, order-independent against a control, one
  label per node on generic weights, with a precondition checkable in one pass over the edges.
* **size its width from a bound on cost** — a feasible journey's cost, not a time threshold — and
  fall back to the graph bound when none is available.
* **do not carry the second band by default.** It is the only thing that settles the named route,
  and it costs `5·2^k − 3` labels on a graph that is acyclic, positive and within the precondition.
  Route identity stays open.

The other two repairs — an amendment that settles both keys or adopts an exactly-additive primary
order, and accepting the gap and measuring its frequency on the real graph — remain unpriced.
Nothing here ran on a real road graph.
