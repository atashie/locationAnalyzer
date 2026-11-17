# The grey diagonal striping: a disclosure that fires on cell coordinates

**2026-11-16.** The owner, looking at the built seven-criterion page, said: *"I disagree that the
grey diagonal lines of nodata are okay - those striping effects are problematic and should be
rectified."*

That was a disagreement with a **pass-56 verdict of mine**, not a new question. I had told them the
hatch was "the renderer working as designed". Taking the objection seriously produced a measurement
nobody had taken, and the verdict was wrong — not about the design's intent, which is real and
deliberate, but about whether the design does the job its name claims.

**Both pass-57 reviewers judged the complaint SUPPORTED.** Reviews in
`docs/research/59-review-pass57/`; measurement in `v2/scripts/measure_hatch_visibility.py`, which
needs no graph and runs in a second.

## The rule

`spikes/g3-render/worker.js:473`:

```js
px[p] = (((r + c) & HATCH_PERIOD_MASK) < HATCH_WIDTH) ? PX_NODATA : PX_OUT;
```

with `HATCH_PERIOD_MASK = 7` and `HATCH_WIDTH = 2`, so an UNKNOWN cell is painted grey on **2 of
every 8 diagonal positions** and painted `PX_OUT` on the other 6. **`PX_OUT` is `0` — byte-identical
to the value an EXCLUDED cell gets.** `r` and `c` are **published-grid** indices (`p = r * ncols + c`
over 514 x 643), not UTM, which is why the measurement reads `fixtures/published/*.bin`; quoting a
UTM figure at a question about painted pixels is the pass-56 error class.

So the hatch covers **82,627 of 330,502 cells (25.00%)** of the grid regardless of what is in it.

## What that does to the disclosure, measured

Published park/walk at its **shipped 15-minute default** (the layer also ships `default_on: false`;
only grocery/walk opens enabled):

```text
limit UNKNOWN painted invisible %painted blobs wholly-invisible cells-in-those
   15   55,752  13,953    41,799   25.03%  1,075              369            975
   20   56,034  14,023    42,011   25.03%  1,075              369            975
```

**369 of 1,075 eight-connected UNKNOWN regions — 34.3% — receive not one grey pixel.** On screen
they are byte-identical to a confident "no". The hover verdict still reports UNKNOWN, so the data
is not lost; the *visual* disclosure is.

It fails on small regions and succeeds on large ones, which is the opposite of what a texture needs:

| region size | regions | cells | wholly invisible | % of regions |
|---|---:|---:|---:|---:|
| 1 | 249 | 249 | 182 | 73.1% |
| 2-3 | 164 | 391 | 106 | 64.6% |
| 4-8 | 168 | 947 | 63 | 37.5% |
| 9-16 | 132 | 1,588 | 17 | 12.9% |
| 17-64 | 196 | 6,685 | 1 | 0.5% |
| 65+ | 166 | 45,892 | 0 | 0.0% |

Median region is **7 cells**. All three walk layers are identical, and Codex verified set membership
rather than counts: **zero UNKNOWN-set differences across every integer threshold 1-60**.

## What the owner is actually seeing, which is not what I guessed

I guessed moiré, or the invisible specks. Codex's projection arithmetic says neither. The mask is
sampled `nearest`, so the hatch period in CSS pixels is:

| zoom | px per raster cell | hatch period across the stripes |
|---|---:|---:|
| 8 | 0.40 | 2.23 px |
| 9 | 0.79 | 4.47 px |
| 10 | 1.58 | 8.94 px |
| 11 | 3.16 | 17.88 px |
| 12 | 6.32 | 35.75 px |
| 14 | 25.28 | 143.00 px |

At the opening view the stripes are broad, stepped diagonal bands — roughly 200 m of dark separated
by 600 m of clear, across the 17% of the map that is OFF_NETWORK, which here is the lakes and the
state forests. That is what "grey diagonal lines" describes. **The invisible-small-region defect is
a separate thing the investigation uncovered, not what the owner complained about** — and I
initially told them the invisible patches were the serious half, which was backwards.

