# Codex review, pass 54 — the closing round: is this work fit for its purpose?

**This is not an adversarial defect hunt, and that is deliberate.** The owner asked for a final
round after five consecutive passes, and a sixth hunt on the same surface is the lowest-value
thing you could do with this budget. What is wanted is a **fitness review in the shape of pass 25**
— whose report is at `docs/research/32-*` and which is the most valuable pass in this project's
history, because it judged eleven passes of apparatus "disproportionate and elaborating the wrong
axis" and produced `docs/plans/2026-11-04-s3-execution-plan.md` §0's ordering rule.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at `477bc2f`.
Python: `v2/.venv/Scripts/python.exe`.

## Runtime note

Your sandbox cannot start processes: every `exec_command` fails with `windows unelevated
restricted-token sandbox cannot enforce split writable root sets`. See
`docs/engineering-notes/reference-codex-runtime-quirks.md`. You can read any file and run
JavaScript through `node_repl`. For Python, reason from source and **say what you could not
execute**. Report to stdout as your final message.

## The facts, so you are judging the same thing I am

Since `4a3b926` committed the per-criterion card plan: **8,997 insertions across 57 files.** By
area:

| added | what |
|---:|---|
| 4,773 | tests and mutation guards |
| 2,201 | product and script code |
| 1,135 | Codex reports and prompts |
| 888 | other docs and notes |

Current verified state: 1,519 tests passing, 24 skipped; 87 browser conformance checks; 33 card
checks; 69 of 69 worker mutations, 29 of 29 card, 30 of 30 admissibility, 9 of 9 migration — 0
inert, 0 misplaced, 0 errored.

Five passes, each finding more in the previous pass's repairs than in the work repaired: 49 (11
findings), 50 (14), 51 (12), 52 (10), 53 (11). All integrated.

**And the page has never been rendered in a browser.** No browser has been reachable from any
session that built it. The three disclosures `docs/s3-decision-report.md` says a household is owed
are closed in logic and shown to nobody.

## The question

**Is this body of work proportionate to the product's purpose, and what is the highest-value next
action?** Answer that first and at length. Read `docs/engineering-notes/project-phase1-s3-progress.md`
(the live state), `docs/s3-decision-report.md` (what a household is owed), and §0 of the execution
plan (the ordering rule). Specifically:

1. **Has the card actually retired product risk, or only defect risk?** §0 orders by product risk
   retired. Five passes have hardened `explainAt`, the card's words, the walked-record predicate
   and a sheet migration. Argue the case *against* that having been the right use of the effort,
   as strongly as you can — and then say whether you believe it.

2. **I claim the highest-value unblocked item is now rendering the page in a browser** (queue item
   3, which also covers the unmeasured Mercator-vs-latitude placement). Attack that. Is there
   something cheaper or more decisive? Consider in particular: the owner's single repeat walk of
   `band15min_pass-03`, which the E3 record still has no admissible observation for; the grocery
   definition, which changes every published number; and step 4's comparator, which gates verdict
   impact.

3. **What in this work is apparatus that should not have been built?** Name specific files or
   checks that cost more than they are worth, and say what you would delete. §0's standing rule is
   "no more apparatus without a named product risk"; judge the last five passes against it.

4. **What is the cheapest thing that would most reduce the chance the product tells a household
   something false?** It may be none of the above.

5. **Is there a product risk nobody in this chain has looked at?** Five passes have examined the
   same surface. Say what is unexamined — not unhardened, *unexamined*.

## A last defect sweep, secondary

After the above, and only after: a final look at the pass 53 repairs for anything materially wrong.
`admissible.py`'s `walk_happened` / `WALK_ONLY_FIELDS` / `PREPARATION_FIELDS` split and the
per-member destination match; `card.js`'s `createInspector` and `requestFailed`;
`scripts/migrate_audit_sheet.py`; the three-layer conformance group; and the four mutation runners'
new landing-site and ERROR gates. Report anything High you find, and do not manufacture findings to
fill the section — "nothing material" is an acceptable answer and a more useful one than a
stretched finding.

## My own position, which you should attack rather than accept

* I think the chain stopped paying for itself around pass 52, and that I continued it because each
  pass kept finding real things rather than because the things it found mattered to a household.
* I think the single most useful hour available is opening the page in a browser, because every
  disclosure is unverified at the only layer a person meets.
* I think the walked-record work was worth it — it is the one check that consults the world — but
  that its last two rounds were about my own apparatus rather than about the record.
* I am not confident the card's `destinationAt`-at-excluded-cells policy (pass 51 B4) is right,
  and you called it defensible but unevidenced twice.

## Output

Prose, not a findings table, for the fitness part. Be concrete: name files, name the next action,
say what to delete. Then the defect sweep, labelled, with severities. Say explicitly where you
disagree with my position above.
