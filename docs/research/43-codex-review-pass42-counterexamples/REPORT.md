**The recommendation in §I is wrong as written.** A travel-time threshold is not a safe cost ceiling, and the second band has an unmeasured exponential price even when every cost is positive and the precondition holds. I found no counterexample to the finite rounding-interval lemma itself.

The reviewed files match `e0c699c`; the current checkout adds the review prompt. All 11 targeted fixtures passed, and both published sweeps and the 363-graph zero-cycle results reproduced exactly. I skipped the full suite. Testing used an explicit external `--basetemp`, disabled temporary-file capture, and created no repository temporary directories.

For the Python reproducers below, run from the repository root using:

```powershell
@'
# Paste one complete Python block here.
'@ | .\v2\.venv\Scripts\python.exe -B -
```

1. **High — sizing from the query’s travel-time threshold changes PASS to FAIL.**

   Locations: [comparator plan:339](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/plans/2026-11-11-step4-comparator-plan.md:339), [recommendation:349](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/plans/2026-11-11-step4-comparator-plan.md:349), [implementation:352](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/spike_suffix_band.py:352).

   A threshold on reported time does not bound the primary cost. The spike tests its “query ceiling” using the **oracle’s winning cost**, which does not establish that the actual query threshold is usable.

   This scales only the witness’s costs, leaving its times unchanged:

   ```python
   import sys
   from dataclasses import replace
   sys.path.insert(0, "v2/scripts")
   import spike_suffix_band as b
   from locfinder.measure import toy

   g, o, ds, ids = b.witness_graph()
   g = toy.ToyGraph(tuple(
       replace(e, cost_base=16 * e.cost_base, penalty=16 * e.penalty)
       for e in g.edges
   ))
   oracle = b.oracle_answer(g, o, ds, ids)
   normal = b.band_answer(g, o, ds, ids, both_bands=True)
   threshold = b.band_answer(g, o, ds, ids, both_bands=True,
                             cost_ceiling=600.0)
   for name, ans in [("oracle", oracle), ("default", normal),
                     ("threshold", threshold)]:
       print(name, ans["cost"], ans["time_s"])
   print("precondition:", threshold["precondition"]["holds"])
   ```

   Output:

   ```text
   oracle    32018.0 5.0
   default   32018.0 5.0
   threshold 32018.0 1004.0
   precondition: True
   ```

   **Cost:** PASS becomes FAIL at 600 seconds.

   This does not refute the restricted `cost_ceiling` contract when the caller supplies a valid bound. It refutes the recommendation to use the query’s threshold without establishing that it bounds primary cost. Require a valid cost bound—potentially obtained from a feasible candidate—or retain the graph bound.

2. **High — finite, admissible graphs overflow the bound calculation.**

   Locations: [_ceiling:174](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/spike_suffix_band.py:174), [band_widths:192](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/spike_suffix_band.py:192).

   The graph constructor accepts these one-way graphs, and the exhaustive oracle answers them. The band raises before returning even the already-created same-edge direct candidate.

   ```python
   import sys
   sys.path.insert(0, "v2/scripts")
   import spike_suffix_band as b
   from locfinder.measure import toy

   for cost in [3e307, 7e307]:
       g = toy.ToyGraph((
           toy.ToyEdge(0, 1, ((0., 0.), (1000., 0.)),
                       time_s=1., cost_base=cost, oneway=True),
       ))
       args = (g, (0., 0.), [(1000., 0.)], ["a"])
       print("oracle:", b.oracle_answer(*args)["cost"])
       try:
           print("band:", b.band_answer(*args, both_bands=True)["cost"])
       except OverflowError as exc:
           print(type(exc).__name__, str(exc))
   ```

   Output:

   ```text
   oracle: 3e+307
   OverflowError cannot convert Infinity to integer ratio
   oracle: 7e+307
   OverflowError intermediate overflow in fsum
   ```

   At `3e307`, doubling the loose bound produces infinity; `F(width)` then raises. At `7e307`, the artificial `_ceiling` sum itself overflows.

   **Cost:** an answerable query produces no answer. Finite journey totals do not imply finite intermediate *bounds*. Bound construction needs explicit overflow handling.

   Your third self-correction also has an incorrect rationale. For a finite binary64 bound `B ≥ sigma(v) + S`:

   ```text
   rnd(sigma(v) + S) ≤ B
   ```

   If a costlier prefix ties that rounded result `T`, its gap is at most:

   ```text
   ulp(T) ≤ ulp(B)
   ```

   This argument does **not** require bounding the costlier prefix’s completed total independently. Thus the stated “retained label pushes past the bound” argument does not demonstrate that the old width was too narrow. Doubling is conservative in the finite regime, but its necessity should be withdrawn; its overflow consequence is real.

