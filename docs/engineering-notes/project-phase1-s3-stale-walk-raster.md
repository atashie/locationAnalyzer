# The committed walk raster predates a fix to its own graph

**2026-11-10.** Found while building a baseline for the soft-way counterfactual, when a
current-code rebuild refused to reproduce the shipped layer.

## The fact

`v2/data/layers/own_triangle_grocery_walk.npy` was built **2026-11-04 13:42** and verified
bit-identical by `spikes/s0_status_on_real_layer.py` at **14:43**
(`data/s0_status_triangle_grocery_walk.json`: `float32_identical: true`, `cells_differing: 0`).

**`ab01ffa`, 2026-11-04 21:12**, then fixed a production defect in `speeds.symmetrise`. It had
asked `G.has_edge(v, u)`, so the existence of *any* edge from `v` to `u` suppressed the reverse of
*every* road from `u` to `v`. Where those are different roads with different access classes, a
legitimate pedestrian route disappeared. Its own commit message says it "silently removed
pedestrian edges from the shipped walk graph".

The raster was never rebuilt. `symmetrise` now adds **54,453** reverse edges
(1,406,156 → 1,460,609).

## What differs

A current-code rebuild against the committed raster:

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
only shorten journeys.** It is possible, and the reason is in `csr.py`: for parallel edges the
**cost**-minimal one wins and carries *its own* time. A new reverse edge that is cheaper but slower
can therefore displace a faster one and lengthen the reported journey. So the staleness is not
monotone, and I should not have assumed it was — the assumption survived one sentence before the
data refuted it. Not chased further; recorded so the next person does not re-derive it.

## Why it matters more than 2.19% suggests

The walked-audit sheets were generated from this raster, and its SHA-256 still matches their
metadata. So the owner is being asked to walk journeys whose predicted times were computed with
pedestrian edges missing.

It also broke a verification claim. `scripts/recover_audit_destinations.py` checked its rebuild
against the committed raster on the 35 audit rows, all 35 matched, and I wrote in the sheet's
README that the recovered destinations therefore "belong to the published numbers". **None of the
35 is among the 7,246**, which is why they agreed — the sampler had no reason to pick changed
cells. See [[project-phase1-s3-audit-destination-recovery]] for the withdrawal and for Codex pass
33's second, independent defeat of the same argument.

## It does not explain the owner's walk

`band15min_pass-03` is **810.8 s in both** the committed raster and the current rebuild. The cell
the owner walked is not among the 7,246. So the staleness and
[[project-phase1-s3-soft-way-dependence]] are two independent problems, and fixing this one would
not have moved that journey by a second.

## What to do

**Rebuild the layer**, and the audit sheets from it. The rebuild is a known command
(`spikes/g1_own_graph_layer.py`, verified by `spikes/s0_status_on_real_layer.py`) and the
differences are measured, so this is bookkeeping rather than a decision.

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
