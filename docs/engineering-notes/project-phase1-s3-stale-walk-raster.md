# The committed walk raster predates a fix to its own graph

**2026-11-10.** Found while building a baseline for the soft-way counterfactual, when a
current-code rebuild refused to reproduce the shipped layer.

## The fact

`v2/data/layers/own_triangle_grocery_walk.npy` — **stored, not committed: nothing under
`v2/data/` is tracked, which is its own problem, below** — was built **2026-11-04 13:42** and
verified bit-identical by `spikes/s0_status_on_real_layer.py` at **14:43**
(`data/s0_status_triangle_grocery_walk.json`: `float32_identical: true`, `cells_differing: 0`).

**`ab01ffa`, 2026-11-04 21:12**, then fixed a production defect in `speeds.symmetrise`. It had
asked `G.has_edge(v, u)`, so the existence of *any* edge from `v` to `u` suppressed the reverse of
*every* road from `u` to `v`. Where those are different roads with different access classes, a
legitimate pedestrian route disappeared. Its own commit message says it "silently removed
pedestrian edges from the shipped walk graph".

The raster was never rebuilt. `symmetrise` now adds **54,453** reverse edges
(1,406,156 → 1,460,609).

## What differs

A current-code rebuild against the stored raster:

| | |
|---|---|
| cells differing | **7,246** of 330,502 (2.19%) |
| buildings in them | **11,436** of 512,633 |
| finiteness changes | **0** — nothing became UNKNOWN or stopped being UNKNOWN |
| largest difference | 2,316.8 s |

Verdict movement is small:

| *T* | gained a PASS | lost one |
|---|---|---|
| 10 | 10 | 0 |
| 15 | 15 | **1** |
| 25 | 13 | 0 |
| 45 | 6 | 0 |

**One cell lost a 15-minute PASS, and that should not be possible if adding pedestrian edges can
only shorten journeys.** It is possible, and Codex pass 34 **confirmed the mechanism exactly** on
the real data rather than leaving it as my hypothesis. The cell is **(211, 150)**, moving
883.9439 → 923.7095 s. At the directed pair `6814689349 → 6801677574`:

| edge | time | cost |
|---|---|---|
| the old private Harkness Circle, way `572930114` | 46.4852 s | 166.4852 |
| the newly added reverse `service` edge, way `727164383` | 86.2508 s | 86.2508 |

`csr.graph_to_cost_time_csr` keeps the **cost**-minimal parallel edge and carries *its own* time, so
the cheaper-but-slower new edge displaced the faster penalised one. Access, endpoint, destination and
the rest of the route are unchanged. So the staleness is **not monotone**, and I should not have
assumed it was — the assumption survived one sentence before the data refuted it.

Pass 34 also reproduced the whole diagnosis independently: reinstating the historical `symmetrise`
regenerates the stored raster **bit-for-bit across all 330,502 cells**.

## Why it matters more than 2.19% suggests

The walked-audit sheets were generated from this raster, and its SHA-256 still matches their
metadata. So the owner is being asked to walk journeys whose predicted times were computed with
pedestrian edges missing.

It also broke a verification claim. `scripts/recover_audit_destinations.py` checked its rebuild
against the stored raster on the 35 audit rows, all 35 matched, and I wrote in the sheet's
README that the recovered destinations therefore "belong to the published numbers". **None of the
35 is among the 7,246**, which is why they agreed — the sampler had no reason to pick changed
cells. See [[project-phase1-s3-audit-destination-recovery]] for the withdrawal and for Codex pass
33's second, independent defeat of the same argument.

## It does not explain the owner's walk

`band15min_pass-03` is **810.8 s in both** the stored raster and the current rebuild. The cell
the owner walked is not among the 7,246. So the staleness and
[[project-phase1-s3-soft-way-dependence]] are two independent problems, and fixing this one would
not have moved that journey by a second.

## What to do — and the one-command version of it was wrong

**Rebuild the layer**, and the audit sheets from it. Revision 1 called this "a known command
(`spikes/g1_own_graph_layer.py`) … bookkeeping rather than a decision". Codex pass 34 found that
insufficient in two ways.

**The G1 command does not write all the companions.** A coherent rebuild has to produce the seconds,
the reason raster, the lower bounds, the build sidecar and its digests, and the encoded TIFF
together — the **S2 builder** writes that bundle; G1 does not. Then S0 verification, then the audit
draws, their metadata hashes and the destination enrichment, then any published figure computed off
the old surface. Sequenced, not one command.

**The browser is not downstream of this raster at all.** The exporter ignores
`own_triangle_grocery_walk.tif` and selects `own_grocery_walk.tif` — the earlier 401×550 slice. So
a Triangle rebuild does **not** update what the browser serves, and serving Triangle at all needs
explicit export configuration plus regenerated bins and manifest. That is a separate gap from the
staleness and it belongs to plan §0 step 6.

**The frozen B/C sampling frames are safe.** Their inputs are the buildings file, the grid and the
seed — not this raster — so a rebuild does not disturb `51a59463` or `7914e80a`.

The process lesson is the one worth keeping: **a fix to a graph-building function invalidates every
artifact built from it, and nothing in the repository connected those two facts.** The provenance
JSON records the inputs and the code's behaviour at build time but has no way to say "a function I
depend on has since changed". A cheap guard would be for `s0_status_on_real_layer.py` to run in CI,
or for the layer to carry a digest of the preparation functions the way the encoding now carries an
`encoding` version — see [[project-phase1-s3-encoding-threshold-crossing]], which solved the same
class of problem for the minute rasters by stamping a version into every raster and the browser
manifest.

## A related gap found while fixing this

**Nothing in `v2/data/` is tracked, including `s0_status_triangle_grocery_walk.json`** — the
provenance file whose destination counts `recover_audit_destinations.py` validates against. The
check is guarded with `if PROVENANCE.exists()`, so on a fresh clone it silently does not run.

That is the same shape as the staleness itself: the artifact that would detect a mismatch is not
in the diff, so no review can see it go missing. Worth settling as its own decision — either the
small provenance JSONs join the repository while the rasters stay out, or the check becomes a hard
requirement that fails loudly when the file is absent. It should not stay as a check that
disappears quietly.
