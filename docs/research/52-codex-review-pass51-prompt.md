# Codex adversarial review, pass 51 — the per-criterion card, and the walked-record refusal

You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at the tip
(commits `04bfacf`, `3406da6`, `ba9213c`, `1aa0570`). Python: `v2/.venv/Scripts/python.exe`.

## Runtime note — read this first, it changes what you can check

Your sandbox on this machine **cannot start processes at all**. Passes 48, 49 and 50 all
established this: every `exec_command` fails with `windows unelevated restricted-token sandbox
cannot enforce split writable root sets`, under `workspace-write`, with and without `--add-dir`,
and with `--ephemeral`. See `docs/engineering-notes/reference-codex-runtime-quirks.md`. So:

* You **cannot** run Python, pytest, `node` or `git`. Do not plan around them.
* You **can** read any file, and you **can** execute JavaScript through the `node_repl` MCP tool.
  Pass 49 used it to replay the whole conformance harness in `vm` contexts and decode the shipped
  binary planes; pass 50 used it to get three forbidden fields into a table that passed the gate.
  That is the strongest tool you have here, and both `card.js` and `worker.js` are plain scripts
  that attach to `self`, so they load into a `vm` context directly.
* For anything needing Python, reason from the source and **say what you could not execute**. An
  unexecuted argument clearly labelled as such is worth more to me than a guess dressed as a
  measurement. Pass 49's unexecuted Python findings were among its best.
* Write your report **to stdout as your final message**, not to a file.

## What this pass reviews

Two pieces of work. The second is the bigger one.

**A. The walked-record refusal** (`04bfacf`). `locfinder/measure/admissible.py`,
`scripts/score_walked_audit.py`, the `E3Result` additions in `measure/e3.py`,
`tests/test_admissible.py`, `scripts/mutate_admissible.py`, two new audit-sheet columns, and the
`docs/s3-decision-report.md` note.

**B. The per-criterion card** (`3406da6`, `ba9213c`, `1aa0570`). `handleExplainAt` in
`spikes/g3-render/worker.js`, the fold check and the per-criterion expectations in
`spikes/g3-render/worker_conformance.mjs`, `attach_outcome_expectations` in
`scripts/make_wire_vectors.py`, `spikes/g3-render/card.js`,
`spikes/g3-render/card_selftest.mjs`, `spikes/g3-render/mutate_card.mjs`,
`spikes/g3-render/bench_explain.mjs`, the plumbing in `spikes/g3-render/app.js`, and
`docs/plans/2026-11-14-per-criterion-card-plan.md`.

Read `docs/engineering-notes/project-phase1-s3-progress.md` first for the standing constraints and
the feedback ledger's 36 instances. The two passes before you found more in the repairs than in
the work being repaired, both times.

## The claims to attack, hardest first

Each of these is a claim I am making. Break it or narrow it.

1. **"The outcomes `explainAt` reports fold to the verdict `compute` wrote, at every cell of every
   fixture."** The fold check in `worker_conformance.mjs`. 720,165 cells across 47 cases. Attack
   the *claim*, not the arithmetic: what class of defect is this check structurally unable to see?
   I have already found one — at a cell where some layer already FAILs, the other layers' outcomes
   are invisible to both the fold and the verdict plane — and closed it by recording
   `wire.outcome_planes` per enabled layer. **Is there a second one?** Specifically: is there a
   defect in `handleExplainAt` that the fold, the recorded per-layer outcomes, the per-cell field
   assertions and the verdict-plane-did-not-move check all miss together?

2. **"The per-criterion expectations come from Python and are therefore independent."**
   `attach_outcome_expectations` reads the **written fixture bytes** and calls
   `wire.outcome_planes`. Is it independent? `wire.outcome_planes` is also what generated the
   `verdicts` arrays those same cases carry, via `combine_planes`. Does that make the new
   expectation a restatement of one already there, for some or all cases? And the digest path for
   the 40,000-cell window: the harness assembles `seenOutcomes[i][p] = cr.outcome` into an
   `Int8Array` and hashes it — does that hash the same bytes Python hashes, including for a case
   where a cell is never visited?

3. **"`explainAt` cannot move an eligibility answer."** It calls the same `outcomeFor`, which
   cannot see the route flag (pass 48 F1). But it now also reads `state.lastThresholds`, which is
   new mutable state written by `handleCompute`. Find a message sequence — `init`, `compute`,
   `recycle`, `mask`, `verdicts`, `destinationAt`, `explainAt`, in any order, with any arguments,
   including a compute that throws — where `explainAt` reports an explanation inconsistent with
   the verdict a household is looking at, or where it reports anything at all that it should not.
   The `enabledIndex` walk over `lastEnabled` and `lastThresholds` is where I would look first.

4. **"`null` means the layer does not disclose, and the card never renders it as an absence of
   restriction."** `card.js` plus `card_selftest.mjs`. Get a sentence out of `renderCardHTML`
   that claims more than the data supports. The specific targets: a bare minute where the value is
   a lower bound; "no restrictions" or anything a household would read that way, from a layer that
   does not disclose; a single named shop where the node carries several; a number where the
   status carries neither a time nor a bound; an unescaped place name. `card_selftest.mjs` claims
   to catch all five, and `mutate_card.mjs` claims 12 of 12. Find the sixth.

