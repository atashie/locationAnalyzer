# Pass 41: phase 4b.0 search-semantics spike

Reviewed branch `v2-rethink`, HEAD `6d2e22efd4ebc0cb930ceb5c2ac63ddd53049f11`, against
`docs/research/42-codex-review-pass41-prompt.md`. Review date: 2026-11-12.

**Do not narrow §12 item 6 on this evidence.** The proposed `(cost, time)` label still discards the
normative winner on pass 37's original witness, and on a version whose largest cost is only 1,000.
A real multi-destination journey with partial traversals and connectors returns **1,004 s instead
of 5 s**. The spike also uses a nonconforming oracle, overcounts distinct route ties, and tests a
different band from the plan's proposed band. Findings: **two High, three Medium**.

Only review artifacts were added; the spike, saved experiment, plan, and design were left unchanged.
This report follows the requested A–F attack order. Passing claims and their limits are explicit.

## Reproduction and scope

Run from the repository root, using the requested interpreter:

```powershell
v2/.venv/Scripts/python.exe -B docs/research/42-codex-review-pass41-counterexamples/run_all.py
```

This runs every attack in A–F order, asserts the reported outcomes, and writes final evidence to
[RESULTS.txt](RESULTS.txt) and [results.json](results.json). To run a particular attack:

```powershell
v2/.venv/Scripts/python.exe -B docs/research/42-codex-review-pass41-counterexamples/review.py A
```

Replace `A` with `B`–`F`, or provide several letters. [common.py](common.py) contains an independent
enumerator that retains individual binary64 terms until the complete path's `math.fsum`, including
edge indices so parallel records remain visible. [review.py](review.py) imports the actual spike
functions and the actual `toy.py` journey oracle. The harness uses no temporary directories, and
`-B` plus `sys.dont_write_bytecode` prevents import caches.

