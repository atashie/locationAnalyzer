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

## A sixth instance, 2026-11-10: the fixture could not see its own mutation

Recovering which grocery the layer routed each household to (`aeef909`). The snapping fixture
existed to check that the destination comes from **the endpoint whose time was actually reported**,
and I wrote a mutation harness to confirm it: swap `e_idx` for `s_idx` and a test should fail.

It did not fail. The fixture hung a *penalised* shop off the far endpoint, which made that
endpoint's own cheapest path route back through the near endpoint to the **same shop**. Both
endpoints selected one destination, so which endpoint won was unobservable. The test exercised the
branch and could not see it.

The fix is not a better fixture, it is a fixture **whose discriminating property is asserted**:

    def test_the_two_endpoints_select_different_shops():
        """Guards the fixture itself. If this ever fails, the branch tests below have stopped
        being able to detect a flipped endpoint and are passing for the wrong reason."""

**When a test's power depends on a property of its fixture, assert that property in its own test.**
Otherwise the fixture can drift into degeneracy and every test built on it keeps passing — louder
than before, because the suite is now larger.

The same run produced two more of this shape, both recorded in
[[project-phase1-s3-audit-destination-recovery]]: a guard that is **unobservable through the public
API**, so no behavioural test could ever reach it (kept, with its test moved to where the invariant
lives); and two mutation harnesses whose "restored byte-identically" check compared decoded text to
decoded text and therefore could not see line endings at all — see
[[reference-text-io-rewrites-line-endings]]. That one is the purest form of the pattern in this
note: a check written specifically to catch a tool corrupting a tracked file, which could not fail.

## A seventh instance, hours later: the fixture guard guarded the wrong property

The sixth instance above ends with the rule *when a test's power depends on a property of its
fixture, assert that property in its own test*. I did exactly that, adding

    def test_the_two_endpoints_select_different_shops():

and Codex pass 33 then defeated the suite anyway. **Naming the endpoint chosen by *time* while
reporting the seconds chosen by *cost* passed all 17 tests.** Different shops behind the two
endpoints is not the same as the two selection rules *disagreeing about which endpoint*, and on
that fixture they agreed. I had written the guard for the degeneracy I had just been bitten by,
and the live degeneracy was its neighbour.

The repaired version builds a fixture where cost and time genuinely disagree -- an expensive road
whose far endpoint is quick -- and asserts `time_pick != cost_pick` inside the test that depends on
it. That defect was the one with real consequences: the sheet would have printed our cost-selected
seconds beside the time-selected shop, so a person walks to a shop our number is not about and the
gap reads as a product error.

**The rule to add, and it is uncomfortable because it has no stopping point:** a fixture guard
asserts a property, and the question is always whether that property is the one the test's power
rests on. Writing the guard converts an unexamined assumption into a stated one, which is progress,
but a stated assumption can still be the wrong assumption. What actually settles it is the
mutation, every time. In this session the mutation harness is what found both the sixth and the
seventh instance; the reasoning found neither.

Two more from the same pass, both about checks rather than fixtures, and both in
[[project-phase1-s3-audit-destination-recovery]]:

- **A check that samples where the artifact is known to agree measures nothing.** I verified a
  rebuild against the committed raster on 35 sampled rows, all 35 matched, and wrote that the
  result "belongs to the published numbers". The full surface disagrees on 7,246 of 330,502 cells
  and none of the 35 is among them -- the sampler had no reason to pick changed cells. See
  [[project-phase1-s3-stale-walk-raster]].
- **Comparing counts and reading it as comparing sets.** Three matching integers were treated as
  establishing that a 510-node destination set was the published one. Codex swapped one node for
  another, preserved every sampled value, and changed 1,798 node times.

Related: [[feedback-a-fixture-is-exact-only-where-you-point-it]], which is the same error one level
up — a test drawn from the wrong domain also passes without establishing anything. In this session
that one recurred too: the fixture "proving" an `OFF_NETWORK` bound drew access distances from
`[0, 200]` m, the range in which a cell is *not* off-network at all.

## An eighth instance, 2026-11-10: the guard against an unchecked claim was itself an unchecked claim

The `vehicle` defect existed because the code's rules and the data's contents were two separate
claims with nothing comparing them. I wrote a guard: a manifest beside the graph cache declaring
which OSM way tags it was parsed with, refused before the graph is read, with eleven tests and a
docstring explaining why it mattered.

Codex pass 35 wrote a valid graph and manifest, replaced **only the graphml** with a graph lacking
`vehicle`, and the guard accepted it. The manifest declared a tag set and nothing said *which file
it described* — so the fix had the shape of the bug, one level up. See
[[project-phase1-s3-extract-tag-gap]].