5. **"The admissibility predicate is the decision report's table in code."** Compare
   `admissible.py` against the four rows of the table in `docs/s3-decision-report.md` and against
   the audit README's instructions. Does the code require something the report does not, or
   permit something the report requires? Then: construct an audit-sheet row that is **inadmissible
   in substance and admissible to the predicate**. The destination comparison is a stripped string
   equality against `predicted_destination`; the start door is a cell-identity check; the duration
   is a `yes`/`no` column filled in by the person being checked.

6. **"An inadmissible walk is never silently dropped."** `sort_records` and `score_walked_records`.
   Is there a path by which a walk that happened reaches an `E3Result` as neither a scored
   observation nor an `Inadmissible` — or by which `no_admissible_observation` is `False` when it
   should be `True`? Consider duplicate labels, a record with `reported_s is None` and
   `walked_seconds` set, a record walked with `walked_seconds = 0`, and the interaction with
   `score_e3`'s own `walked` count.

## Measurements to attack as METHOD, since you cannot reproduce them

You cannot run these. Attack how they were taken and what they are claimed to show.

* **`bench_explain.mjs`: `explainAt` costs 0.0002 ms median, 0.0011 ms p99, over 20,000 cells of
  the real bundle, against 5.2 ms for a whole-raster compute.** I conclude that one `explainAt`
  per pointer move needs no batching and no cached outcome plane. The script says it is a floor
  because Node's shim is synchronous. Is the conclusion safe? Note the stride is a fixed prime
  (7919) and the warmup is 2,000 calls. What does a prime-stride walk over a 514×643 raster do to
  cache behaviour compared with a pointer moving between neighbouring cells, and does that make
  the figure optimistic or pessimistic? Is the comparison against a whole-raster compute the right
  denominator for a per-pointer-move cost at all?

* **"MapLibre draws the mask across a Mercator quad while the published rows are linear in
  latitude, and the two disagree by at most 0.366 rows, which is 35.6 m at a 97.5 m row."**
  Arithmetic on `bounds_wgs84 = [-79.2, 35.7, -78.5, 36.15]`, `nrows = 514`, in
  `card.js`'s `cellForLonLat` docstring and in the plan. I assumed MapLibre interpolates the
  canvas texture linearly in Mercator screen space between the four corner coordinates. **Check
  that assumption** against maplibre-gl-js v5.24.0 if you can read it, and check the arithmetic.
  Is the bound right, is it the right quantity, and does it apply to the longitude direction too?
  And is the conclusion right — that the card's lookup is correct and only the drawing is warped?

* **`card_selftest.mjs`'s real-bundle pass: 40,000 cells sampled at stride 7919 reached 5,960
  PASS, 27,207 FAIL, 6,833 UNKNOWN over three status codes, with 432 shared-node destinations.**
  I assert the sample "actually exercised something". What does it not reach? The bundle has one
  layer, so no multi-criterion card has ever been rendered against real data at all. Say how much
  that costs the check.

## My own suspicions, which you should settle rather than take from me

1. **The card is a single-layer surface tested on a single-layer bundle.** Every real-data check
   has one criterion. The fixtures have two-layer groups but no card rendering runs against them:
   `card_selftest.mjs`'s multi-criterion cases are hand-built. I think this is the biggest hole in
   B and I did not close it. How would you?

2. **`handleExplainAt` names no destination at a cell the region excludes**, following
   `destinationAt`. But a walk criterion that passes with a named grocery, at a cell excluded by a
   *different* criterion, arguably should be named. I left it as `destinationAt`'s rule and
   recorded the question. Is leaving it a defect, or is the rule right?

3. **`state.lastThresholds = T.slice()` stores the hoisted array, in enabled order**, while
   `lastEnabled` is in layer order. Two arrays in two orders, walked together by an index I
   increment by hand. I think the conformance check catches a mis-walk (it compares
   `thresholdMin` per entry against the case's own thresholds) but I am not confident the fixtures
   reach every pattern — only two cases disable an earlier layer, and no case disables a middle
   one because no group has three layers.

4. **`duration_timed` is filled in by the person whose walk is being checked.** The predicate
   refuses a blank, which is what pass 47's journey needed. It cannot refuse a wrong `yes`. Is
   there a check worth having here, or is this the irreducible limit of a self-reported audit?

5. **The two new sheet columns changed an artifact the owner may already have a copy of.** I
   inserted them into four committed CSVs and backfilled `duration_timed=no` on the one walked row
   from the text in its own `notes`. Is inferring that value from prose defensible, or should it
   have been left blank?

## Output

For each finding: a label (A1, B2, …), the file and line, **a concrete counterexample or witness**,
the severity, and what it would take to fix. Rank by severity. Say explicitly which of my six
claims survive and which do not, and which of my five suspicions you settled in which direction.
If a claim survives, say what evidence would still be missing.

Do not fix anything. Report.
