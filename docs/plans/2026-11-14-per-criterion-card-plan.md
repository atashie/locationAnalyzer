# The per-criterion card — plan

**2026-11-14.** The next planned step for S3. This is the plan; it has not been executed.

Ordering follows `docs/plans/2026-11-04-s3-execution-plan.md` §0: **product risk retired, not
defect severity.** That is what chooses this over another Codex pass on the pass 50 repairs, even
though passes 49 and 50 both found more in the repairs than in the work they repaired. Those
findings are *defect* risk in code no household has ever seen. The card is the only thing standing
between all three owed disclosures and a person actually being told anything.

## Why this one piece unblocks all three

`docs/s3-decision-report.md` names three things a household is owed. Their state:

| owed | data | interface |
|---|---|---|
| the restricted-route flag | done, `5e5118f` | not shown |
| the destination the time was measured to | done, `4685158` + pass 49/50 repairs | not shown |
| which criterion was unknown, and why | **not computed as an answer** | not shown |

The third is not merely unshown. **The worker computes per-layer outcomes and keeps none of them.**
`handleCompute` evaluates `outcomeOf(...)` per layer per cell inside its loop, folds the results
into `anyFail`/`anyUnknown`, writes one combined verdict, and discards the detail. There are six
message types — `init`, `compute`, `recycle`, `mask`, `verdicts`, `destinationAt` — and not one of
them can say *which* criterion was unknown at a cell, or why.

So the card is not three features. It is **one new worker message plus one presentation surface**,
because all three questions are the same question asked of one cell: *what did each criterion say
about this place, and what does it decline to say?*

## The shape

### 1. `explainAt(row, col)` — the worker message the card needs

One reply, per **enabled** layer, with every field optional in the sense the format already
means: absent is *this layer does not disclose*, never *there is nothing to disclose*.

```
{ type: 'explainAt', reqId, seq, row, col,
  outside?: true, invalidCoordinates?: true, notComputed?: true,
  verdict: 0 | 1 | 2 | null,          // the combined answer, null before a compute
  criteria: [                          // one entry per ENABLED layer, in manifest order
    { layer, outcome,                  // PASS | FAIL | UNKNOWN -- the three-outcome algebra
      status,                          // the wire status code, so the card can say WHY
      value, valueIsLowerBound,        // minutes, or a bound where the status says so
      thresholdMin,                    // what it was compared against
      horizonS,                        // what BEYOND_HORIZON was measured against
      routeFlag: 0 | 1 | null,         // null = this layer does not disclose
      namesDestination: [...] | null } // null = this layer does not say
  ] | null }
```

Three constraints carried over, each already paid for:

* **`null` is not `[]` and not `0`.** The whole optionality discipline. `criteria: null` before a
  compute, `routeFlag: null` where the layer does not disclose.
* **It answers for any cell, included or not.** `destinationAt` answers only where the verdict
  passes, because a destination beside an excluded cell is "not applicable". But *why* a cell is
  excluded is exactly what the card exists to say, so `explainAt` must answer where
  `destinationAt` declines — and then **not** name a destination there.
* **A disclosure must not be able to move an eligibility answer.** Pass 48's F1. `explainAt` reads
  state and computes nothing; `outcomeOf` keeps its current signature, which cannot see the flag.

Open question for the step itself: recompute the per-layer outcome on demand in `explainAt`, or
keep a per-layer outcome plane from the last compute? **Recompute**, on current evidence — one
cell is free, and a stored plane is `layers × cells` bytes plus a second thing that can drift from
the verdict it is supposed to explain. The cost is that `explainAt` must reproduce the compute's
decision exactly, so the test is: for every cell in a fixture, the outcomes `explainAt` reports
must fold to the verdict `compute` wrote. That is a cheap, total check and it is the one that
matters.

### 2. The card

Minimum that discharges the three disclosures, and nothing more:

* Per criterion: the time or the bound, the threshold, and the outcome in words.
* Where the outcome is UNKNOWN: **the reason**, from the status code — off the network, beyond the
  horizon, no path, the layer does not know. "We cannot tell you" with a cause.
* Where a route is flagged: that the route uses a restricted way. Where the layer does not
  disclose: nothing at all, not "no restrictions".
* The destination: **the node plus the set, and the card chooses** (the owner's rule, 2026-11-13).
  Where the set has more than one place — 5.6% of answered cells — it may say "one of 3 at this
  corner". It may **not** present a pick as ours.

### 3. Tests, as the existing shape demands

* Conformance vectors gain `explain_at` cases beside `destination_at`, generated by
  `make_wire_vectors.py`, replayed through the real worker.
* The total check above: outcomes fold to the verdict, every cell, every fixture.
* Refusal cases: `explainAt` before a compute; a non-integer coordinate; a layer that does not
  disclose reporting `null` and not `0`; an excluded cell naming no destination.
* Mutations for each: collapse `null` to `0`, let a flag reach `outcomeOf`, report the combined
  verdict as a per-criterion outcome, name a destination at an excluded cell.
* The **oracle must not be reachable by the code under test** — ledger 34. Freeze expectations
  before init, as the destination comparison now does.

## Steps, in order

1. `explainAt` in `worker.js`, with the lifecycle and coordinate guards the other readers now have.
2. The fold check: outcomes to verdict, every cell of every fixture.
3. Vectors and conformance cases; mutations for each new guard.
4. The card surface in `app.js`, reading `explainAt` for the hovered cell.
5. Measure what it costs on the real bundle: one `explainAt` per pointer move is not free.
6. Codex pass on the result.

## What this plan does not do

* **It does not resolve which place on a shared node.** Deliberately. That needs an invented rule
  or a finer routing target than a node, and both are the owner's call.
* **It does not publish anything new.** No wire format change, no new artifact; `published-v4` is
  unchanged. The card reads what is already shipped.
* **It does not clear the Apache records for redistribution.** That is now an owner-owed decision
  in its own right — see the progress note.
