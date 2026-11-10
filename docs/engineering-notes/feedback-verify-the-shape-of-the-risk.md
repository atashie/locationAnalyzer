---
name: feedback-verify-the-shape-of-the-risk
description: "A check that does not fail in the way the change can fail proves nothing - ast.parse was run against a missing-import risk, and a guard built from a loose substring match skipped silently instead of erroring"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-09T00:00:00.000Z
---

Two failures in one afternoon, same cause, found by Codex pass 29
([[project-phase1-s3-step0-audit-harness]]).

I routed two spike builders through a writer so their rasters would carry an encoding stamp. The
patch script guarded the new import with `"layer import" not in s` — and that substring already
appeared in the file's existing `from locfinder.traveltime.layer import build_layer_seconds`. The
guard read False, the insertion was skipped, **no error was raised**, and the builder shipped calling
a function it had never imported. It would have crashed after saving new seconds and left the
previous raster in place: contradictory artifacts, worse than the unstamped output it replaced.

Then I verified the change with `ast.parse` on five files and reported "all parse". A missing name
parses perfectly. **The check could not fail in the way the change could fail**, so passing it said
nothing at all — and it read as diligence in the transcript, which is the part that makes this worth
recording.

**Why:** a verification step earns its place by being able to fail for the reason at hand. Syntax
checking a change whose risk is resolution, or asserting a substring is absent when a longer string
containing it is present, both produce a green signal that is unconnected to the thing being
established. The second is worse than no check, because a guard that silently skips leaves no trace
while an absent one at least leaves the work visibly undone.

**How to apply:**

- **Name the failure mode, then pick the check that exhibits it.** Missing import or typo'd name →
  `pyflakes` / `ruff --select F821`, or import the module. Wrong arithmetic → run it on the
  counterexample. Wrong file written → read the bytes back. Syntax is almost never the risk.
- **In a patch script, assert on the exact thing being added**, not on a loose proxy for it.
  `"from x import y" not in s` guards an insertion of `from x import y`; `"x import" not in s` guards
  nothing and matches by accident.
- **Prefer a guard that raises over one that skips.** The assertion-guarded patch pattern
  ([[project-phase1-s3-step0-audit-harness]]) works because a mismatch *stops* the script before
  `write_text`. A conditional that silently declines to act has the opposite property, and I used
  one for an insertion that mattered.
- `uv run --with pyflakes python -m pyflakes <dirs>` needs no project dependency and takes a second;
  it is now the check after any edit that moves or adds a name. `ruff` is not installed here.

**It happened a third time, twenty minutes after this note was written**, which is why the rule needs
to be a habit rather than a paragraph. Waiting on a background review, I armed
`until ... | grep -qE "Phase: done|completed"` against a status command whose output also lists
*previous* jobs — one of which was completed — so the wait returned immediately and I reported a
review finished that was ninety seconds into a nine-minute run. The fix is the same shape as the
others: anchor it. `grep -qE "^[[:space:]]*Phase: done[[:space:]]*$"` matches that job's own phase
line and nothing else. **When a pattern is a stop condition, bound it to the line and the field you
mean**; an unanchored alternation against multi-record output is a loose proxy, exactly as
`"layer import" not in s` was.

**A fourth instance, and this one I had explicitly certified.** Codex pass 31
([[project-phase1-s3-step2-conditional-estimand]]). I wrote a script to recompute every figure
quoted in a design amendment and assert each appears in the text, then tested it by changing
`7.3358%` to `7.3359%`, watched it fail, and wrote in the commit message that it was "shaped like the
risk". Pass 31 then defeated it three ways: **swapping two whole table rows passed** (every figure
was still present, on the wrong row), **deleting the entire interval-method passage passed**, and
**flipping the estimand's conditioning event from product PASS to product FAIL passed**.

The lesson is not "add more checks". It is that **presence is not association**, and that I had
tested the check in the one way I had imagined it failing — the same mistake as the fixture drawn
from the wrong domain, one level up. A single-digit perturbation exercises the figure-drift path and
says nothing about the structural paths.

**The durable fix is to make the ability to fail executable.** The rewrite parses the table so each
figure is bound to its row, asserts the passage's required claims so deletion fails, and carries a
`--self-test` mode that applies those mutations and fails unless each is caught. **When a check
guards a document or an artifact, put the mutations in the check** — then "it can fail the way the
change can fail" is a thing the script proves on demand rather than a claim in its docstring. And
state what it still cannot see: that script reuses the module it checks for its arithmetic, so that
part is consistency, not validation.

**A fifth instance, in the rewrite itself, which is the part worth keeping.** Codex pass 32 then
defeated the *fixed* checker three more ways: swapping the frame B and frame C **column labels**
passed, because binding a figure to a *position* says nothing about what the position means;
replacing the specified **formula** passed, because no check bound it; and exchanging two bounds
between their frame/threshold **cases** passed, because those were still presence searches. So
"presence is not association" was only half the lesson — **binding by position is also not binding by
meaning**, and the three defects I had fixed were the three shapes I had just been shown. The
generalisation I keep failing to make in advance is: *enumerate the ways the artifact can be wrong,
then check each, rather than checking the ways it was last wrong.*

Two more from the same pass, both about guards rather than figures:

- **A guard that is present but untested is absent the moment someone simplifies it.** Removing the
  non-negativity check, removing the confidence check, and dropping `confidence` from the two bound
  calls each survived **all 146 tests** of the module they live in. A guard needs a test that fails
  when it is deleted, and the cheap way to know is a mutation harness that deletes it.
- **A checker that mutates the artifact it checks can corrupt it.** `--self-test` wrote mutations to
  the tracked document and restored from a fixed shared temporary path, so concurrent runs could
  restore each other's mutated text and a forced termination could leave a mutation committed. It now
  mutates a private copy. **A verification tool must not be able to damage the thing it verifies.**

Related: [[feedback-a-fixture-is-exact-only-where-you-point-it]], which is the same error one level
up — a test drawn from the wrong domain also passes without establishing anything. In this session
that one recurred too: the fixture "proving" an `OFF_NETWORK` bound drew access distances from
`[0, 200]` m, the range in which a cell is *not* off-network at all.