Environment: Python 3.13.1, Windows 11, as recorded in the evidence. The full repository suite was
**not run**: this review directly exercises the spike and its claimed oracle contract. Two existing
invariant tests were also run, with **2 passed in 0.26 s**:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$reviewTemp=Join-Path ([System.IO.Path]::GetTempPath()) ('distancefinder-pass41-' + [guid]::NewGuid().ToString('N'))
v2/.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --basetemp $reviewTemp v2/tests/test_invariants.py::test_the_ranking_does_not_select_a_unique_traversal v2/tests/test_invariants.py::test_the_ranking_does_not_determine_the_reported_decomposition
```

The actual pytest base was outside the repository:
`C:\Users\arikt\AppData\Local\Temp\distancefinder-pass41-5bb3194293d647bcbdfd693b15babf93`.
The pre-existing inaccessible `review32-i3g8fk_m/` and `v2/.pytest-review27-tmp/` were neither used
nor changed. Git status initially showed no changes; the final addition is this review directory.

## A. Journey abstraction — F1, High

**Claims refuted**, `v2/scripts/spike_search_semantics.py:9–15`:

> “The repair is neither of the three the step 4 plan offered. It is to key the label on the
> **pair** `(cost, time)` instead of on cost alone: still one label per node, still Dijkstra-shaped,
> and free.”

> “The geometry, attachment and connector layers contribute terms to a journey's totals and
> nothing to how a search prunes”

**Runnable reproducer:** `review.py A` (also `review.py C` for the original pass 37 witness).

The missing property is **compatibility of prefix order with completion**. §2.4 item 6, design
lines 514–522, ranks once-rounded totals of all formed terms. Two distinct prefix costs can become
the same final binary64 cost, exposing a time discriminator that a local pair comparison never
reaches. A plain graph can represent journeys, but ordinary additive scalar labels do not represent
that objective. Constants added at the ends can change which differences disappear.

The journey reproducer constructs actual `ToyEdge`/`ToyGraph` objects and calls `journeys` and
`evaluate`. Origin `(-1000, 1.26)` attaches halfway along `(-2000,0) → (0,0)`. Its connector is 1 s
and its entry partial contributes `(cost,time)=(1,1)`. Two distinct paths from node 0 merge at node 3:

| prefix after entry node | cost terms | time terms |
|---|---|---|
| P, via node 1 | `500, 500` | `500, 500` |
| Q, via node 2 | `500, 500.0000000000001` | `0.5, 0.5` |

The outgoing edge from `(200,0)` to `(2200,0)` has cost 2,000 and time 2. Destination `z` is at
`(1200,1.26)`: a halfway exit contributes cost 1,000/time 1, then its connector contributes 1 to
both totals. Destination `a` is at `(2200,0)`: full exit cost 2,000/time 2, connector 0. Thus the
destinations have different connector costs and the lexicographically smaller id belongs to the
more expensive destination.

The actual exhaustive journey oracle produces exactly four journeys:

| destination | via | complete cost | complete seconds |
|---|---|---:|---:|
| z | P | 2003 | 1004 |
| z | Q | 2003 | **5** |
| a | P | 3002 | 1004 |
| a | Q | 3002 | 5 |

The normative answer is `(2003, 5, z)`. An expanded query graph given to the spike's actual
`lexicographic` function returns `(2003, 1004, z)`. Combining connector and partial terms in that
expanded graph is exact in this example, so it introduces no rounding discrepancy. At an exact
600 s threshold this is **PASS → FAIL**, and `ceil(seconds/60)` is **1 → 17**.

**What survives:** different destination ids and different connector costs do not independently
invalidate an **exact-additive** pair-label search. Model origin entries as source arcs and each
destination exit/connector as its own terminal arc; compare terminal results by `(cost,time,id)`.
A better prefix at a shared node is available to every compatible continuation. Destination id is
a terminal comparison, not a reason to keep a separate numerical prefix for every destination.
The harness ran **500** expanded multi-entry, three-destination graphs with unequal connectors and
dyadic partial terms: **500 agree**, including destination id. Partial traversals can similarly be
formed once as entry/exit terms, and direct same-edge candidates must compete separately.

This confirms the graph transformation under its arithmetic assumptions. It does not rescue the
spike's use of exact-additive reasoning to narrow the actual rounded-total rule.

## B. Cost-only baseline — conditional claim confirmed, interpretation rejected

**Claim examined**, script lines 97–102:

> “This is the ordinary implementation and the subject of item 6”

**Runnable reproducer:** `review.py B`.

The unmodified spike was rerun with its default seed and 4,000 draws. Every emitted aggregate
matches the saved JSON: **3,267** reachable comparisons, **119** cost-only wrong-time results,
**0** wrong costs, **0** pair-label errors, **0** band errors, width **6**, and **162** counted ties.
The 119/3267 = **3.64%** is reproducible for *this equal-cost-dropping implementation and population*.

It is not an inherent failure rate of §2.4, or of all searches with one node label. A fair baseline
for the cheapest-then-fastest additive problem is the pair label already measured, which has
**0/3,267** numerical failures here. Arbitrary equal-cost dropping is admissible for cost-only
optimization; it is inadequate for the stated secondary time objective. Calling it the implementation
that item 6 indicts misses pass 37's distinguishing feature: its discarded prefix is **strictly more
expensive**, not merely tied. F1 shows that failure persists after the fair local time tie-break.

No separate severity is assigned to a correct conditional measurement. The claimed consequence for
the normative gate is refuted by F1, rather than by disputing the 119 observations.

## C. Soundness and implementation — F2, High; narrower theorem confirmed

**Claim refuted**, script line 20:

> “**exhaustive** — every simple path, ordered by `(cost, time)`. The normative answer.”

**Runnable reproducer:** `review.py C`.

`all_simple` uses `t + et, c + ec` at line 92. `lexicographic` uses the same repeated additions at
line 134. These disagree with the exactly-rounded, order-independent whole-journey summation in
§2.4 and with `toy._simple_paths`, which returns terms for the final `fsum`. The alleged oracle and
search therefore share an arithmetic defect. Positive small integers conceal it.

An explicit false agreement uses one three-edge path with costs `(2**53, 1, 1)`, time 3, and a
direct competitor with cost `2**53`, time 100. The spike's oracle and search both return
`(9007199254740992, 3)`. Whole-term summation gives the three-edge path cost
`9007199254740994`, so the normative answer is the direct path, **100 s**. Recomputing the chosen
path's cost exposes that its reported cost/time pair was not even that path's normative pair.
Repairing only the oracle is necessary for measurement; repairing only the final sum is insufficient
for pruning (F1).

The original pass 37 witness was also run against the new search, with individual terms retained
by the independent oracle:

| instance | minimum final cost | normative time | pair-label time |
|---|---:|---:|---:|
| original pass 37, suffix `2**54` | `18014398509481984` | 2 | 1001 |
| unit-scale cost diamond | 2 | 2 | 1001 |
| ordinary-scale cost diamond | 2000 | 2 | 1001 |

The last two exclude an explanation based on enormous cost weights. At ordinary scale the exact
prefix gap is **1/8796093022208**; at unit scale it is **1/4503599627370496**. Each is swallowed by
the final rounding bucket. Exact rational prefix accumulation still prefers P and discards Q.

**Cycle-removal reasoning:** removal of a nonnegative cycle proves that a numeric optimum has a
node-simple representative. It does not prove that a locally worse pair remains worse after
completion. In exact-additive arithmetic, pair order *is* preserved by adding a common pair. That
property plus nonnegative cycle removal gives a proof for the narrower additive problem, including
zero edges/cycles. With rounded complete costs, strict cost order can collapse into a tie and reverse
pair order on time. Nonnegativity remains true; the needed prefix-order property does not.

**Stale-label check survives.** The actual `(c,t) != best.get(node)` predicate was instrumented
alongside the original function. A strict improvement enqueues the new pair; stale entries can be
discarded. Every nonnegative extension is at least its parent pair, so a heap that pops the least
current pair cannot later discover a smaller pair for an already popped node through these retained
states. This is distinct from discarding a prefix the objective needed. Observed **4,315** stale
skips and **0** improvements after a valid pop. An explicit zero-cost/zero-time cycle terminates and
returns the correct `(0,1)` optimum.

Additional whole-term-oracle stress, seed 41003, 120 attempts per family:

| family | nodes / extra arcs | compared | wrong cost | right cost, wrong time |
|---|---|---:|---:|---:|
| zero/one weights | 9 / 35 | 119 | 0 | 0 |
| zero/small weights | 12 / 25 | 118 | 0 | 0 |
| dense, weights 0–7 | 9 / 60 | 120 | 0 | 0 |
| wide integer weights 0–999999 | 12 / 25 | 118 | 0 | 0 |
| strongly anticorrelated, `time=1024-cost` | 10 / 35 | 120 | 0 | 0 |
| dyadic weights in eighths | 12 / 25 | 120 | 0 | 0 |
| continuous binary64 weights | 12 / 25 | 118 | **6** | **8** |
| larger directed acyclic graphs | 30 / 70 | 119 | 0 | 0 |

Of 960 attempts, **952** were compared, **7** were unreachable and **1** exceeded the explicitly
retained 400,000-path cap. The largest completed enumeration had **304,868** paths. All **834**
exactly additive integer/dyadic comparisons agree. Continuous-population discrepancies include
accumulation errors in reported totals; they are not asserted to be 14 distinct wrong-route choices.
The explicit diamonds above independently establish wrong-route and verdict changes.

## D. Residual — F3, Medium; F4, Medium; order claim qualified

### F3: enumerated multiplicity is not distinct route identity

**Claim refuted**, script lines 206–211 and saved JSON:

> “paths tying on BOTH cost and time, which only the route key separates”

`graphs_where_only_the_route_key_separates_the_winners = 162`.

**Runnable reproducer:** `review.py D`.

The generator admits parallel/duplicate arcs. `all_simple` records only the node sequence, and the
residual tests `len(tied) > 1`, not the number of distinct identities. The replay finds:

| quantity in the original 3,267 comparisons | count | rate |
|---|---:|---:|
| counted multiple winners | 162 | 4.96% |
| multiple **distinct node sequences** | **23** | **0.7040%** |
| duplicate-only counted ties | **139** | 4.2547% |
| actual pair-label route disagreement with the spike's own ordered oracle | **14** | **0.4285%** |

Minimal witness: two identical `0 → 1` arcs, each cost/time 1. The spike enumerates the same route
twice. Lift them to two identical real `ToyEdge` records: all journey rank keys remain identical.
The route key separates **nothing**. Thus 4.96% is neither an identified distinct-route tie rate nor
an observed provenance-error rate. The 23 is a correction in the spike's **node-sequence model**,
not a claim about arbitrary real parallel geometries: the experiment supplies no geometry/osmid
identities with which to estimate their canonical-route rate.

**The abstract sequence-order claim survives**, with scope. `(1,) < (1,2)`, but after appending
`(3,)`, `(1,3) > (1,2,3)`. However, two node-simple prefixes from the **same root to the same merge**
cannot be proper prefixes of each other: the longer would revisit the merge. Their first differing
edge determines the same order after a common suffix. The abstract example alone is insufficient
to prove the claimed impossibility for that restricted graph search.

There is also a concrete journey-level reversal in the committed oracle. At `(0,0)`, a zero-weight
closed edge `(0,0),(100,0),(0,0),(-100,0),(0,0)` supplies multiple entry occurrences, including an
interior halfway occurrence and an endpoint occurrence. Both reach node 0 with pair `(0,0)`, with
route prefixes `[loop]` and `[]`. Complete with edge `0 → 1`: `[] < [loop]` but
`[exit] > [loop,exit]`, since the loop identity starts `(0,0)` and exit starts `(0,1)`. Both routes
are enumerated by `toy.journeys`; the intervening node path is simple. The oracle chooses
`[loop,exit]`. This confirms a real variable-entry case rather than relying only on abstract strings.

**“No single-label search closes” is too broad as an algorithmic conclusion.** For the exact-additive
internal graph, numerical labels can be followed by canonical reconstruction on tight optimal edges:
choose the least next identity admitting a continuation without a visited node. Reachability checks
handle zero cycles. The included prototype agrees with exhaustive route selection on **261**
reachable zero/one-weight graphs out of 300 attempts. It is a reconstruction procedure, not evidence
that adding a route tuple to every forward label solves all journey cases. Nor does it repair F1's
rounded numerical objective. It shows why tie multiplicity alone is not an impossibility proof.

### F4: “not a wrong reported number” exceeds the surviving guarantee

**Claim refuted**, script lines 36–38:

> “That is a **provenance** ambiguity against §12's manifest requirement, not a wrong reported
> number”

**Runnable reproducer:** `review.py D`; the two targeted existing invariant tests also pass.

The narrow statement that **equal total cost and equal total time do not change those totals**
survives. The broader classification does not survive consumers of the selected geometry. The
reproducer creates upper and lower diamond routes with cost/time terms `(2,0)` and `(1,1)`
respectively. Both have totals `(2,2)`. The actual pair-label search chooses the lower route;
the actual journey oracle chooses the lexicographically smaller upper route. For a declared
boundary band `y >= 0`, the selected route's length share in the band is **100%** for
the upper route and **0%** for the lower route. Persisting different route references in §12's
bundle can therefore change a geometry-consuming diagnostic such as T10. This is a concrete
diagnostic example, not a claim to have run a currently specified production T10 implementation.

Further, **route tie is not the only residual**. Destination id precedes route identity: the harness
shows id `a` wins over `z` even when `z` has the smaller route. This is easy terminal tie handling,
but it is absent from the one-goal residual measurement. And even a correctly selected route
identity does not determine traversal intervals or network/connector decomposition. One self-crossing
zero-weight edge, one origin `(25,0)`, and one destination `(75,0)` produce **three** tied traversals
of **50, 450, and 50 m** with one complete rank key. The existing decomposition invariant confirms
equal ranked totals can leave network seconds **1.0 versus 0.9968253968355556**.

The design already states these limits at lines 672–690 and 718–738, and already prohibits treating
T10 as reproducible before its own reconstruction specification exists. This finding attacks the
spike's unqualified dismissal; it does not claim that the design has already published a wrong T10
number. Persist the chosen reconstruction or sufficient diagnostic statistics as §12 requires.

## E. Population — conditional qualification survives; gate evidence does not

**Runnable reproducer:** `review.py E`, seed 41005, 2,000 attempts per population.

For direct comparison with the advertised statistic, the first rate below uses the spike's own
oracle; the second uses whole-term summation. Keeping these separate prevents arithmetic errors
from being mislabeled as equal-cost tie-selection failures.

| population | compared | spike-oracle wrong-time count/rate | whole-term-oracle count/rate |
|---|---:|---:|---:|
| all positive weights 1 | 1636 | 0 / 0% | 0 / 0% |
| weights 1–3 | 1635 | 73 / **4.4648%** | 73 / 4.4648% |
| weights 1–9999 | 1647 | 0 / 0% | 0 / 0% |
| continuous binary64 weights in [0,4) | 1629 | 0 / 0% | 66 / **4.0516%** |

Continuous weights have no distinct optimal-route ties in this run; the last column exposes
accumulation discrepancies instead. These figures are population-dependent, not Triangle estimates.
The original generator also samples **strictly positive integers**, despite zero weights/cycles
being admissible; the separate C tests address that omitted regime.

**No transfer of 3.64% to the Triangle graph was found in the reviewed plan/design.** The saved JSON
and script explicitly identify the synthetic tie-rich population. The plan's 4b.0 section still
describes strictly more expensive prefixes rejoining a rounded tie and calls for realistic weights;
§12 item 6 still says the real-graph rate is unmeasured. Those statements survive. The script's
qualification is adequate for describing its synthetic baseline statistic, but cannot license
narrowing a gate whose motivating event this positive-small-integer population does not exercise.

## F. Recommendation — F5, Medium; retain the gate

**Claim refuted**, script lines 24–25:

> “**band** — every *cost-minimal* label per node retained, time deciding at the end. The plan's
> first repair, measured so it can be priced rather than preferred.”

**Runnable reproducer:** `review.py F`.

The plan at lines 251–252 proposes a **neighbourhood** sized from a reachable suffix ulp, which can
retain a strictly more expensive prefix. The spike drops it at line 156. An all-exact-cost-minimal
set is not that band and cannot cover F1.

The actual implementation also processes a LIFO queue without invalidating older, costlier queued
labels. They can propagate before later cheaper prefixes are found. On the ordinary-scale diamond,
merely reversing the input edge list gives:

| edge order | normative time | spike band time | maximum observed label set |
|---|---:|---:|---:|
| original | 2 | **2** | 2 |
| reversed | 2 | **1001** | 1 |

The apparently successful first order propagates the costlier Q before P replaces it at the merge;
its descendant remains in the final rounded cost tie. Reversing exploration discovers P first and
prunes Q. This is not a conforming, measured implementation of the proposed suffix-aware band.
The observed width 6 on a different population cannot price that proposed repair.

The plan's other proposed amendment, “make whole-journey cost accumulation edge-by-edge so the
label *is* the cost,” also needs a stronger specification before it can repair the full ranking.
On this same diamond even the spike's own **left-accumulating oracle** selects 2 s, while the
pair-label search selects 1,001 s. Changing only accumulation order still lets a strict prefix-cost
gap round into a final tie. An amendment must settle the secondary time rule too, or use a genuinely
exact-additive primary ordering; edge-by-edge binary64 cost alone does not establish pair dominance.
This is another consequence of F1, not a separate severity count.

**Recommendation:** do not collapse the three options to “pair labels for numbers, route identity
later.” Pair labels are a sound improvement for exact local ties and a useful baseline, but F1
leaves the numerical gap open. Measure against a term-preserving journey oracle, include the
original strict-prefix witness and ordinary-scale variants, and either implement justified
near-optimal-label retention, explicitly accept and measure a gap, or make a semantic amendment.
Route/destination reconstruction and T10's independent traversal requirement remain additional work.

There is a **fourth option**: compute the minimum exact additive cost of the **formed binary64
terms**, identify its minimum rounded-cost bucket, then enumerate cost-ordered node-simple
alternatives only while their complete exact costs round into that bucket. Rank those finalists by
the actual whole-journey `(cost,time,destination_id,route)` key. Monotonic rounding justifies stopping
above the bucket. This preserves the rule and can be implemented lazily or with certified pruning;
it may still be exponentially expensive. This is exact summation of the declared terms, not a switch
to the real-geometry estimand in §12 item 5.

The included finite prototype sorts exhaustive alternatives by their exact rational term sums and
validates that stopping rule: **2 finalists**, selected `(2000,2,(0,2,3,4))`, the normative answer.
It demonstrates a distinct staged search option, **not** a scalability result. For exact-additive
route identity alone, the tight-edge reconstruction in D is another staged approach. Neither
experiment supports claiming a free general one-label implementation of §2.4 as currently written.
