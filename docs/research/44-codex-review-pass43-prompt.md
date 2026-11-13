# Codex adversarial review, pass 43 — the grid decision and the browser path

You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at commit
`e2bd56f`. Python: `v2/.venv/Scripts/python.exe`. Node is on PATH. **Do not create temporary
directories inside the repository** — pass pytest an explicit `--basetemp` outside it, or skip the
full suite and say so.

This pass covers two product-risk steps, not the comparator. Step 4's 4b.0 is banked where your
pass 42 left it and is **out of scope**.

## What to review

**Step 5 / S3.1 — the grid decision**
`v2/scripts/compare_candidate_grids.py`, `docs/experiments/s3-1-candidate-grids.{md,json}`.

**Step 6 / S3.5 — the browser path**
`v2/locfinder/wire.py`, `v2/scripts/export_published_layers.py`,
`v2/scripts/make_wire_vectors.py`, `v2/spikes/g3-render/{worker.js,app.js,worker_conformance.mjs}`,
`v2/tests/test_wire.py`, `v2/tests/test_browser_conformance.py`,
`docs/experiments/s3-5-browser-path.md`.

Context you should read: `docs/plans/layer-contract.md` (S0's algebra and the prohibition on
writing `status.Reason` into a raster), `v2/locfinder/status.py` (`evaluate`, `combine`,
`needs_recomputation`, `Surface.validate`), and §0 of `docs/plans/2026-11-04-s3-execution-plan.md`.

## The claims to attack, hardest first

**A. Is the grid comparison actually matched, and is "the address" a legitimate reference?**
The design evaluates one population of structure centroids three ways — at its own coordinate, at
its 100 m cell centre, at its 200 m cell centre — from one graph and one Dijkstra. Attack that:

* Does `cell_arrival_with_provenance` at an arbitrary coordinate mean the same thing as at a cell
  centre, or does the published builder do something to cell centres that this bypasses?
* The `address` column is treated as truth. It is **our own model** evaluated at a different point,
  not ground truth. Does any conclusion in the write-up require it to be more than that? Is
  "the 200 m grid roughly doubles the error" sound when the reference shares every model defect?
* The population is the 100 m grid's `structure_population`, and each point is then looked up in
  the 200 m grid. Does that privilege the 100 m grid — for instance by excluding structures the
  200 m grid covers and the 100 m one does not? The run reports 0 structures outside either grid;
  verify that and say whether the inclusion test can be asymmetric at the footprint edges.
* `centres_for` dedupes cells with `rows * (ncols + 1) + cols`. Is that injective for every grid
  this could run on, and does it reconstruct the same centres as `GridSpec.cell_centers_xy`?

**B. Are the reported figures the figures?** Reproduce the headline numbers. In particular check
that the verdict counts are over structures and not cells, that `covered` is applied consistently
across the three columns, and that `difference_summary` is not quietly dropping a population — it
indexes before subtracting specifically to avoid `inf - inf`, so check what that exclusion does to
the denominators it reports. Is the 15-minute peak real or an artifact of the population?

**C. The wire format's soundness.** `value` is a travel time where `status` is `OK` and a **lower
bound** where it is `OFF_NETWORK`, `BEYOND_HORIZON` or `NO_PATH`. The claims:

* `ceil(x/60) > T` is equivalent to `x > 60T` for integer `T`, so a whole-minute decoder reaches
  `evaluate`'s verdict **exactly**. Attack it — including at the cap, at zero, and for a
  non-integer threshold, which the slider should not produce but nothing in the format forbids.
* capping a bound downward can only turn a known failure into an unknown, and an `OK` minute above
  the cap is refused rather than capped. Is the refusal reachable on any layer this project can
  build, and is the saturation actually in the safe direction everywhere?
* `BEYOND_HORIZON` compares against the manifest's `horizon_s` and never against the stored bound.
  `Surface.validate` requires that bound to equal the horizon exactly. Is the value plane therefore
  dead weight for that code, and does anything break if a manifest's `horizon_s` disagrees with the
  bound the planes were built from?

**D. `UNKNOWN_CAUSE`, which is the part I am least sure of.** I claim it lets a v1 artifact lift
into v2 "without inventing provenance", because it can never be a known failure and that is exactly
what v1 could assert. Is that true? Is there a case where v1's `NODATA` carried *more* information
than `UNKNOWN_CAUSE` does — or where treating it as unknown changes a verdict against v1's own
behaviour? Note that v1's worker set `inside = 0` for `NODATA`, so in the **mask** it behaved like
an exclusion. Does the lift change what a mask consumer sees, and is that a regression?

**E. A behaviour change I made deliberately and may have got wrong.** With no layers enabled, the
old worker painted everything transparent; the new one marks every cell INCLUDED, because
`status.combine` says a search with no constraints excludes nothing. Is matching the algebra the
right call for a map, or does it put a blue sheet over the whole Triangle the moment a household
unchecks its last criterion? Say which, and whether the algebra and the rendering should differ
here.

**F. Does the conformance harness check what it claims?** It shims `self`, requires `worker.js`,
and drives it by message. Attack:

* the verdict reconstruction. It reads INCLUDED from the mask and separates EXCLUDED from UNKNOWN
  **only on hatch-stripe pixels**, skipping the rest. What fraction of cells is actually compared,
  and could a defect hide in the skipped ones?
* `verdict_sha256_32` is computed and then only checked for being a 32-character string. That is a
  no-op. Confirm it, and say whether the digest can be made meaningful or should be removed.
* the 200 × 200 window is claimed to carry every status code the published layer produces. Verify,
  and say whether a window at origin `(0, 0)` is representative or merely the first that matched.
* `delete require.cache[...]` per group — does each group really get fresh worker state, or does
  module-level state leak between groups and mask an ordering bug?

**G. The exporter.** Both planes are reprojected with nearest and uncovered pixels become
`OUTSIDE`. Check that the source transform reconstructed from `build.json` (and from the metro grid
for the layer that predates it) actually places the array correctly — a transform that disagrees
with its array silently moves every cell. Check that no status code can be produced that the
decoder does not define, and that `deflated()` is a fair size comparison against v1.

**H. What the write-ups claim versus what was run.** Both documents are new. Find any sentence
stating more than the evidence supports, in the way your passes 38 to 42 repeatedly did. I have
tried to mark what is not done — phone latency, the per-criterion card, `OUTSIDE` having no live
producer, recomputation eligibility — but check the positive claims too, especially "it costs 9%",
"cell for cell", and "keep 100 m".

## Output

For each finding: severity, the exact file and line, a **runnable reproducer**, and what it costs —
a number that moves, or a claim that must be withdrawn. Say plainly which of my claims you checked
and could **not** break; that is as useful as a finding. If the grid decision itself is wrong on
this evidence, say so in those words.