## The harm is in the visible stripes, not the invisible specks

Codex measured building exposure without resampling a count raster — building centroids assigned
once each to a published cell, which the reprojection's nearest-neighbour cannot do without
duplicating or dropping:

```text
buildings in the 369 wholly invisible regions      55   (0.011% of published inventory)
occupied invisible regions                          17
occupied invisible cells                            25
buildings in UNKNOWN cells overall               3,364   (0.672%)
published building population                  500,451
```

So the missing mark is real and its measured exposure is **1.64% of the buildings in UNKNOWN
cells**. The other 98% sit in the 166 large regions that *are* marked — the ones the owner can see.
Antigravity puts 86.3% (2,904) of UNKNOWN buildings in those large striped regions. **The visual
complaint is where the harm is.** The one-third-of-regions headline is a count of components, and a
component is not a household.

## What shipped, 2026-11-16

**The owner chose this decision first**, and the hatch is now a **uniform tint**: `worker.js` paints
every UNKNOWN cell `rgba(60, 60, 60, 64)` and the `(row + col) & 7` branch is gone.

Alpha 64 is about **twice the hatch's average ink** (130 x 0.25 = 32.5), so a region is
unmistakable, and **under half its peak**, so the basemap reads through. It stays distinct from
`PX_IN`'s 150 and `PX_OUT`'s 0, which is what `probe_placement.js` uses to tell the three classes
apart.

**Verified by looking, not only by measuring.** Before: scattered dark diagonal ticks with no
coherent boundary, over blue and over land alike -- map clutter, which is what the owner reported.
After: Falls Lake and its forest corridor read as one continuous greyed region. The measurement
agrees: **369 wholly unmarked regions -> 0**, at every region size and on every walk layer.

What this did **not** do is make the mark zoom-independent. The tint still lives in the raster, so
it still scales. That matters much less than it did -- a uniform fill has no period to beat against
the sampling grid -- but the screen-space pattern in option (iv) remains the thing that would
remove scale dependence entirely, and it needs the polygonizer and a `fill-pattern` layer.

**Three things changed with it.**

* `index.html` said `nodata in an enabled layer` in the legend, beside the thing the owner
  objected to. That is debug plumbing. It now reads **"not enough data to say"**, and the swatch
  is a solid tint rather than a miniature hatch.
* `measure_hatch_visibility.py` diagnosed the hatch, so it would have rotted into a description of
  code that no longer exists. It now **checks the shipped rule and exits non-zero** if any UNKNOWN
  cell carries EXCLUDED's bytes; `--rule hatch` still reproduces the defect's own numbers. The gate
  was shown reachable rather than assumed so: fed the old mask it reports **41,799 of 55,752
  unmarked**, fed the shipped one it reports none.
* The drawn-pixel oracle (`docs/experiments/s3-10-drawn-pixel.json`) carried its own copy of the
  paint rule and had to be regenerated. **Its headline findings did not move** -- 131,571 structures
  read a moved row, 5,801 contradictions at 20 minutes, 2,771 painted-out-but-included -- because
  the row displacement does not depend on the paint. But one of its three sensitive probes had an
  expected pixel of `[0, 0, 0, 0]`: an UNKNOWN cell the old renderer drew **exactly like an excluded
  one**, sitting in the committed oracle the whole time.

That last change also closed a known inaccuracy. Codex pass 55 (F8) found that
`the_outcome_contradicts_the_card` and `the_colour_contradicts_the_card` described different
quantities while holding the same number, because an UNKNOWN cell off the stripe painted like a
FAIL. **Every outcome now paints a distinct pixel**, so the two names are finally synonyms.

