# Codex adversarial review, pass 48 — publishing the restricted-route flag

You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at commit
`5e5118f` plus two uncommitted record corrections described in §G. Python:
`v2/.venv/Scripts/python.exe`. **Do not create temporary directories inside the repository** — pass
pytest an explicit `--basetemp` outside it, or skip the full suite and say so. A graph load takes
about 100 seconds; `v2/scripts/flag_restricted_routes.py` takes several minutes.

The commit publishes step 8's restricted-route disclosure in the layer bundle and the wire format.
The format is `published-v3`: an **optional third uint8 plane** beside value and status, where
`0 = ROUTE_CLEAR` and `1 = ROUTE_RESTRICTED`. The whole design rests on four claims, and I want
every one of them attacked.

## The claims to attack, hardest first

**A. "The flag cannot move a verdict."** This is the claim the whole disclosure depends on: a
household's eligibility must not change because we told them something about the route. Three
mechanisms are supposed to enforce it.

* `wire.outcome_planes` does not take the flag as a parameter at all, and
  `v2/tests/test_wire.py::test_the_flag_is_never_an_eligibility_input` asserts that by inspecting
  the signature. Is a signature check real protection, or does it just mean the coupling would
  move somewhere a signature cannot see? Find a way to make the flag change a verdict without
  changing that signature.
* `worker_conformance.mjs` now initialises **two workers per disclosing group** — one with the
  flag planes, one without — and runs each `real window T=n` case twice against the same
  `verdict_sha256_32`. Attack the control itself: `loadWorker` deletes `require.cache` to get a
  fresh module instance, and the second worker is sent `{...initArgs(plainManifest), routeFlags:
  undefined}`. Does the plain worker genuinely never see a plane, or does some state survive the
  cache delete (`globalThis`, a closure, a typed-array view into a shared buffer)? If the two
  workers share anything, the control proves nothing and I want to know now.
* the `flags withheld` vectors reuse the **same** expected counts and digest as the disclosing
  case. Confirm those expectations are actually asserted on the withheld run rather than silently
  skipped — a case that passes because its assertions never execute is the failure mode this
  project has hit three times.

**B. The reprojection moves the flag, and I only half-caught it.** The source raster
(`v2/data/layers/own_triangle_grocery_walk_restricted_route.npy`) holds **57,175** set cells. The
shipped manifest (`v2/spikes/g3-render/fixtures/published/manifest.json`) reports
`flagged_cells: 57193` — **18 more**. `export_published_layers.py` re-checks only one direction
after reprojection: that no cell carries a flag where the status is not OK. So:

* account for the 18 in **both** directions. How many source-flagged cells were **dropped** by
  nearest resampling, and how many clear cells were **raised**? The net being +18 says nothing
  about the gross, and a dropped flag is an under-disclosure that no check in the pipeline can
  see.
* is nearest resampling of a flag plane defensible at all when value and status are resampled
  independently? Can a shipped cell end up with cell *P*'s minutes, cell *Q*'s status and cell
  *R*'s flag? If so the triple describes no journey that exists, and the invariant would still
  pass.
* my claim in the commit message — "the count is now 57,175, which matches the reported aggregate
  exactly" — is about the source grid. Is that sentence misleading about what ships?

**C. The invariant that caught a real defect. Does it have more gaps?** Before the plane shipped,
`cell_route_flag` was called with no horizon while the surface applies 7,200 s, so 5,145 cells
carried a disclosure about a journey whose reason had become `BEYOND_HORIZON`;
`wire.encode_route_flag` refused the export and named the count. Attack what that invariant does
**not** cover.

* it enforces `flag set ⟹ status OK`. Nothing enforces the converse direction in any form. Is
  there a soundness obligation we are not expressing — e.g. that a cell whose cost-minimal path
  used a restricted edge **must** be flagged? Construct a case where the flag is silently clear
  and it matters.
* the horizon fix passes `HORIZON_S = 7200.0`, a module constant in
  `v2/scripts/flag_restricted_routes.py`, while the surface's horizon arrives from the build JSON.
  Are they the same number by construction or by coincidence? What happens when a layer is built
  with a different horizon?
* `flag_restricted_routes.py` computes three populations. Does the horizon fix apply to all three,
  or only the ones I checked?

**D. Is the format decision right, and is the size claim fair?** I rejected a bit in the status
byte on contract grounds: wire codes are assigned explicitly and may not be reinterpreted, the
same rule that forbade reading minutes 251–254 as sentinels.

* attack the contract argument. Is there a reading under which a high bit in the status byte is
  *not* a reinterpretation — a reserved-bit scheme the format could have declared from the start?
* the size claim is 25,651 deflated bytes for the flag plane, 228,031 total against a
  `v1_deflated` baseline of 171,260, so 1.33×. Pass 43 F5 found the previous baseline unfair
  because it compressed v2's own bounds rather than v1's constant fill. Check `v1_plane()` is now
  the right baseline, and check whether **the flag plane's own** comparison is fair — should it be
  measured against the alternatives (a status bit, a sparse index, run-length) rather than against
  nothing?
* the plane is 17.3% set. Would a sparse representation beat 25,651 bytes, and by enough to matter
  on a phone?

**E. "Optional is load-bearing."** An absent plane means *this layer does not disclose*, which is
not *no route is restricted*. The worker reports `disclosesRoutes`, returns
`restrictedIncludedCount: null` rather than `0`, and **throws** when a manifest declares
`flag_file` but the plane does not arrive.

* trace every path by which a consumer could read the count and find one where `null` degrades to
  `0`, or to `false`, or to a rendered "0". `v2/spikes/g3-render/app.js:477` stores it in
  `state.lastRestrictedIncludedCount`; follow it.
* the refusal is keyed on the manifest declaring `flag_file`. What happens in the opposite case —
  a plane **arrives** that the manifest did not declare? Is it ignored, counted, or does it shift
  the per-layer array indices?
* is `discloses_restricted_routes` in the manifest derivable from the entries, and can the two
  disagree?

**F. The new mutations, as new code.** `mutate_worker.mjs` gained four mutations and reports 18 of
18 caught. Review them as new code: does each mutation actually produce the defect its name
claims, is any of them caught by something unrelated to what it targets, and is there an obvious
disclosure defect **no** mutation represents? An uncaught-but-unrepresented defect is worth more
than a caught one.

**G. The two record corrections, uncommitted at review time.** I corrected
`docs/experiments/s3-8-restricted-routes.json` (its prose quoted 7,276 from your pass 46 report
where the file's own datum is 7,271, and it still said "no flag plane is shipped at all") and the
step 8 row of `docs/plans/2026-11-04-s3-execution-plan.md` (which still said the flag is not
published). Check both corrections are now true and complete, and sweep for any **other** record
that the flag publication falsified — `docs/s3-decision-report.md` above all.

## Output

For each finding: severity, the exact file and line, a **runnable reproducer**, and what it costs —
a number that moves, or a claim that must be withdrawn. Say which claims you checked and could not
break. If claim A is unsound, say so first and in those words. Write your report to
`docs/research/49-codex-review-pass48-counterexamples/REPORT.md`.
