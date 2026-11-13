# S3 decision report — walk to a grocery, Triangle, 100 m grid

**2026-11-13.** One page, for one decision: whether to put this in front of a bounded set of
households. Every number below links to the measurement that produced it. **Nothing here grants
the accuracy claim** — §S3.4 reserves that, and this report says plainly that it is unverified.

## What the product answers

For each 100 m cell in the Triangle, the walking time to the nearest qualifying grocery, published
as whole minutes and read as a PASS / FAIL / UNKNOWN verdict at a threshold the household picks.
Scope is **walk / grocery / Triangle only** — drive, bike and transit have no layer at this extent
and the verdict does not generalise to them.

## What is established

| | |
|---|---|
| **The grid decision** | Keep 100 m. The 200 m candidate roughly doubles the rate at which the published cell answer differs from the answer at the structure's own coordinate — 4.38% against 2.52% at 15 minutes, over all 512,633 structures. [s3-1](experiments/s3-1-candidate-grids.md) |
| **The encoding** | `published-v2`: two uint8 planes, minutes and a status code. The decoder reproduces `status.evaluate` **cell for cell** on all 330,502 cells at ten thresholds, and the browser's JavaScript reproduces the Python, checked by 37 conformance cases and 13 mutations. Costs 18.2% more bytes (31 KB). [s3-5](experiments/s3-5-browser-path.md) |
| **Three outcomes reach the browser** | Previously 18,648 cells that the pipeline can **prove** are over the threshold arrived as "unknown", and a known failure in one layer could be overridden by an unknown in another. Both fixed. |
| **Attachment prevalence** | A/B/C/D's *prevalence* measured by census over 844,685 points, and eligibility is invariant on every point measured. The **choice between them is still open**: the pre-registered rule makes it open on verdict impact, and that stage needs the comparator. [t0](experiments/t0-attachment-pilot.md) |

## What is not established, and must be said out loud

**Real-world accuracy is UNVERIFIED.** One walked journey exists. It found **≈25 minutes against a
published 13.5** — the route took a private track that wins on cost. One journey is existence
evidence, not a rate.

**The direction of that bias is optimistic, and about one household in ten is exposed.** The
estimate's route depends on a restricted way for **8,033 of the 78,627 structures** included at ten
minutes (10.2%), and 16,871 of 162,699 at fifteen (10.4%). Those households must be told. The flag
is computed per cell and per structure; it is **not yet published in the layer bundle**.
[s3-8](experiments/s3-8-restricted-routes.json)

**The destination list has not been validated** — only screened. Nine records carry a closure flag
and **must not be filtered on current evidence** (four sit within 150 m of an open destination we
already publish; the Kroger site is an operating Harris Teeter already in the list). 1,473
structures at ten minutes depend on one of those records. Separately, **Target, Costco, Sam's Club
and BJ's are not destinations at all**, and Walmart is split by format — Neighborhood Markets are
in, four `superstore` rows are not. [s3-7](experiments/s3-7-destination-truth.md)

**The shipped raster is not the measured grid.** The browser receives a WGS84 re-tiling that moves
another 2.42% of structures at fifteen minutes and omits 12,182 of them; and MapLibre places it in
Mercator while its rows are linear in latitude, which shifts 131,571 structures by one row. That
last is an analytical estimate, not a screenshot.

**There is no reference comparator.** T3 is gated on design §12 item 6, which the suffix-aware band
addresses for cost and travel time and **not** for route identity. So "our pipeline agrees with an
independent implementation of the same rules" is not a claim this release can make.

**E1c has no interval method chosen**, so the conditional estimand is specified and not computed.

## The decision this supports

Shipping with an **unverified** accuracy claim is a legitimate choice for a friends-and-family
release. It is the owner's to make explicitly, and the label must say which of the three outcomes
applies: construction fidelity is partly evidenced, engine disagreement is reported, real-world
accuracy is **unverified**.

If it ships, three things are owed to each household:

1. **the restricted-route flag** on any estimate whose route uses one — about 1 in 10;
2. **the destination the time was measured to**, since 550 places snap to 510 nodes and 75 share a
   node, so "ten minutes to a grocery" cannot name which without it;
3. **the scope**, in the household's words: walking, groceries, this metro, and a number that is an
   upper bound on the cost-selected journey rather than the best possible one.

## What would change the verdict most, per hour spent

1. **Walked journeys on restricted routes** — the only check that consults the world, aimed at the
   10% most likely to be wrong and in the known direction.
2. **The grocery definition decision** — it moves 3,912 structures at ten minutes and is currently
   arbitrary at the branch level.
3. **28 candidate destinations and 4 masked identities checked** by someone who can look.