Guarded by two new mutations in `mutate_worker.mjs`, both confirmed caught and neither inert:
dropping the tint, and **reintroducing the diagonal hatch**. Nothing else would catch the second --
the counts, the verdict plane and the mask are all unchanged by it, and only the per-pixel check
sees it. The conformance suite's own expectation had to be corrected too: it read
`onStripe ? PX_NODATA : PX_OUT`, so it **asserted that three quarters of UNKNOWN renders exactly
like EXCLUDED**, and passed while they did. A check that encodes the defect cannot report it.

## Options, as they stood

| option | assessment |
|---|---|
| (i) Leave it | Rejected by both reviewers and by the owner. |
| (ii) Solid translucent fill | Removes the marking holes at texture resolution. Colour, opacity and comprehension untested; a flat grey may read as another data class or obscure the basemap. |
| (iii) Force one marked cell per component | Marks every component. One dot communicates neither extent nor certainty, and does not guarantee screen visibility at low zoom. |
| (iv) Screen-space hairline hatch over a faint neutral tint | Antigravity's recommendation: ~6-8% tint plus a zoom-independent pattern. Fixes both the scale dependence and the gaps. Untested with a reader. |
| (v) Outline or stipple the boundaries | Identifies edges, leaves large interiors ambiguous. |
| (vi) Publish a smaller area and stop drawing it | **UNSUPPORTED.** See below. |

**Option (vi) does not work and I should not have offered it.** I suggested to the owner that we
stop publishing the OFF_NETWORK area. **80.3% of it (44,995 cells, 2,811 buildings) is strictly
interior** — Jordan Lake, Falls Lake, Umstead, Duke Forest — not an outer margin that can be
clipped. And `worker.js:533-536` maps `S_OUTSIDE` to `O_UNKNOWN`, so a naive crop **redraws the same
stripes** on the same pixels. Codex adds the epistemics: for a cell where the lower bound cannot
establish a threshold failure, UNKNOWN **is** the correct verdict, and silently making unsupported
land transparent preserves the ambiguity rather than removing it. A legend count does not tell a
household whether its own property is covered.

I also gave the owner this area as **560 km²**, by multiplying 56,036 published cells by 100 m
squares. Published cells are WGS84 lon/lat averaging **9,544 m²** — a 97.69 m equivalent side — so
the geodesic figure is **535.0 km²**. Ledger instance 50, third time.

## What is not established

- **That any replacement reads better.** Both reviewers were explicit: the 166 large regions each
  containing some ink does not establish that their presentation *works*, and no option here has
  been put in front of a reader. This needs the reading test, not another measurement.
- **That the three classes are distinguishable at useful zooms.** The check to run is whether a
  reader can tell UNKNOWN from EXCLUDED from outside-coverage at the opening view and at
  neighbourhood zoom. Nothing has tested that.
- **No screenshot-level diagnosis was done.** The zoom table above is projection arithmetic from
  the code, not an observation of the rendered page.
- **`index.html:29` still reads "nodata in an enabled layer"**, which is debug plumbing sitting in
  the legend next to the thing the owner objected to. Separate from the design decision and
  cheaper.

## Where it ranks

Antigravity ranks this **first** of the four decisions — the cheapest honest improvement, covering
17% of the map, with no routing rebuild. Codex ranks it **second**, behind the restricted-route
penalty, on the ground that the penalty has direct evidence of a materially misleading
recommendation while a 17% map-area share is not itself evidence of retired recommendation risk.
Both put it above the donut holes, and both note it is the cheapest **clear** product improvement
available.

The owner ranked this **first** on 2026-11-16 and it is done, in the narrow form above: a uniform tint, not the screen-space texture. The remaining question is whether a reader can tell the three classes apart, and that is a reading test, not a measurement.

Related: [[project-phase1-s3-donut-holes]], [[project-phase1-s3-progress]],
[[feedback-verify-the-shape-of-the-risk]], [[s3-13-reading-test]].