Three of the tests also died: one rejected a missing `surface` and waved every other missing tag
through; one called `load_graphml`, swallowed the exception and then validated, which my
"refuses before reading" test could not see because it monkeypatched a function that *raises*
rather than one that *counts*; one loaded a valid graph twice. Each is a failure I had not
pictured, and each passed a test written by picturing failures.

Then the mutation harness I wrote to catch those found a twelfth survivor the twelve repaired tests
still missed: **ignore the graph's sha256**. Every swap test I had written changed the file's length
as well, so the cheap size check caught them all and the digest check was never exercised. One
equal-length byte change closes it.

**The compounding rule.** Each layer of this was a check whose power I could not see without
attacking it: the rule against the data, the manifest against the file, the tests against the
implementation, the tests against *each other's coverage*. The honest summary is that **writing a
guard moves the unexamined assumption rather than removing it**, and the only thing that has
reliably located it in this project is an adversary — human, agent or mutation harness — trying to
get past it. Eight instances now, four of them inside two days.

## A ninth instance, 2026-11-11: a plan whose own invalidation condition it failed to run

Codex pass 37 reviewed the step 4 plan — a plan, nothing built. Four High findings, and the first of
them tripped a condition the plan had written down itself:

> **4a turns out not to close W2.** [...] if an exact projection still produces a wrong argmin on
> some witness, the item is wider than arithmetic and T3 stays gated.

I wrote that sentence and then did not test it. Pass 37 did, and produced the witness in one try:
two records whose exact costs differ by `4.1e-17`, where the plan's arithmetic makes them tie and
the time discriminator then reports **1 s PASS** against the real answer of **994.11 s FAIL**.

The shape is the usual one, one level further up than pass 36's: **a guarantee about intermediate
quantities reported as a guarantee about the decision that consumes them.** Correctly rounding every
operand says nothing about their ratio. I had even written the honest version of the limit —
"exact where the quantity is rational, exactly-rounded where it is algebraic... not exact
throughout" — and then drew the conclusion that the gate was closed, which that sentence does not
support.

Three more in the same pass were cheaper to find and should have been free:

- **Two of my own sentences contradicted each other four lines apart.** 4b.2 named "two CSR
  matrices, cost for selection and time for reporting" as the architecture; 4b.3 required both
  objectives first-class. The production pair is *one cost-selected view* and erases objective 1.
- **A fixture's expected value was inverted against the rule adopted in the same table.** W1's
  "required" answer was the one that follows from the summation the table rejects. The adopted rule
  leaves W1 at its current value, so the fixture as written would have failed on day one.
- **"`fsum` cannot reach W2" was too strong**, and W2 was load-bearing for the choice of method.
  Reassociating before rounding reaches it exactly.

**What this instance adds to the rule.** The previous eight were all about guards and measurements.
This one is about a *plan*, and it is the cheapest of the nine by a wide margin: the cost was a
rewrite of a document, not a correction to published figures or a rebuild. **An adversarial pass on
a plan buys the same class of finding at a fraction of the price**, which is the argument for running
one before the first line of code rather than after the last. Nine instances now.

## A tenth, 2026-11-12: reaching past a sufficient reason for a stronger one

Codex pass 38 F2. The adopted same-edge rule is right and the measurement that settles it was
already in hand: subtracting two rounded prefixes gives `0.0` on W3 and loses the traversal
entirely, against 558.7935 s for the span. Having measured that, I wrote into the normative design
that the alternative was **not implementable**, because a prefix arclength is a sum of square roots
and so "not representable as a `Fraction`".

Wrong twice. The step 4 plan's own rule had defined its two prefixes as the *exactly-rounded* ones,
and every binary64 is a rational, so subtracting them exactly was immediate — the rule as written
was implementable all along. And "not a `Fraction`" is not "not representable": a finite sum of
rational radicals is an exact algebraic expression, and the review cancelled W3's common irrational
part symbolically to recover the `1.862645149230957e-9` m gap.

**This is a different shape from the first nine.** Those over-generalised a narrow measurement into
a broad guarantee. This one keeps the measurement accurate and *replaces* it with a stronger
argument that is false — an impossibility claim where a "this is wrong here" claim was already
sufficient and already verified. The tell is the same in both: a sentence that would be more
impressive if true, written without being checked.

**How to apply:** when a measurement already decides a question, state the measurement as the
reason. If a stronger reason occurs to you, it needs its own evidence before it goes in the document
— and it buys nothing, because the question is already decided. Ten instances now, and the same
pass found three more of the ordinary kind in the same artifacts: a blanket "every comparison that
decides something" that swept in two §2.2 predicates it had never been checked against, a counter
named `parameter_differs` that compared rounded images of the parameters, and a mutation harness
that counted a crashing mutant as caught.

