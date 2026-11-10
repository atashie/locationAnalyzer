# Codex adversarial review, pass 34 — the walked finding and its recommendations

**2026-11-10.** Reviewed the **findings and recommendations** in `8931563`, not its code hygiene.
Eight findings. Its one-line verdict:

> "The stale-raster diagnosis holds. The soft-way note needs substantive corrections before it
> supports a product decision."

That split is the useful part. The diagnosis I was least sure of was confirmed exactly; the note
written for the owner to act on needed six corrections, and one of them replaced its central
framing. Counterexamples and scripts are in `35-codex-review-pass34-counterexamples/` — the review
left 431 MB of surfaces and logs in an untracked `v2/.review34/`, of which the 174 KB that
reproduces the findings is kept.

## What it corrected

**1. The ratio survives, the causal conclusion does not.** The published journey decomposes to
28.1508 s / 35.4700 m of access plus 782.6677 s / 1,095.7348 m of network = **1,131.2049 m**, so
multiplying everything by 1.40 m/s overstated it by 3.94 m and the **54.1%** figure holds. But those
are lengths of *potentially different journeys*. It supports "the model represents a substantially
shorter journey than the owner described" and **not** "half the real distance", an impassable
shortcut, or speed and intersection delay being ruled out. Unsupported rather than refuted.

**2. The bracket compared two different journeys, and a matching route exists.** My no-track rebuild
also changed the **destination** — Seal The Seasons rather than Hill's Family Asian Markets — so
"the observation sits between the two bounds" was not a clean comparison. Holding Hill's fixed and
entering through the `service` way 57.4 m out, with neither `track` nor `path`:
**2,139.9 m = 1.3297 mi, 1,533.1 s = 25.55 min**, against the owner's 1.3 mi and ~25 min. A
reproducible candidate, not proof of their route — the access connector is unknown.

**3. `{track, path}` measures tag sensitivity, not usability.** Removing `footway` costs 3.775% of
15-minute PASS buildings and `service` 9.004%, against 0.393% for `track`+`path`. Class establishes
neither surface nor permission: tracks can be paved, informal footways exist. And the larger
deletions change destination snapping, so they are full-pipeline policy sensitivities rather than
route-only effects or error rates.

**4. Destination contamination refuted; my UNKNOWN figure wrong.** All three variants retain exactly
the **same 510 destination identities and admission decisions** despite retaining
539,814 / 538,178 / 534,949 nodes, and component pruning introduces **zero** of the reported losses
(holding nodes and destinations fixed gives 446 lost 15-minute PASSes against 414, so pruning
*rescues* 32). Every one of the 5,287 distinct lost cells uses `track`/`path` on its baseline route.
But "10,010 cells into UNKNOWN" is a **net change in non-finite times**: gross 10,080 finite →
non-finite and 70 back, of which **8,307 become `OFF_NETWORK` and 1,773 `BEYOND_HORIZON`** — the
latter are *known FAILs*, not unknowns. And at fifteen minutes the deletion **gains** 245 PASS
cells, a net reduction of 169 cells / 493 buildings.

**5. Enrichment reproduces; the comparison it justified does not.** Band cells lose PASS at 1.164%
against 0.429% overall at ten minutes and 2.651% against 0.871% at fifteen — **2.72× and 3.04×**,
now measured instead of argued. But my "3 in 16 against 0.39%" counted *any time change* on one side
and *buildings losing PASS* on the other. **Only one sampled row loses a PASS.**

**6. The staleness mechanism confirmed exactly.** Reinstating the historical `symmetrise`
reproduces the stored raster **bit-for-bit across all 330,502 cells**. The lost 15-minute PASS is
cell **(211, 150)**, 883.9439 → 923.7095 s: at `6814689349 → 6801677574` the old private Harkness
Circle (way 572930114, 46.4852 s, cost 166.4852) is displaced by a newly added reverse `service`
edge (way 727164383, 86.2508 s, cost 86.2508). CSR keeps the cheaper, slower edge. My hypothesis
was right and is now evidence.

**7. The rebuild recommendation needed a procedure.** G1 does not write all the companions — the
**S2 builder** writes the seconds/reasons/lower-bounds/sidecar/TIFF bundle — and the sequence has to
continue through S0 verification, the audit draws, their metadata hashes, and dependent published
figures. The frozen B/C frames are safe (their inputs are buildings, grid and seed). And the
browser **exporter ignores `own_triangle_grocery_walk.tif`**, selecting `own_grocery_walk.tif`, so a
Triangle rebuild does not update what the browser serves at all — a gap I had not noticed, belonging
to plan §0 step 6.

Also: option 3 as I wrote it is an engineering proposal for highway *classes*, since `access.py`
penalises access *tags* and open `track`/`path`/`footway`/`service` examples all receive zero. And
**"loses to any paved alternative" is false for any finite penalty** — the saved counterexample
picks a 100 s track plus 120 s penalty over a 1,000 s paved alternative.

**8. The snap identity was wrong.** The matched way is **430448289**; 1254722642 is the next full
segment. With the 7.56 m partial first edge the approach is **305.44 m**, not 298 m. **17–19
geometries qualify within 120 m** and my tool printed only the nearest 14 — which I then wrote up as
"every one of the 14 edges within 120 m", a print limit read as a population. "Unmapped",
"artificial" and "impassable" all exceed the evidence. And `v2/data/` is untracked, so "stored
raster" is the accurate phrase, not "committed".

## What it did not find, and what I found alongside it

The review did not reach the cause. While it ran, I traced the chain: the 298 m approach is way
**1254722641**, tagged **`access=private`**; `classify_access` labels it `restricted` correctly;
`add_travel_times` does apply `cost = travel_time + 120 s`; and 120 s over ~4 restricted edges is
480 s against a 968 s detour, so the private track wins on cost and its *real* time is reported.
**A calibration finding, not a missing mechanism** — and the two results are compatible: pass 34 is
right that the penalty is keyed to access tags rather than classes, and this edge happens to carry
the tag.

`scripts/measure_restricted_walk_policy.py` then measured the policy: **600 s fixes the walked cell
and costs 1.10% of 15-minute PASS buildings**, with UNKNOWN moving only 73,750 → 73,968. That is now
the recommended option, and it exists because the review's framing correction forced the question
"what is actually causing this" instead of "which class should we delete".

## The pattern

Revision 1 of that note got the observation right, the mechanism wrong, and the measurement pointed
at the wrong knob. Six of the eight findings are in **how I framed and compared**, not in the
computation: a ratio between two different journeys, a bracket across two destinations, a class
exclusion standing in for a usability question, a net change reported as a gross one, two
differently-defined rates compared directly, and a print limit read as a count.

This is the same distribution as passes 31–33 and the reason the pass exists at all. The
generalisation that fits all six is narrower than "verify the shape of the risk": **when a number is
produced to inform a decision, the thing most likely to be wrong is what it is a number *of*.** Both
sides of every corrected comparison were individually computed correctly.

Noted in [[feedback-decide-by-measurement-not-by-argument]], because the measurements were real and
the inferences drawn from them were the defective part.
