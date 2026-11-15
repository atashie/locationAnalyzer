# Codex adversarial review, pass 53 — the pass 52 repairs

You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at commit
`bcae16e`. Python: `v2/.venv/Scripts/python.exe`.

## Runtime note — read this first

Your sandbox on this machine **cannot start processes at all**: every `exec_command` fails with
`windows unelevated restricted-token sandbox cannot enforce split writable root sets`, under
`workspace-write`, with and without `--add-dir`, and with `--ephemeral`. See
`docs/engineering-notes/reference-codex-runtime-quirks.md`.

* You **cannot** run Python, pytest, `node` or `git`. Do not plan around them.
* You **can** read any file, and you **can** execute JavaScript through the `node_repl` MCP tool.
  Passes 51 and 52 both replayed the JavaScript harnesses inside `vm` contexts to a passing
  baseline and then applied mutations in memory. `card.js`, `worker.js` and both harnesses load
  into a `vm` context directly. That is the strongest tool here.
* For Python, reason from the source and **say what you could not execute**. Passes 51 and 52 each
  produced real source-derived findings.
* Write your report **to stdout as your final message**, not to a file.

## What this pass reviews

**The pass 52 repairs.** Your report on pass 52 is at
`docs/research/53-codex-review-pass52-repairs/REPORT.md`; the integration is `0dccf61`, plus
`bcae16e`. This is the fifth pass in a chain where each one has found more in the previous pass's
repairs than in the work being repaired, so assume that is the shape here too.

The repairs, in the order I rate their risk:

1. **The envelope and field expectations** in `worker_conformance.mjs`, and the **three-layer
   group** in `make_wire_vectors.py` added because no fixture could discriminate a criterion index.
2. **`createInspector`** in `card.js` after the position check replaced the generation counter,
   plus `requestFailed` and the `app.js` adapter around them.
3. **`admissible.py`'s** `evidence_of_a_walk` / `NON_EVIDENCE_VALUES`, `PermittedPlace`,
   `permitted_destinations`, the per-member arrival match, and `check_lonlat`.
4. **`scripts/migrate_audit_sheet.py`** and `tests/test_migrate_audit_sheet.py`.
5. **The block-level card assertions** in `card_selftest.mjs`.
6. **The seq-keyed paint wait** in `app.js` (`waitForResult`, `paintedSeqs`, `paintWaiters`) and
   `autoBench`.
7. The narrowed measurement wording in `bench_explain.mjs` and `card.js`.

Read `docs/engineering-notes/project-phase1-s3-progress.md` for the standing constraints and
`feedback-verify-the-shape-of-the-risk.md` for the 42 instances.

## The claims to attack, hardest first

**Instance 40 in that ledger is "closing the instances a reviewer supplies is not closing the
class", and you established it twice in one pass. So claim 1 is the one that matters.**

1. **"This time I enumerated the class rather than the instances."** For the worker: every field
   of the `explainAt` reply is now compared — `type`, `reqId`, `seq`, `row`, `col`, `verdict`,
   `verdictName`, and per criterion `layer`, `outcome`, `outcomeName`, `status`, `statusName`,
   `value`, `valueIsLowerBound`, `thresholdMin`, `horizonS`, `routeFlag`, `namesDestination`. For
   the sheet: `EVIDENCE_FIELDS` is meant to be every column only a walker fills in. **Find a
   field, or a column, or a value of one, that is still unchecked** — or a corruption that passes
   despite the comparison. Enumerate both lists yourself against the artifact rather than
   trusting mine.

2. **"The inspector cannot render a stale reply, cannot wedge, and cannot loop."** The generation
   counter is gone: `inspected` is the single source of truth and a reply must name that cell.
   `requestFailed` deliberately re-sends **only a queued position**, because re-asking the failed
   cell loops a deterministic error — I found that reading back my own F5 repair and fixed it in
   `bcae16e`. **Attack all three properties**, and the reasoning that removing `pointerGen` was
   safe. Then attack the `app.js` adapter: `post`, `cardFailed`, `clearCard`, `explainSentAt`
   (which is overwritten by every `post`, including a queued one), `resetAll`, and the `error`
   branch now calling `post(cardFailed())`.

3. **"The arrival is matched to the place it names, so the destination check establishes
   identity."** `PermittedPlace`, `permitted_destinations`, `DESTINATION_ARRIVAL_M = 200`.
   Construct a walk to a genuinely different shop that passes, or a legitimate walk that fails. Is
   200 m right, and is the centroid the right thing to measure to? Check against the real side
   table and the snapping code, as you did for the 600 m claim.

4. **"`migrate_audit_sheet.py` cannot lose an observation."** It inserts missing columns in
   canonical positions, reads the result back and compares every pre-existing value. **Find an
   input where it loses, reorders or corrupts something**, or where its read-back check would not
   notice. Consider: duplicate `journey_id`s (the check is keyed on them), a column the owner
   added whose name collides with a canonical one, embedded newlines or commas in `notes`, a BOM,
   a sheet with CRLF inside a quoted field, a row with more fields than the header, and
   `--in-place` when the backup path already exists.

5. **"The three-layer group makes a criterion-index substitution visible."** Three thresholds,
   three horizons, seven enable masks including a disabled middle layer. **Is there an index
   defect it still cannot see?** Check the `enabledIndex` walk, `enabledOracles`, `enabledTables`,
   `enabledDiscloses` and `enabledNames` against it, and say whether the group's own planes
   actually produce differing per-layer outcomes at the cells that matter.

6. **"`autoBench` can now finish, and the paint wait is correct."** `waitForResult` is keyed on a
   sequence number, with a 10 s timeout; `paintedSeqs` is pruned to 64. Attack it: a compute that
   paints before anyone waits, two waiters for one sequence, a `resetAll` mid-wait, the pruning
   (it slices a `Set`), and whether the timeout path can leave the bench button disabled.

## My own suspicions

1. **`explainSentAt` is a single timestamp on `state`, overwritten by every `post`.** With a
   queued request sent from inside `handleExplainAt`, the timing figure in the stats row may be
   measuring the wrong interval. It is a stats row rather than a verdict, but it is a published
   number on the page.
2. **The migration imports `audit_recommendations`**, which imports `geopandas`. A pure-CSV
   migration that cannot run without the geospatial stack is fragile for the one job it has — but
   duplicating the column list is the drift hazard this project keeps paying for. Which is worse?
3. **`NON_EVIDENCE_VALUES` is keyed by field name**, and only the two witness columns have an
   entry. Are there other columns whose legitimate answers do not mean somebody walked?
4. **I removed `pointerGen` rather than keeping it as defence in depth**, on the grounds that dead
   defensive code is a permanent mutation survivor. Was that the right call, or did I remove a
   guard that a future change will need?
5. **The card now names a destination at an excluded cell** (pass 51 B4), and you called the
   policy defensible but unevidenced. The wording you suggested — "these destinations explain
   individual criteria; this location does not meet all your criteria" — is **not** implemented.
   Should it be, and does the current wording mislead without it?

## Output

For each finding: a label, the file and line, **a concrete counterexample or witness**, the
severity, and what it would take to fix. Rank by severity. Say which of my six claims survive and
which do not, and which suspicions you settled in which direction. If a claim survives, say what
evidence is still missing.

Do not fix anything. Report.