## An eleventh, and the shape is now specific enough to catch: the summary sentence

Codex passes 38, 39 and 40 each found the same thing in the same place. Not in a measurement, not in
a guard, not in a rule -- in the **short confident clause written to round off a section**.

| pass | the summary sentence | what the section's own tables said |
|---|---|---|
| 38 F1 | "every comparison that decides something made on the exact value" | the caps and the 0.01 m band are compared in binary64, and nobody had enumerated them |
| 38 F4 | "the adoption changes no candidate set" | true of places and counts; the normative occurrence identity changed on 67.85% of points |
| 39 R1 | "decided on the correctly-rounded residual, under both the production path and T0's exact path" | production uses GEOS, measured one ulp out |
| 39 R4 | "a provenance finding, not an answer finding" | an identity difference reaches a reported number, 512 s apart at an admissible weight |
| 39 R4 | "the largest displacement anywhere is half a nanometre" | the retained candidates move 36 um, three paragraphs further down the same document |
| 40 F7 | "T4 contains no near tie" | the margin **from the minimum** was measured; a fixture holds pairs 2 ulps apart above it |
| 40 F8 | "the convention always selects B" | the class had no time field; the selection was supplied, not derived |

Seven instances, three consecutive passes, one grammatical position. The detail was right every
time. **The generalisation written on top of it was wrong every time.**

**How to apply, and this is cheap enough that there is no excuse.** A sentence that generalises the
table above it gets checked against that table before the commit, not against the intention that
produced it. Three questions, in order: what is the subject of this sentence; what did I actually
vary or enumerate; and is the first wider than the second. If the sentence contains "any", "every",
"no", "always", "anywhere" or "nothing", assume it is wider until shown otherwise.

Eleven instances now. The first nine were about over-generalising a measurement and the tenth about
reaching past a sufficient reason; this one is about **where** the error lands, which is the part
that makes it findable.

## A twelfth, 2026-11-12: an abstraction asserted to be faithful, and a plan I did not reread

Codex pass 41 F1. Phase 4b.0 had to decide whether section 2.4's ranking is implementable by a
label-setting search. I built the experiment on a plain weighted digraph and wrote, as the reason it
was legitimate:

> "The geometry, attachment and connector layers contribute terms to a journey's totals and nothing
> to how a search prunes."

That sentence is the whole load-bearing structure of the spike, and it is false. Section 2.4 ranks
the **once-rounded total of all formed terms**, so the constants added at the ends decide *which
prefix differences survive*. Two prefixes differing strictly in cost can land on the same final
binary64 cost once the entry, exit and connector terms are added, and the travel-time key then picks
between them -- on a prefix any pruning search has already discarded. The reviewer built it from real
`ToyGraph` objects: both journeys cost exactly 2003, one takes 1,004 s and the other 5 s, and at a
600 s threshold that is PASS against FAIL.

**The part that stings is that my own plan said so.** Its 4b.0 paragraph reads: *"A prefix that is
strictly more expensive at a merge can join the final rounded-cost tie after a shared suffix and win
it on time; once pruned it cannot be recovered."* I then built an experiment about **equal-cost**
prefixes -- a tie-break problem -- and reported that the gate was too strong. The plan was right, the
spike contradicted it on a weaker model, and the review restored the plan.

**A second defect of the same kind, one layer down.** The spike's "exhaustive oracle" accumulated
`c + ec` edge by edge, which is the rule the searches under test also used -- so oracle and search
agreed with each other while both departed from the design. On costs `(2**53, 1, 1)` repeated
addition gives 9007199254740992 and the whole-journey `fsum` gives 9007199254740994, and the
normative winner changes. **An oracle that shares the defect it is checking is not an oracle.**

**What distinguishes this from the previous eleven.** Those were claims stated wider than the
evidence -- mostly in summary sentences. This one is a **modelling assumption asserted as a fact**,
and it is more dangerous, because every number the experiment produced was correct *about the model*
and the model was the error. The 3.64% reproduces exactly. It simply measures the additive problem,
which is not the rule.

**How to apply.** When an experiment replaces the real object with a simpler one, the sentence
justifying the substitution is a claim that needs evidence like any other -- and the cheapest
evidence is to reread the document that defined the problem, because it may already contain the
counterexample. Before building a spike: quote the gate's own wording into the spike, and check the
experiment against that wording rather than against your summary of it. Had I pasted the plan's
sentence into the script, the mismatch would have been visible before the first run.

Twelve instances now.