3. **High — the two-band price is exponential even with exactly equal costs.**

   Locations: [second-pass key:233](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/spike_suffix_band.py:233), [report’s price claims:69](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/suffix-band.md:69), [claimed bound:86](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/suffix-band.md:86), [design’s “never … tie exactly”:2131](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/plans/2026-11-04-s3-measurement-design.md:2131).

   Give every diamond arm exactly the same cost, but independently distinguish its time by a small binary fraction. All `2**k` exact times fit inside the time band. Pass two retains them separately.

   ```python
   import sys
   from dataclasses import replace
   sys.path.insert(0, "v2/scripts")
   import spike_suffix_band as b
   from locfinder.measure import toy

   for k in [8, 12, 16]:
       g, o, ds, ids = b.diamond_chain(k)
       edges = []
       for j, e in enumerate(g.edges):
           if 1 <= j <= 4 * k:
               i, arm = divmod(j - 1, 4)
               e = replace(e, cost_base=1.,
                           time_s=2.**-20 +
                           (2.**(-45-i) if arm == 3 else 0.))
           if j == len(g.edges) - 1:
               e = replace(e, time_s=4000.)
           edges.append(e)
       g = toy.ToyGraph(tuple(edges))
       one = b.band_answer(g, o, ds, ids)
       print(k, "one:", one["labels_retained"],
             "precondition:", one["precondition"]["holds"])
       try:
           two = b.band_answer(g, o, ds, ids, both_bands=True)
           print("two:", two["labels_retained"])
       except b.LabelExplosion as exc:
           print(type(exc).__name__, str(exc))
   ```

   The family retains `5 * 2**k - 3` second-pass labels while they fit under the cap:

   | Diamonds | One band | Two bands |
   |---:|---:|---:|
   | 8 | 26 | 1,277 |
   | 12 | 38 | 20,477 |
   | 16 | 50 | exceeds default 200,000 cap |

   Every edge cost and time is positive. The graph is acyclic and the reported precondition holds.

   **Cost:** the proposed route repair can turn a 50-label search into `LabelExplosion`. The statements that exact cost ties add nothing, and that `W/g` bounds the two-band retained count, must be withdrawn.

   For one band, the inclusive interval gives `floor(W/g) + 1`, not `W/g`. For two bands, distinct times within each cost bucket also matter. The published chain conceals this by producing only `k + 1` cost buckets with identical time for each bucket.

   Related reporting corrections:

   - The reported “max” is the maximum **graph-average** label count, not maximum labels at a node. The original witness averages 1.4 but has a node retaining 2.
   - The plan still says capacity **8,192** at line 335; the artifact says **16,384**.
   - “Free” establishes retained-label counts on these small draws. It establishes neither runtime nor memory equivalence to scalar search.

4. **Medium — item 6 cannot stand “exactly as written.”**

   Locations: [design:2101](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/plans/2026-11-04-s3-measurement-design.md:2101), [design:2147](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/plans/2026-11-04-s3-measurement-design.md:2147), [report:145](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/suffix-band.md:145), [actual pruning:227](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/spike_suffix_band.py:227).

   The band is a prefix-pruning search. It uses a suffix-dependent threshold to decide which prefixes to prune. Retaining some strictly costlier prefixes does not change that classification.

   ```python
   import sys
   from fractions import Fraction as F
   sys.path.insert(0, "v2/scripts")
   import spike_suffix_band as b

   arcs = {0: [(1, F(1), F(1), (0, 1)),
               (1, F(2), F(2), (0, 1))]}
   starts = [b.Terminal(0, F(0), F(0), ())]
   sigma = b.exact_min_costs(arcs, starts)
   labels, _ = b.band_labels(arcs, starts, sigma,
                             {0: 1e-12, 1: 1e-12}, cap=10)
   print(list(labels[1]))
   ```

   Output: `[Fraction(1, 1)]`. The cost-2 prefix was pruned.

   **Cost:** the universal impossibility claim must be restated. A defensible version concerns keeping only one best prefix, or pruning without sufficient information about possible suffix rounding.

