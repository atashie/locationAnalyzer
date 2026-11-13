# S3 decision report — walk to a grocery, Triangle, 100 m grid

**2026-11-13, rewritten the same day after Codex pass 46.** For one decision: whether to put this
in front of a bounded set of households. Every number links to the measurement behind it.

> **The first version of this report said real-world accuracy was "UNVERIFIED, the owner's call".
> That was wrong by this project's own rule.** `locfinder/measure/e3.py` is the predeclared scorer,
> and on the evidence we have it returns **FAILED**. One observation cannot establish a rate, but
> the scorer was deliberately built so that one observation *can* establish failure — that is
> §S3.4's honesty mechanism, and the first draft bypassed it.

## The verdict, in the scorer's own words

```
score_e3([Journey("band15min_pass-03", reported=810.8186, walked=1500)])
  -> FAILED
     observed 1500 s against 811 s reported - 1.85x and 11.5 min over,
       past both 1.5x and 5 min
     median signed difference 11.49 min exceeds 25% of the median reported
       time (3.38 min)
```

**The observation is approximate and the verdict is robust to that.** The owner recorded "~25
minutes", and a hard-edged scorer fed an approximate number needs its sensitivity stated: the
outcome flips to `FAILED` at **16.9 minutes** and stays there above it. It would take the real walk
being under 17 minutes — a third less than what was recorded — to return `UNVERIFIED`. The
reproducer sweeps 14 to 30 minutes.

So of §S3.4's three outcomes:

| outcome | status |
|---|---|
| **Construction fidelity** | partly evidenced — no reference comparator exists (T3 is gated on design §12 item 6) |
| **Engine disagreement** | **not measured** in this release. No magnitude is reported here |
| **Real-world accuracy** | **FAILED** on one walked journey, by the predeclared rule |

## What the product answers

For each 100 m cell in the Triangle, the walking time to **the grocery the routing cost rule
selects** — not the nearest by walking time. Those differ: with costs `(700, 650)` and times
`(500, 650)`, the rule selects the 650-second journey and reports 650 seconds while a 500-second
walk exists. The published number is a whole-minute rounding of the **modelled journey from the
cell centre**; it is not an upper bound on the household's real walk, and the FAILED verdict above
is one measured instance of it being an underestimate.

Scope is **walk / grocery / Triangle only**. Drive, bike and transit have no layer at this extent.

## What is established

| | |
|---|---|
| **The grid decision** | Keep 100 m. The 200 m candidate roughly doubles the rate at which the published cell answer differs from the answer at the structure's own coordinate — 4.38% against 2.52% at 15 minutes, over 512,633 structures. [s3-1](experiments/s3-1-candidate-grids.md) |
| **The encoding** | `published-v2`: two uint8 planes. The decoder reproduces `status.evaluate` **cell for cell** on all 330,502 cells at ten thresholds, and the browser's JavaScript reproduces the Python — 37 conformance cases, 13 mutations all caught. Costs 18.2% more bytes. [s3-5](experiments/s3-5-browser-path.md) |
| **Three outcomes reach the browser** | 18,648 cells the pipeline can *prove* are over the threshold used to arrive as "unknown", and a known failure in one layer could be overridden by an unknown in another. Both fixed. |
| **Attachment prevalence** | Conventions **A, C and D** measured by census over **843,685** points; eligibility invariant on every point measured. **B is not implemented.** The choice between them is open on verdict impact, which needs the comparator. [t0](experiments/t0-attachment-pilot.md) |

## The known optimistic bias, and who is exposed

The walked journey took a private track that wins on cost. Measured over the **published cell each
structure falls in** — the answer the product would actually give that household:

| *T* | structures included | of those, route uses a restricted way |
|---|---|---|
| 10 min | 80,067 | **7,271 (9.1%)** |
| 15 min | 163,875 | 15,294 (9.3%) |
| 25 min | 298,716 | 30,971 (10.4%) |
| 45 min | 424,886 | 47,236 (11.1%) |

About one in eleven of the **structures** the product includes — this is a structure count, not a
household count, and frame B is a frame of structures.

**These are candidate disclosures, not deliverable ones.** They are the *source grid's* figures;
the browser receives a WGS84 re-tiling and MapLibre places it in Mercator, each moving the lookup
again. And **no flag plane is shipped**, so no household can currently be told any of this.
[s3-8](experiments/s3-8-restricted-routes.json)

The statistic the owner's 2026-11-10 decision owes is the **signed error on restricted-route
journeys**. This supplies the denominator and leaves the numerator empty: one journey, in the
optimistic direction.

## What else is not established

**The destination list is screened, not validated.** Nine records carry a closure flag and **must
not be filtered on current evidence** — four sit within 150 m of an open destination we already
publish. 1,473 structures at ten minutes depend on one of those records. Separately **Target,
Costco, Sam's Club and BJ's are not destinations at all**, and Walmart is split by format.
[s3-7](experiments/s3-7-destination-truth.md)

**The shipped raster is not the measured grid**: a WGS84 re-tiling moves 2.42% of structures at
fifteen minutes and omits 12,182; MapLibre's placement shifts 131,571 by one row (analytical, not a
screenshot).

**E1c has no interval method chosen**, so the conditional estimand is specified and not computed.

**The geocoding audit is unstarted** — whether a household's address resolves to the right cell.

## Release prerequisites, which are longer than "publish the flag"

None of the three things a household is owed can be delivered today:

1. **The restricted-route flag** — computed, not persisted in the layer bundle. Adding it is a
   wire-format change.
2. **The destination the time was measured to** — not persisted either, and a destination *node*
   does not identify a shop: 550 places snap to 510 nodes and 75 share one, so presenting an
   identity needs a rule that does not exist yet.
3. **Which criterion was unknown, and why** — the per-criterion card is unbuilt.

Also outstanding: **phone decode latency is unmeasured** (it needs a device), the
**recomputation-eligibility UI** is absent although the format carries what it needs, and the
browser implementation discussed above is **`v2/spikes/g3-render`, a spike** — not an identified
household product.

## A proposed ordering, not a measured one

No comparative error rates or return-per-hour figures exist, so this is a judgement about where to
look next, not a finding:

1. **More walked journeys, aimed at restricted routes** — the only check that consults the world,
   pointed at the ~9% most likely to be wrong and in the one direction already observed. It is also
   the only thing that can move the FAILED verdict.
2. **The grocery definition decision** — moves 3,912 structures at ten minutes and is currently
   arbitrary at the branch level.
3. **28 candidate destinations and 4 masked identities** checked by someone who can look.
