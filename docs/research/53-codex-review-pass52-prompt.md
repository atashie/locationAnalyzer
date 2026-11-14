# Codex adversarial review, pass 52 — the pass 51 repairs

You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at commit
`50e3884`. Python: `v2/.venv/Scripts/python.exe`.

## Runtime note — read this first

Your sandbox on this machine **cannot start processes at all**: every `exec_command` fails with
`windows unelevated restricted-token sandbox cannot enforce split writable root sets`, under
`workspace-write`, with and without `--add-dir`, and with `--ephemeral`. See
`docs/engineering-notes/reference-codex-runtime-quirks.md`.

* You **cannot** run Python, pytest, `node` or `git`. Do not plan around them.
* You **can** read any file, and you **can** execute JavaScript through the `node_repl` MCP tool.
  Pass 51 replayed both JavaScript harnesses inside `vm` contexts to a passing baseline and then
  applied mutations in memory; that is the strongest tool here and `card.js`, `worker.js` and the
  harnesses all load into a `vm` context directly.
* For Python, reason from the source and **say what you could not execute**. Pass 51's A findings
  were source-derived and three of them were real.
* Write your report **to stdout as your final message**, not to a file.

## What this pass reviews

**The pass 51 repairs, which are larger than the thing they repaired** — 1,406 insertions. Your
own report is at `docs/research/52-codex-review-pass51-card/REPORT.md`; the integration is
`50e3884`. Passes 49, 50 and 51 each found more in the previous pass's repairs than in the work
being repaired, so that is the expected shape here too.

The repairs, in the order I rate their risk:

1. **The field-level expectations** in `worker_conformance.mjs` — `ORACLE_PLANES` and the
   per-criterion assertions that replaced the shape checks your B2 defeated.
2. **`createInspector`** in `card.js` — the request lifecycle extracted from `app.js` for B1 and
   B5, and the `app.js` adapter around it.
3. **`admissible.py`'s** new rules: `evidence_of_a_walk` (A1), the destination identity check and
   permitted set (A2), `route_identified` (A3), and `metres_between`.
4. **`minutesText`** (B3) and the destination disclosure change in `handleExplainAt` (B4).
5. **The multi-criterion rendering checks** in `card_selftest.mjs` (B6).
6. **The visitation guard** on the digest buffers (B9).
7. The two new sheet columns and the four committed CSVs they were inserted into.

## The claims to attack, hardest first

1. **"Every explanation field is now compared with the byte it reports."** `ORACLE_PLANES` reads
   the plane files a second time and the per-criterion block compares status, value, horizon, flag,
   verdict name and the whole destination record. **Find a sixth corruption of `handleExplainAt`
   that still passes.** You found five; I claim the class is closed. Attack that. Consider in
   particular: fields I compute an expectation for rather than read (the `bounded` set, the
   `VALUE_NONE` rule, `enabledNames`/`enabledDiscloses` for a `withhold_flags` case), the
   `enabledOracles`/`enabledTables` index walks, and anything in the reply that no assertion
   mentions at all.

2. **"`createInspector` makes a stale or superseded reply unrenderable."** Three dimensions:
   `reqId`, `pointerGen`, and `seq` against `displayedSeq`. **Find a sequence of
   `pointerAt` / `pointerLeft` / `computeStarted` / `computePainted` / `reply` calls that renders
   an explanation the page should not show, or that wedges the card shut so a legitimate reply
   never renders.** The second failure mode matters as much as the first. Also check the `app.js`
   adapter: `post`, `explainSentAt`, `clearCard`, `cardAwaitingCompute`, and whether anything the
   inspector decides is contradicted by what `app.js` then does — including `resetAll`,
   `autoBench` and a worker `error` message mid-flight.

3. **"A walk can no longer disappear from the refusal record."** `evidence_of_a_walk` over
   `EVIDENCE_FIELDS`, and `sort_records`'s three buckets. **Find a sheet row that reaches an
   `E3Result` as neither a scored observation, nor an `Inadmissible`, nor
   `without_a_published_time`** — or one whose bucket misdescribes it. Consider: a row where only
   `route_followed` is filled; `walked_seconds = "0"`; a row with `walked_seconds` and no
   `encoded_minutes`; `destination_qualifies = "no"` as the only evidence; and what
   `score_e3`'s own `walked`/`planned` counts then say.

4. **"The destination identity check establishes identity."** `DESTINATION_IDENTITY_M = 600.0`
   measured from the **selected place's** coordinate. Is 600 m right? I justified it as "a place
   is within 300 m of its node, so two places on one node are within 600 m of each other" — check
   that reasoning against `fetch_places.py`/the snapping code, and against the real side table in
   `v2/spikes/g3-render/fixtures/published/`. Then: can a walk to a genuinely different shop pass
   it, and can a walk to a legitimately permitted alternative fail it?

5. **"Disclosing a destination per criterion is the right rule."** B4's fix changed what a
   household is shown at an excluded cell: the passing criterion's shop is now named. Attack the
   decision, not just the code. Does naming a grocery at a cell the region excludes mislead? Is
   there a case for the suppression policy I removed, and if so what should the card say instead?

6. **"The 0.388-row figure and the narrowed benchmark conclusion are now honestly stated."** Read
   `card.js`'s `cellForLonLat` docstring and `bench_explain.mjs`'s output text. I attribute 0.388
   to you and say it was not reproduced here. Is what I wrote accurate about your finding, and is
   anything still overstated?

## My own suspicions

1. **The `withhold_flags` path.** `enabledDiscloses` and `enabledNames` both fall back to `false`
   for those cases, and `plainManifest` strips `dest_file` as well as `flag_file`. I think that is
   right but it is the one place where the expectation is computed from the *case* rather than
   read from the artifact, so it is where a wrong expectation would hide.

2. **`route_identified` and `duration_timed` are self-reports.** You settled that a false `yes`
   cannot be caught. But is there now an *inconsistency* check worth having — a row claiming
   `route_identified=yes` with a blank `route_followed`, or `duration_timed=yes` with a
   suspiciously round `walked_seconds`?

3. **I inserted columns into four committed CSVs twice in one day.** An owner with a copy of the
   sheet now has a file whose header differs from the generator's. I said regenerating is not an
   appropriate migration. Is there a defect in how I did it, and what should the migration be?

4. **`minutesText` at `value = 1`.** "more than 0 min" is true and useless. Is there a better
   sentence, and is the `value <= 0` branch reachable at all given how the bound is encoded?

5. **The card still has no multi-criterion REAL data.** The fixtures are hand-built planes. I
   think this is irreducible until a second layer ships, but say if it is not.

## Output

For each finding: a label, the file and line, **a concrete counterexample or witness**, the
severity, and what it would take to fix. Rank by severity. Say which of my six claims survive and
which do not, and which suspicions you settled in which direction. If a claim survives, say what
evidence is still missing.

Do not fix anything. Report.