5. **Low — the advertised exact-total verification mode does not exist.**

   Locations: [script:42](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/spike_suffix_band.py:42), [Candidate docstring:96](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/spike_suffix_band.py:96), [exactness test:115](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/tests/test_suffix_band.py:115).

   Runnable reproducer:

   ```powershell
   .\v2\.venv\Scripts\python.exe -B v2/scripts/spike_suffix_band.py --verify-totals
   ```

   It exits with `unrecognized arguments: --verify-totals`.

   The named test checks finite oracle totals and membership of the winning answer. It does not reconstruct and compare exact sums for every journey.

   **Cost:** withdraw the claim that this verification mode checks the equality, or implement it. I found no arithmetic disagreement: independently reconstructing 44 journey totals and testing another 10,000 mixed-magnitude nonnegative term lists matched `float(Fraction sum)` against `fsum`.

What I checked and could **not** break:

- **A, finite rounding:** the interval-width bound survives subnormals, half-even endpoints, and asymmetric power-of-two intervals. At a normal power of two, the interval is only `0.75 * ulp(T)` wide. The finite implementation failure is overflowing the bound, not an interval wider than `ulp(T)`.
- **A, suffix coverage:** `_ceiling` is conservative for a node-simple network suffix plus its terminal. Out-and-back partial traversals are covered. Same-edge direct candidates use their own exact totals and bypass band retention.
- **B, numerical dominance:** at fixed exact cost, smaller exact prefix time cannot produce larger reported time after adding the same suffix. I found no numerical counterexample under a valid finite cost bound.
- **B/C, normative route:** I found no returned wrong route when the stated sufficient precondition holds and the search completes. The hand-built route witness does demonstrate the one-band miss and its repair: 5 labels become 7.
- **D, heap ordering:** with the declared integer node IDs and canonical identity structure, different route lengths and heterogeneous *fields* do not themselves cause incompatible comparisons. Appending an identity increases a route tuple.
- **E, permutations:** this is a real check, though narrow. Shuffling changes arc insertion and scheduling. The reproduced control gives two answers while the band gives one; index-free identities appropriately keep the requested identity stable.
- **F, sufficient check:** if every edge cost exceeds the widest band, every cycle does too. I could not construct a zero-cost cycle that changes a returned numerical optimum under nonnegative times. Removing a cycle cannot increase either exact objective.
- **G, term formation:** connector grouping is exact; same-edge direct costs and `_partial_route` agree with the oracle’s construction.

Positive costs **alone** do not establish route agreement with the node-simple oracle. For example, a two-way edge costing `2**-46` per traversal, with zero time, before a 1,000-cost suffix lets the band select a cyclic route whose reported totals tie the simple route. I reproduced an unformable winner containing two out-and-back cycles. Its precondition correctly reports false. Likewise, a zero-cost edge with tiny **positive** time can produce an unformable second-band winner. Your sampled zero-cycle edges always have **zero time**, so those 363 graphs do not exercise that case. Neither example changed a reported number.

Finally, your first two self-checks hold:

- Replacing the heap with the documented LIFO worklist in memory reproduced **655,354 versus 884 expansions**, with **identical retained dictionaries** and 442 final labels.
- A sub-width cycle does not imply an infinite retained set. The replacement explanation correctly identifies route semantics as the concern; the positive-time cases above add a formability failure beyond the measured population.

The evidence supports continuing with the band as a candidate. It does not yet support adopting it with the current threshold advice and price claims.

Codex session ID: 01a1d507-3ba8-7d70-be85-d92229cf32fd
Resume in Codex: codex resume 01a1d507-3ba8-7d70-be85-d92229cf32fd
