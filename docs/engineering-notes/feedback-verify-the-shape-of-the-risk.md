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

## Thirteenth and fourteenth, 2026-11-13 -- the first two caught before publication

Building the suffix-aware band produced two claims of exactly the twelfth instance's shape, and
both were caught before they reached a document.

**The band's price was about to be an artifact of my queue.** The first implementation used a DFS
stack and re-expanded a node on every improvement. On 16 diamonds it reported 655,354 expansions
for 442 retained labels, and the shape of that series is exponential. I was one paragraph from
writing "the band's retained set is cheap but its work explodes". Ordering the queue by
`(cost, time, route)` -- which is non-decreasing along any path, so a key is final when first
popped -- gives 884 expansions for the same 442 labels. **The retained set was identical.** The
exponent belonged to the queue discipline, not to the band, and an exponential figure that an
ordinary fix removes is not a property of the thing being measured.

**The precondition's docstring asserted a mechanism that measurement contradicted.** I wrote that a
cycle costing less than the band width makes "the retained set not finite". Planting a zero-cost
two-way edge in 400 graphs showed otherwise: 363 answers, all flagged by the check, **zero** wrong
on cost, time or destination, 8 wrong on the route sequence, and nothing unformable. The real
mechanism is narrower and more interesting -- a zero-cost cycle makes one route a proper prefix of
another at a merge, which is the one condition pass 41 F4's dominance argument forbids -- and the
numbers are safe for a reason rather than by luck, since a zero-cost cycle cannot lower a time.

**What is different about these two.** Both were asserted in a docstring before anything was run,
and in each case running the thing took minutes. The twelfth instance's habit -- quote the claim
into the experiment and check it -- works, and it works earlier than I had been applying it: not
only for the gate the spike is about, but for every mechanism sentence the spike itself writes
down. A docstring is not a safe place to put an untested claim. It is the place a reader will
believe one.

Fourteen instances now.

## Fifteenth to seventeenth, 2026-11-13 — pass 42 on the band

**Fifteenth, and the worst of the three: the recommendation broke the design's own central
distinction.** I recommended sizing the band's width from "the query's own ceiling", meaning the
travel-time threshold a query carries. The design's first principle is *selection is by cost,
reporting is by time*, and `cost = travel_time + access penalty`. A threshold on the reported time
is therefore not a bound on cost, and a band sized from one is not sound. Scale the witness's costs
by sixteen and leave its times alone: the rule says 5 s, the band sized from 600 s says 1,004 s,
and PASS becomes FAIL. The repair was easy — use the cost of a journey that exists, which the
argmin cannot exceed — but the mistake is not a slip. **It is the one conflation this whole design
exists to prevent, made in the sentence that told someone what to build.**

**Sixteenth: a classification asserted rather than checked.** I wrote that item 6 "stands exactly
as written" because the band "is not a prefix-pruning search". It is one: it prunes prefixes on a
threshold that happens to be suffix-aware, and two lines of its own code drop a cost-2 prefix
beside a cost-1 one. Retaining *some* strictly costlier prefixes does not change what the search
is. Note what the wrong classification bought me: it let the design stand unchanged. A claim that
conveniently removes work is the one to check first, and this one took a four-line reproducer.

**Seventeenth: the adversarial family was adversarial in only one direction.** I priced the band on
diamonds whose arms differ in *cost*, which gives each merge `k + 1` cost buckets each holding one
time — a family in which the second band provably cannot cost anything. Give the arms **equal**
costs and distinct times and the same construction retains `5·2ᵏ − 3` labels: 20,477 at `k = 12`
where one band holds 38. "Exact cost ties cost the band nothing" was true of what I measured and
false of what I claimed. A worst case has as many dimensions as the thing has keys, and I varied
one of two.

**How to apply.** Two habits, both cheap. Before recommending a quantity as a bound, write down
what it is a bound **on**, in the design's own units, and check that against the design's defining
equation — not against your sense of what the quantity means. And when a result says a cost is
zero, ask which key the family varied; if the mechanism has two keys and the family varies one,
the zero is about the family.

Seventeen instances now.

## Eighteenth to twentieth, 2026-11-13 — pass 43 on the browser path

**Eighteenth, and it is the sharpest one yet: I wrote the lesson into the review prompt and broke
it in the same commit.** The prompt for pass 43 says, of the order-independence check, *"a check
that has never caught anything is not evidence"*. In the same commit I shipped a conformance
harness that compared **nothing** on three quarters of its cells, nothing at all on the real-layer
window, and computed a digest it then checked only for being a 32-character string. Two wrong
decoders passed all 37 of its checks — one returning UNKNOWN for `NO_PATH`, one **rotating the
entire raster by 10,007 cells**, which moves 13,695 verdicts.

The cause is worth naming precisely, because it was not carelessness. I reconstructed verdicts from
the RGBA buffer, where INCLUDED is readable from the mask but EXCLUDED and UNKNOWN are
distinguishable only where the hatch stripe falls. I **knew** that — there is a comment in the code
saying so — and I wrote the skip-list as a limitation rather than as a hole. A limitation you
accept in a correctness check is a hole; the right move was to make the worker report what it
decided, which took nine lines.

The repair is `mutate_worker.mjs`: nine known-wrong decoders, each of which must be caught, with a
mutation whose edit matches nothing reported `INERT` rather than banked as a catch. It immediately
caught three of my own anchors failing against a CRLF working tree. **A check that has never caught
anything is not evidence — including when the check is mine and the thing it is checking is a test.**

**Nineteenth: the size baseline measured the wrong baseline.** "It costs 9%" compared v2's two
planes against **v2's own value plane**, which carries a lower bound at every missing cell. v1
stored a constant there, and a constant compresses far better than a bound. The true figure is
18.2%, and 31 KB rather than 17 KB. The number was computed correctly; it was a comparison against
a thing that never existed.

**Twentieth: "the peak" was a property of the four numbers I printed.** I reported thresholds
10, 15, 25 and 45, observed that 15 was the largest, and wrote that the error "peaks at 15 minutes
… that is where the most structures sit near a boundary". Sweeping every whole minute the slider
can produce puts the maximum at **14**, and the explanation about boundaries was never measured at
all. This is the summary-sentence failure from instances one to eleven, in a new place: a
superlative over a sample described as a superlative over the range.

**How to apply.** Before claiming a check establishes something, break the thing it checks on
purpose and confirm it fails — and keep that mutation as a file, not as a thing you did once.
Before quoting a ratio, write down what the denominator **is**, in bytes or rows, and confirm that
artifact exists. And never write "peaks at X" from a list of four; either sweep the range or say
"largest of the four reported".

Twenty instances now.

## Twenty-first, 2026-11-13 — pass 44, and the same failure three times running

The eighteenth instance was a conformance harness that could not fail. The repair for it was a
mutation guard — thirteen wrong decoders that each have to be caught — and **the guard could not
fail either**. It counted every non-zero outcome as a catch, including `status: null` from a spawn
error. In the reviewer's session `spawnSync` returned `EPERM`, and the gate printed *"9 of 9
mutations caught"* having executed **no mutated decoder at all**.

So in three consecutive passes I built: a check that compared nothing on most of its cells (18th),
a guard for that check that was green when it did not run (21st), and in between, a mask assertion
so weak that `mask[p] = 2` satisfied it while putting 225,520 excluded pixels inside the published
polygon.

**The pattern is specific and it is not carelessness.** Each time, the check was written to confirm
the thing I had just fixed, and its *own* failure modes were never considered. A check is a program.
It has inputs it mishandles, exits it misreads, and outputs it does not look at. I was treating the
check as the place where scrutiny ends rather than as one more thing to attack.

**What the three have in common, concretely:**

* the harness read the RGBA buffer, which cannot express the distinction it was testing;
* the guard read an exit status, which cannot distinguish "the mutant was rejected" from "nothing
  ran";
* the mask assertion read a truthiness comparison, which cannot distinguish `1` from `2` — and the
  consumer thresholds at `0.5`.

In every case a *weaker* reading of a stronger signal was available and I took it.

**How to apply.** Three questions before a check is allowed to count as evidence, and they are
cheap:

1. **What does a pass actually prove?** Name the cells, bytes or rows compared, as a number. "Every
   cell" has to mean every cell; if three quarters are skipped, the check establishes a quarter.
2. **What does a failure of the harness itself look like?** Make the not-run case a distinguishable
   outcome — `ERROR`, not a catch — and prove it by forcing one.
3. **Is the signal I am reading the one the consumer reads?** `app.js` thresholds the mask at 0.5;
   my assertion compared it to 1. The consumer's rule is the specification, not mine.

Twenty-one instances now.

## Twenty-second, 2026-11-13 — the cost/time conflation, twice in three days

The fifteenth instance was recommending a **travel-time threshold** as a bound on **cost**, in a
design whose first principle is *selection is by cost, reporting is by time*. Three days later I
wrote this, in the step 7 audit's own docstring:

> "Removing destinations can only lengthen a time, and adding them can only shorten one, so each
> comparison has a direction and the direction is what makes it a harm statement."

False, for exactly the same reason. The search minimises cost and reports time, so a cheaper
destination can select a slower journey. Three lines refute it: costs `(700, 650)` with times
`(500, 650)`, and adding the second destination turns 500 s into 650 s — a ten-minute pass into a
fail. Measured on the real graph, 69 structures **lose** inclusion when destinations are added.

**Why it recurred is the useful part.** Both times the sentence was about a *direction of effect*,
and both times I reasoned about the quantity I was reporting rather than the quantity the
implementation selects on. "Adding a destination can only help" is true of the minimum over
destinations. This pipeline does not take a minimum over destinations — it takes an argmin over
**cost** and reports that journey's **time**, which is the whole reason `cost_selected_category`
has its own name and the whole reason §2.1 exists.

It also let a worse error through unchallenged: because I believed the effect was one-directional,
I only **counted** one direction. The losses were not hidden by a bug; they were never looked for.

**How to apply.** Any sentence of the form "X can only make Y better/worse" in this codebase is a
claim about a monotone relationship between the **selected** quantity and the **reported** one, and
there is none. Before writing one, name both quantities explicitly — "adding a destination can only
lower the selected cost" is true, "and therefore the reported time" does not follow. And count both
directions regardless of what the argument says, because the count costs nothing and the argument
has now been wrong twice.

Twenty-two instances now.

## Twenty-third, 2026-11-13 — I wrote a verdict the project already had an instrument for

The decision report's job was to tell the owner whether real-world accuracy is supported. I wrote
**"UNVERIFIED, the owner's call"**. `locfinder/measure/e3.py` had been sitting in the repository the
whole time, predeclared for exactly this question, and on the evidence we have it returns
**FAILED** — 1.85× and 11.5 minutes over, past both of its bounds, plus a median difference past
its third.

**This is not the same mistake as the previous twenty-two.** Those were claims stated wider than
their evidence. This is a claim stated **narrower** than the evidence, and in a document whose
entire purpose was to carry that evidence to a person. I reasoned from the sample size — one
journey cannot establish a rate, therefore nothing is established — without checking whether the
project had already decided what one journey establishes. It had: the scorer is deliberately
asymmetric, because one observation can refute a claim it cannot confirm.

So the failure is: **writing a verdict by argument when a predeclared instrument for that verdict
existed.** Every adversarial pass in this project has been about not reaching conclusions the
evidence does not support; this was reaching a conclusion while walking past the thing built to
reach it. And the direction matters — "unverified" sounds cautious and is not, because it converts
a measured failure into an open question.

**How to apply.** Before writing any verdict, status or outcome into a document, grep for the
scorer. `E0`, `E1`, `E1b`, `E1c`, `E2`, `E3` and the four diagnostics all have or will have code;
if a sentence is about one of them, the sentence belongs to that code and not to me. Where no
instrument exists, say which one is missing rather than supplying a verdict in its place. And treat
"not enough data to conclude anything" as a claim needing the same check as any other — a
predeclared rule may already say what this much data concludes.

Twenty-three instances now.

## Twenty-fourth, 2026-11-13 — a scorer running is not a scorer applying

Instance twenty-three was writing a verdict by argument while a predeclared instrument for it sat
in the repository. The repair was to consult the instrument. I consulted it, fed it the one
observation we have, and reported its output — `FAILED` — as the report's headline. Pass 47:
**the scorer cannot be applied to that observation.** No recorded start door, no confirmed
destination, the private-approach question explicitly unresolved, and a duration recorded as
"closer to 25 mins" rather than timed. The audit README lists those gaps itself.

So the same sentence was corrected twice in opposite directions inside one day, and **both of my
versions were the same error in different clothes: supplying a verdict where the honest answer was
"this cannot be scored yet, and here is what would make it scorable".** First I supplied
"unverified" from an argument about sample size. Then I supplied "failed" from a function call. The
function call felt like rigour because it produced a number with a provenance, and a number with a
provenance is not the same as a measurement of the thing the number is named after.

**What I did next made it worse, which is the part worth remembering.** Challenged on
admissibility, I built an argument *for* it — the owner must have walked the detour because the
track is private — and that argument establishes what the **model** routes through and nothing
about what the owner walked. Asked to check a claim, I went looking for support for it. The
sensitivity sweep was the same reflex: it defends the conclusion against one objection (the
duration is approximate) while the actual objection was a different one (the journey is not
identified), and a sweep over the wrong axis reads as diligence.

**How to apply.** Before reporting any instrument's output as a result, state its input contract
and check the record against it, field by field — `E3` wants a reported time, an observed time, and
implicitly the same journey, and the third is the one no type signature enforces. When a reviewer
questions admissibility, the first move is to list what the instrument needs and mark each item
present or absent, **not** to construct a reason the comparison is fair. And a robustness check is
only evidence if it varies the axis the objection is actually about.

## Twenty-fifth to twenty-eighth, 2026-11-13 — pass 48 on publishing the flag

**Twenty-fifth: I cited measurement for a conclusion I had reached on other grounds, without
running the measurement.** The commit message says *"the byte argument for the bit does not survive
measurement either: the plane is 17.3% set, spatially clustered, and deflates to 25,651 bytes."*
That sentence reports a measurement of the option I chose and calls it a refutation of the option I
rejected. It is not. I never priced the bit. When priced — the flag in bit 3 of the status byte,
measured as the status plane's growth — it costs **21,096 bytes against the separate plane's
25,651**, and the whole bundle is **223,476 against 228,031**. The option I rejected is 4,555 bytes
cheaper. A packed bitmap, which keeps every property I argued for, is **22,022**, so the encoding I
shipped is the most expensive of five ways to carry the same information.

The format decision still stands, because the contract argument is the one that decides it. But
"measurement refutes the alternative" and "I did not measure the alternative" are different
sentences, and I wrote the first while the second was true. The tell was that the number I quoted
was about my own choice: **a measurement that cannot come out against you is not evidence.**

**Twenty-sixth: I corrected the artifact and not the generator.** Two statements in
`docs/experiments/s3-8-restricted-routes.json` were falsified the moment the plane shipped. I fixed
the JSON. Codex found that `flag_restricted_routes.py` still emits both, so the next run would
restore them — and the repository would then hold a published artifact that disagrees with the
script that builds it, which is worse than a stale artifact because it looks right and cannot be
rebuilt. The same block had two edge counts written as literals beside the variables holding them.
`CLAUDE.md` already says anything needed to rebuild a published artifact is committed beside it;
what it did not say, and now does, is that **correcting a generated file means correcting the
generator, and the artifact is then rebuilt or explicitly marked as hand-corrected.**

**Twenty-seventh: my fixtures made a whole class of defect unreachable, for the fourth time.**
Every conformance group carries exactly one disclosing layer. So the per-layer flag indexing is
never exercised, and Codex found two mutations that pass all fifty checks: reading every layer's
flag from layer 0, and counting a cell twice when two enabled layers both disclose. It also found
that a bundle mixing one disclosing layer with one that does not **crashes the worker**, because
the app sends `[flagBuffer, null]` and the worker reads the null slot's byte length.

This is the same shape as instances thirteen, fourteen and twenty-one: a check that cannot fail,
and in each case the reason it cannot fail is the **shape of the fixture**, not the logic of the
check. Three of those were caught by mutation testing and this one was not, because a mutation
guard inherits its blind spots from the fixtures it mutates. **A mutation suite proves the checks
discriminate on the inputs they are given; it says nothing about the inputs they are not.** So the
fixture question is now explicit: for each dimension the code indexes over — layers, thresholds,
status codes, planes — does at least one fixture carry more than one distinct value along it?

**Twenty-eighth, and it is the mirror of the twenty-fifth.** Having run two measurements, I
described both as establishing more than they do. I called a *round trip* -- reproject to the
shipped grid and back -- an instrument for "what a household reads". It is not: the return applies
a second nearest lookup that can undo the outward error, add a new one, or miss a disagreement away
from a cell centre. Codex's counterexample is two source cells re-tiled to three and back, which
restores every source value exactly while a coordinate at 0.9 still reads the wrong cell. A perfect
round trip is compatible with a wrong answer, so the figure bounds nothing. And I called "0 of
330,502 mixed triples" a proof that each shipped cell's three planes come from one source cell,
when three warped byte planes can in principle recombine into a valid index; the real reason to
expect coherence is that the three reprojections share geometry, dimensions, resampling and fill,
which the measurement then confirms.

Both conclusions survived. What did not survive was my account of *why* they hold, and in one case
the quantity I attached to it. The pattern: **a measurement that is easy to run is not thereby a
measurement of the thing you want to know**, and the round trip was easy. The forward comparison --
read each structure's source cell and its shipped pixel and compare them -- is the instrument that
answers the question, and I had in fact built it in the same script, which is why the household
figures are unaffected. So the discipline is not "measure more" but **name the question before
choosing the instrument, then check that the instrument's output is in the units of the question.**
Round-trip agreement is in units of cells; 1,316 structures silently unflagged is in units of
households.



## Twenty-ninth to thirty-third, 2026-11-14 — pass 49 on publishing the destination

Eleven findings, three High, and one of them was a **release blocker that 1,431 tests and 71
conformance checks could not see**. Five new shapes, and the first is the most useful thing in this
file.

**Twenty-ninth: a fixture is a model of the artifact, and passing on the model says nothing about
the artifact.** The published side table contained 85 bare `NaN` tokens, because `brand` and
`operating_status` arrive from the parquet as float NaN and `json.dumps` writes those as `NaN`,
which is not JSON. `JSON.parse` throws, so `Response.json()` throws, so the page could not display
a destination at all — the entire feature I had just published, dead on arrival. Nothing caught it
because **every one of the 71 conformance checks builds its own fixture**, and not one byte of the
real bundle had ever been through the harness. The fixtures were not wrong; they were not the
artifact.

This is distinct from the twenty-seventh instance, where the fixtures' *shape* made a defect class
unreachable. Here the shape was fine. The gap was that a whole category of defect — anything that
happens between the generator and the bytes on disk — lives in the artifact and nowhere else, and
I had built an elaborate apparatus that could not reach it. The check now exists: load the shipped
manifest and side table with `JSON.parse`, init the real worker with the real planes, compute, and
resolve a cell that names something. It failed on first run, which is how I know it works.

The rule: **for every artifact a consumer loads, one check must load it the way the consumer
does.** Not a copy of it, not a fixture shaped like it. It.

**Thirtieth: a positive control that can pass on the wrong cause is not a control.** I had written
`byteswap_control.mjs` precisely because I suspected a guard was decoration, and it printed
`CONFIRMED`. Codex reformatted the little-endian expression so the control's own `replace` became a
no-op — mutating nothing — then added an unrelated wrong-name defect. The control still printed
`CONFIRMED` and exited 0.

The twenty-fifth and twenty-eighth instances were about an instrument never shown to move. This is
the next failure along: the instrument moved, for the wrong reason, and the control could not tell
the difference because it asked "is some name wrong?" instead of "is *this specific predicted
thing* true?". Three conditions were missing and all three are now required: **the mutation must be
shown to have applied**, the **baseline must answer completely correctly**, and the observed effect
must be the **specific** predicted one — here ordinals exactly `1 ↔ 256`, named in the file rather
than inferred.

**Thirty-first: checking one member of a set is not checking the set, and a count is not a set.**
The conformance harness compared a destination's ordinal, its place *count* and its *first* place's
name. Four defects passed all 71 checks: renaming every place after the first; replacing every
place with a copy of the first, which preserves the count exactly; a constant `node_index`, which
nothing compared at all; and deleting one half of the two-directional invariant, which had no
refusal case while its partner did. This is sharpest here because **the set is the answer** — the
whole point of this layer is that the selection is a cost-argmin over nodes and a shared node's
places are indistinguishable to it. I wrote that down in three documents and then checked one
member of it.

**Thirty-second: allocation is not evaluation.** `state.verdict` is allocated at init and
zero-filled, and in this algebra zero means INCLUDED. The destination query guarded itself with
`if (!state.verdict) throw`, which tests whether the array *exists*. So before any compute had run,
every cell read as included and the worker named a shop for a cell no criterion had been applied
to. The general shape: **a default-initialised value that is indistinguishable from a real answer
turns "I have not been asked yet" into a confident reply.** A lifecycle flag is the fix; noticing
that zero was load-bearing was the part I missed.

**Thirty-third: a label is not the thing it names, and silence is not confirmation.** Two findings
with one shape. The side table carried SPDX licence identifiers and I wrote that the names were
"publishable with attribution" — but CDLA-Permissive-2.0 §2.1 requires *the text of the agreement*
to travel with the data, and Apache-2.0 §4 requires the licence, a modification statement and the
source `NOTICE`. "Publishable with attribution" described the licence; it was not a description of
anything the build had done. Separately, the byte-order guard refused a manifest that declared the
wrong order and **accepted one that declared nothing**, falling back to little-endian — so a plane
written the other way round was read as though its order had been confirmed. The project already
has "absence is not evidence of cleanliness" written down. Both of these are that sentence, and I
still wrote the code the other way.

### And one correction that is not an instance

Pass 49 also took apart my cost report (finding 9) in three ways at once: it priced the encodings on
the source raster while taking the other planes from the reprojected bundle, reported the total of
the bundle carrying the *cheapest* encoding as the total for the one carrying the *chosen* one, and
left the side table out of every figure. The headline moved from "4.1% of the bundle" to **20.6%**.
And the access-pattern argument was a false necessity — run-length random access needs no expanded
plane and no shipped index: cumulative run endpoints cost 173,934 bytes against the plane's 661,004
and answer every one of 330,502 cells correctly.

That is the twenty-second instance again (a measurement that mixes two populations) and the
twenty-fifth again (defending a choice with a figure about the alternative). It is listed here
rather than numbered because the shape is already in this file twice. **Both times it was a
denominator.** When a share is reported, the next sentence should name the denominator.

## Pass 50, 2026-11-14 — four of the five instances above were overstated, and three more

Pass 50 reviewed the pass 49 **repairs** and found 14 things, 4 High. The repairs were a bigger
change than the defects they repaired, and most of the new findings are in them. Before adding
anything, the corrections to what I had just written:

* **29 said "passing on the model says nothing about the artifact".** Too broad. A fixture test
  provides algorithmic evidence; what it does not establish is that the *particular shipped
  artifact* loads. The usable form is the narrower one. The consumer-equivalent check I proposed
  is also only partly built: it reads files with `fs`, not `fetch`, so it covers parsing and
  initialisation and not URL resolution, HTTP handling, cross-request staleness, `app.js`'s own
  manifest checks, or a real Worker's structured cloning. The check is renamed to "parses and
  initialises" and lists what it does not do.
* **30 was right in principle and wrong about my own compliance with it.** I claimed the control
  now enforced all three conditions — mutation applied, baseline correct, effect specific. It did
  not enforce the second: the baseline check required the ordinal to be *non-null*, not to match
  the recorded expectation, so a worker whose baseline returns 256 where 1 is expected passed,
  its mutated run returning 1 — the byte-swap of its own wrong answer. **A relative test anchored
  on an unverified baseline confirms nothing.** Fixed to pin the absolute recorded ordinals.
* **31 bundled three omissions into one.** Checking only the first member of a set explains the
  renamed-places and duplicated-places defects. The uncompared `node_index` and the missing
  refusal branch for the named-implies-OK half are *separate* omissions that happened to be found
  in the same place. Collapsing them hid two distinct lessons: compare every field you claim to
  check, and give both halves of a two-sided invariant a refusal case.
* **33's second half was imprecise.** Requiring a byte-order declaration establishes a *declared*
  order, not a verified one. Bytes incorrectly labelled little-endian pass, and nothing in a
  plane can detect that. The guard closes "silence read as confirmation"; it does not make the
  order true.
* **32 survived intact**, and immediately earned its keep: it says the shape is "a
  default-initialised value indistinguishable from a real answer", and that generalisation is
  what exposed `verdicts` and `mask` having the same hole that `destinationAt` had.

### Thirty-fourth: the oracle must not be the thing under test

The conformance harness handed the worker `group.dest_tables` and then read the *expected* record
out of that same object. Node's shim does not structured-clone, so a worker that rewrote every
`gers_id` and `licence` of the record it returned agreed with itself, and all 75 checks passed.
The whole-record comparison I added for pass 49 finding 5 was therefore comparing an object with
itself.

The browser would have cloned, so this was a property of the test harness and not of the product —
which is exactly why the harness has to defend against it instead of relying on the environment.
The fix is one line of discipline: **snapshot and freeze the expectation before the code under
test can touch it**, and hand that code its own copy. `JSON.parse(JSON.stringify(...))` twice,
`Object.freeze` recursively, and the comparison means something.

The general shape: **a check whose expected value is reachable by the code under test is not a
check.** Ask of every oracle: could the thing I am testing have written this?

### Thirty-fifth: coercion is not validation

`handleDestinationAt` read `msg.row | 0`, and `| 0` runs *before* the bounds check. So
`4294967296` wrapped to 0, `0.9` truncated to 0, and `undefined` and `NaN` both became 0 — each of
them getting a confident destination for a cell nobody had asked about, with `outside` false.

The shape is wider than this function. A coercion that maps invalid input onto a *valid* value
destroys the evidence that the input was invalid, so every check downstream of it is checking the
wrong thing. Validate first, then coerce — or never coerce, which is what the fix does:
`Number.isInteger` or it is not a cell.

### Thirty-sixth: an allowlist has to cover every entrance

The publication gate I wrote for pass 49 checked destination-entry keys and place-record keys. It
did not check the table's root keys, the keys inside the root `licence` object, or the *types* of
the values in the fields it did allow. So a phone number could ship as root metadata, an upstream
provider id inside the licence block, and a website inside an object stored under `brand` — the
last one being the sharpest, because `brand` is an **allowed** field and an allowed field holding
an unreviewed object is an unreviewed field with a reviewed name.

"No forbidden field can leave" is a claim about every path out, and I had checked two of four. The
gate now walks the whole document and refuses a non-scalar anywhere a scalar is expected.

### And the recurring one, for the third time

Pass 49's cost report mixed two grids and divided by the wrong denominator; pass 50 found a
different version of the same thing in the surface-binding gate, which compared journey *masks*
where the question was about journey *values*. Both are the twenty-eighth instance: the instrument's
output was not in the units of the question. **Mask agreement is not value agreement, and a share
is not a share until its denominator is named.**

Thirty-six instances at that point.

## Pass 51, 2026-11-14 — the card, and three more

Pass 51 reviewed the per-criterion card and the walked-record refusal. **Four of the six claims I
put up for attack failed or were narrowed**, and both of the two suspicions I asked it to settle
came back as defects rather than questions. Three new instances, and two of the old ones recurred
in the code written for them.

### Thirty-seventh: a check on the answer is not a check on the explanation of the answer

I built a total check — the per-layer outcomes `explainAt` reports must fold to the verdict
`compute` wrote, at every cell of every fixture, 720,165 cells — and then recorded Python's own
per-layer outcomes beside it after finding one blind spot myself. I thought that settled it.

**Five separate corruptions of `handleExplainAt` passed all 79 conformance checks and all 16 card
checks**: a minute of 42 for every published time, an inverted route flag, a forced `INCLUDED`
headline, every place name after the first replaced with "Fabricated Shop", and a horizon of 1.

The reason is one sentence. Every assertion I wrote bound the **outcome**: that it folded
correctly, that it matched Python, that its name matched its code. The explanation *beside* the
outcome — the minute, the flag, the headline, the destination record, the horizon — was checked
only for **shape**: that a flag was 0 or 1, that a value was not 255. An inverted flag is 0 or 1.
A fabricated minute is not 255.

> **Binding the conclusion does not bind the evidence reported with it.** Every field a reader is
> shown needs comparing with the byte it claims to report, not with a predicate it happens to
> satisfy.

### Thirty-eighth: one field cannot answer two questions

`WalkedRecord.walked` was `walked_seconds is not None`. That one expression was asked to mean both
*somebody walked this journey* and *we have a duration to compare*. When they diverged — a row
dated, with a door, a destination and a route recorded, and no usable duration — the first meaning
vanished without trace: `walked=0, planned=1`, nothing inadmissible, `no_admissible_observation`
false. **The walk disappeared from the record of what could not be scored**, which is the one
thing the module exists to prevent, and it disappeared through the convenience property rather
than through any rule.

This is the same shape as the three-state problem the module was written to fix, one level down. I
replaced a two-state scorer with a three-state predicate and then put a two-state property inside
it.

### Thirty-ninth: a rule borrowed from a different question changes meaning on arrival

`destinationAt` names no destination outside the region, because a destination beside an excluded
cell is not applicable to the question *that message answers* — the cell's combined answer. I
reused the rule in `explainAt` without re-deriving it, and recorded the choice in the plan as
deliberate.

`explainAt` answers **per criterion**. So at a cell where the walk criterion passes with a named
grocery and the drive criterion fails, the card printed *"this criterion does not say which
destination the time was measured to"* about a layer whose plane and side table both name one.
**A false claim of non-disclosure, produced by the optionality discipline that exists to prevent
exactly that confusion.** The policy was defensible where it came from and became a lie where it
was copied to.

### And two recurrences, both inside the checks written for them

**Instance 32, allocation is not evaluation — in the digest buffer I added for the real-layer
window.** The observation buffer was `new Int8Array(n)`, and zero is the `PASS` code, so a cell
that was never explained already held a plausible answer. Codex skipped real-window cell 5166, an
`OK` one-minute PASS, and all 79 checks still passed. It is filled with an impossible code now and
the absence of that code is asserted. I wrote this hole into the check whose whole job is to prove
a plane was read.

**Instance 30, a control that can pass on the wrong cause — in my own new mutation.** The mutation
for `explainAt`'s lifecycle guard anchored on `if (!state.computed) {` plus `notComputed: true,`,
text that `destinationAt` also carries earlier in the file. `String.replace` takes the first
match, so it mutated `destinationAt`, failed the destination check, and reported **CAUGHT** while
the guard under test was never touched. I noticed only because the FAIL line named the wrong
check. The pre-existing `destinationAt` mutation used a bare positional anchor for the same text,
so it would have retargeted silently the next time a handler was added above it. **A positional
anchor that can move is how a mutation starts testing something else.**

### And a narrowing worth keeping

"At least 11 minutes" was an overstatement, not a rounding detail. The value byte holds
`ceil(bound_seconds / 60)`, so a byte of 11 means the bound lies in `(600, 660]` seconds — and a
journey of 630 seconds is compatible with that evidence while taking **less** than 11 minutes.
What the byte supports is "more than 10 minutes". The ceiling was chosen so the encoded verdict
matches the float verdict at integer thresholds; it was never a literal bound in minutes, and
reading it as one claimed more than the data.

Thirty-nine instances at that point.

## Pass 52, 2026-11-14 — the repairs again, and the shape of my repairs

Pass 52 reviewed pass 51's repairs. **Ten findings, two High, and five of the six claims I put up
failed.** The fourth consecutive pass to find more in the previous pass's repairs than in the work
being repaired. Three new instances.

### Fortieth: closing the instances a reviewer gives you is not closing the class

Pass 51 found five corruptions of `explainAt` that passed every check. I fixed the class as I
understood it — compare every field against the byte it reports — and claimed it closed. **Five
more survived.** Three were response-envelope fields no assertion mentioned at all: a reply
labelled `seq: -1` (after which the page rejects every explanation it ever receives), `reqId: 0`
(every request rejected), and `row: 0, col: 0` (every correct answer labelled as another cell's).
Two were criterion-index substitutions.

The same thing happened in the Python half. Pass 51's A1 was "a walk with no duration disappears",
and I fixed it by listing thirteen columns whose presence means somebody walked. **I left out the
two that most directly mean it** — `duration_timed` and `route_identified` — so a row whose only
entry was one of those disappeared exactly as before.

> **A reviewer's counterexamples are samples from a class, not the class.** After fixing them,
> enumerate the class yourself and check the enumeration against the artifact: every field in the
> reply, every column in the sheet. "I fixed the five and generalised" is the claim that failed
> twice in one pass.

### Forty-first: a regression test written beside a fix can lock in the adjacent bug

Pass 51's B5 was "a late reply restores an inside card after the pointer leaves". I fixed it with a
pointer generation counter and wrote a test. That test asserted, as a precondition, that **the
first reply renders** — and pass 52's F4 is that the first reply must *not* render when the pointer
has moved to another cell, because the card then describes a cell the pointer has left. My
regression test asserted the defect as expected behaviour, one line from the fix.

The generation counter was the wrong mechanism for the same reason: it changes only on *leaving*
the data, so it cannot see a move between two cells. Once F4 was fixed by comparing the reply's
position with the inspected cell, **both of the generation mutations survived** — the mechanism had
become redundant, and dead defensive code is a permanent mutation survivor. It is removed.

> A fix tells you what to assert about the bug. It does not tell you what to assert about the
> states either side of it, and a precondition written to set up the bug can be the next bug.

### Forty-second: a schema change is not finished until the copies already in the field can move

I added columns to the audit sheets twice in one day. `score_walked_audit.py` refused a sheet
without them and told the owner to **regenerate** — and the generator writes every owner column
blank, so the only route past its overwrite guard destroys exactly the observations the whole
exercise exists to collect. There was no migration at all, and the instruction was worse than
nothing.

> A required column is a breaking change to every copy of the file that already exists. The
> migration is part of the change, not a follow-up.

### And two recurrences

**A fixture set that holds a dimension constant cannot see a defect along it**, which is the
oldest lesson in this document. Every multi-layer group gave its layers the **same threshold and
the same horizon**, so two of F1's mutations — reading the first enabled threshold for every
criterion, and reporting the first layer's horizon for every criterion — were invisible to all 79
conformance checks and all 27 card checks. The groups were built before `explainAt` existed to read
those arrays, and nothing re-asked whether they still discriminated. There is now a three-layer
group with three thresholds and three horizons, and it is what catches both.

**And the shell heredoc, for the fifth time in one session.** The rule was narrowed to "a heredoc
is fine for a script with no backslashes" and I broke it five times anyway, because a patch script
almost always grows a `\n` or a regex. The rule is now absolute: see
[[reference-codex-runtime-quirks]].

Forty-two instances at that point.

## Pass 53, 2026-11-14 — instance 40 again, in the repair written for instance 40

Pass 53 reviewed pass 52's repairs. **Eleven findings, two High, and five of six claims failed.**
The fifth consecutive pass to find more in the previous pass's repairs than in the work repaired.

**The prompt's first claim was "this time I enumerated the class rather than the instances", and
it failed twice in one pass.** That is instance 40 recurring immediately, in the work done
*because* of instance 40. Three separate mechanisms, and each is worth naming because they are
different:

* **My enumeration was wrong.** I listed the `explainAt` reply's fields and compared every one —
  and omitted three: `outside`, `invalidCoordinates`, `notComputed`. Adding `outside: true` to a
  successful reply passed all 87 worker checks. Writing an enumeration from memory of the code is
  not enumerating the artifact; Codex produced its own list and diffed it against mine.
* **The assertion compared against a constant.** Every exhaustive case computes with `seq: 1`, so
  `seq: state.lastSeq` could be replaced by the literal `1` undetected. A constant in a harness
  cannot detect a constant in the thing it tests — which I had already written in this file one
  pass earlier, about `reqId`, and then did not generalise to its neighbour.
* **The fixture I added to catch a finding could not catch the adjacent form of that finding.** I
  added a three-layer group with three thresholds and three horizons, because no group varied
  those. It has **no destination planes and no flag planes**, so a destination-index substitution
  survives it — the same index walk, the same defect class, one array along.

> Fixing a finding creates a new artifact, and the new artifact has its own blind spots. The
> fixture built to discriminate one dimension is silent on every dimension it does not carry.

### Forty-third: a read-back check whose snapshot is taken after the loss cannot see it

`migrate_audit_sheet.py` reads the written file back and compares every pre-existing value, and
prints "every pre-existing value was read back and compared; none changed". With a **duplicate
header** — two `notes` columns, which is exactly what an owner adding a column of their own
produces — `csv.DictReader` keeps only the last value. The snapshot is built from that same
already-lossy read, so the comparison succeeds and the script asserts in words that nothing was
lost while a value is gone.

> A verification that reads its expectation through the same lossy path as the thing it verifies
> confirms the path, not the data. The snapshot has to come from a representation that cannot have
> dropped anything — here, positional rows rather than a dict.

### Forty-fourth: checking that expected content is present does not check that foreign content is absent

The card's new per-criterion assertions check each block for its own outcome, limit, bound, cause,
disclosure and complete place set. A mutation that **copied other criteria's destination text into
unnamed blocks** passed all 29 checks, because every assertion was satisfied — the expected content
was all there, with more beside it. So was a mutation replacing the combined headline with the
affirmative one, since no assertion mentioned the headline at all.

> For any surface that composes parts, "each part contains what it should" is half a check. The
> other half is "and nothing it should not".

Forty-four instances at that point.

### Forty-fifth, from integrating pass 53: a runner that cannot tell a crash from a catch

Writing a mutation runner for `migrate_audit_sheet.py` reproduced, immediately, the defect pass 44
found in this project's first JavaScript runner. It reported **caught** for a mutant that did not
parse: the replacement's regex backreference was mangled, Python could not import the module,
pytest exited non-zero, and "non-zero" was the whole test for a catch. `mutate_worker.mjs` has
required a `FAIL` line in the output since pass 44 for exactly this reason, and I wrote the new
runner without it.

It also produced a **false** MISPLACED on its first run in the Python case — the landing-site
detector tracked `def` and not `class`, so a mutation of a class attribute was attributed to the
preceding module-level function and a correctly placed mutation was accused.

> A guard written fresh does not inherit the lessons of the guard beside it. Both of these were
> already recorded in this document, about the file one directory away.

And one mutation is withdrawn rather than kept: keying the migration's snapshot positionally is a
real strengthening whose failure needs **two** faults — a duplicated label *and* a corruption of
the earlier row — so no one-fault mutation can be caught for the right reason. Recorded as
unguarded, like `state.lastInCount` and the pointer generation before it.

Forty-five instances now.

## Pass 54's aftermath, 2026-11-15 — one instance supplied, six more of the same claim

### Forty-sixth: a probe aimed at the obvious place cannot see a sub-cell error

Queue item 3 was written as "compare the cell the page resolves at known coordinates against
`GridSpec.cell_for_lonlat`, at the footprint corners and far from the origin". Computing the
displacement first showed that at **every one of the 514 row centres the two placement rules name
the same row**: the disagreement is a sub-row offset, at most 0.37 of a row, which can only tip a
floor near a row *boundary*. A probe at a cell centre — the natural place to put one, and the place
corners and cell indices lead you to — would have reported agreement 514 times out of 514 and been
quoted as confirmation.

> Place the probe where the error can show, not where the coordinate is easy to name. A measurement
> whose resolution is coarser than the error it looks for returns agreement, and agreement from an
> inert probe is indistinguishable from the real thing in a report.

The same reasoning made the probe's own blind spot visible: it recovers the drawn row from where
the quad's corners project, so any **affine** placement error — a constant offset, a uniform
stretch — cancels and it reports agreement. That is now a passing check that says so, rather than
a gap discovered after the number was used.

### Forty-seventh: instance 40 again, and this time a reviewer had handed me one of the instances

Codex pass 54 found that the progress note's first table said "the per-criterion card is unbuilt" a
day after the card was built. I fixed that table and committed, with a commit message about what
contradictory live documents cost. **There were six more copies of the same claim in live
documents** — two in the decision report's release prerequisites, where it says a release is
blocked on building something that already exists, and four in the execution plan. One grep for
"is unbuilt" found them all, and I ran it a day later, while writing something else.

> A stale claim is a class, not a line. When a reviewer points at one instance of a sentence that
> is no longer true, the next action is to search for the sentence — not to edit the line.

This is at least the third recurrence of instance 40 since it was written -- twice inside pass
53’s own repairs, by that section’s own account, and now with the instance handed to me by a
reviewer. It is the first where somebody else found the instance and I still closed only that.

### Forty-eighth: the self-test proved the instrument could fail, and the browser broke it twice

`probe_placement_selftest.mjs` was built to show the browser probe could fail: four stub pages, a
Mercator one it must agree with, two displaced ones it must catch, and one it is asserted to be
blind to. Twelve checks, all passing, and the reasoning behind them was right. Then the probe ran
in Chrome for the first time and reported **fourteen disagreements, none of them about the page**.

Both were behaviours the stub had quietly replaced with something kinder:

* the stub's `maskPixel` returned the bytes the worker wrote. A real canvas stores a translucent
  pixel premultiplied by alpha in eight bits, so `getImageData` cannot give the byte back: the
  page's blue (24,119,242,150) reads as (24,119,241,150). Every exact RGBA comparison failed.
* the stub's `MouseEvent` kept the fractional coordinates it was handed. A real `MouseEvent`
  truncates them, because clientX is an IDL `long` -- 464.378 arrives as 464. One screen pixel was
  two thirds of a cell at that view, so the hover read a card for the *next cell* and compared it
  against the probe's. Every probe worth having sits on a cell boundary, which is exactly where a
  lost pixel changes the answer.

> A stub must be at least as hostile as the thing it stands in for. A test double written from
> what the real thing *means* will model the semantics and smooth away the mechanics -- integer
> truncation, 8-bit quantisation, premultiplied alpha -- and those are what break at a boundary.
> When a double's behaviour is kinder than the original's, the test measures the double.

Both are now reproduced in the stub -- the quantisation exactly, with a check that a three-count
shift is still caught so the new tolerance has not turned the comparison off -- and the repaired
probe ran again and agreed with the oracle at all eleven probes. Instance 46 was about where to
put a probe; this one is about what the probe is rehearsed against. The rehearsal was the thing
that was wrong, and nothing in it could have shown that.

### Forty-ninth: a tradeoff can stay right while its justification expires

`grid.encode_minutes` rounds **up**. The argument was measured and it still holds: `ceil(s/60) <=
T` is `s <= 60T`, which is the float comparison, so the published region is exactly what the
pipeline asserts. `rint` was not a shift but a loss -- 590 s and 610 s encode to the same byte, so
8.15% of the cells it showed as passing 10 minutes did not pass. Nothing about that has changed.

What changed is the **price**. The docstring priced the cost of `ceil` like this:

> The cost is that the minute is now an **upper bound** on our model's time rather than the
> nearest value to it, overstating by less than 60 s. Nothing displays it -- there is no per-cell
> readout anywhere in the render path [...] The day a per-cell number is shown, 30-second units
> are the better answer.

It even named the trigger. On 2026-11-14 the per-criterion card started printing the minute, and
the trigger fired with nothing attached to it. A household can now read "12 min" for a model time
of 11 minutes 1 second. Five adversarial passes read that card's code in the two days that
followed and none of them connected it back, because the encoder still looked right -- and it is
right. Only its cost had moved, and a cost is not where anyone looks for a defect.

> A decision can be correct and its justification stale at the same time. When a tradeoff is
> priced against a fact about somewhere else in the system -- nothing displays this, nobody reads
> that, this never crosses a boundary -- that fact is a dependency, and nothing recompiles when
> it changes. Write the trigger into the place that would fire it, not only into the place that
> would pay.

Closed in both directions: the docstring no longer claims nothing displays the minute, the card
now says "rounded **up** to the whole minute" rather than leaving the direction to be guessed,
and `tests/test_browser_conformance.py` reads that sentence out of the running `card.js` and the
rounding rule out of the running `encode_minutes`.

**That last claim was overstated and pass 55 proved it the next day.** The sentence here said the
cross-check meant "the two cannot drift apart again in silence". The same sentence it checks then
shipped a *different* false statement -- "measured from the centre of this cell", naming the
published cell's centre when the time was computed at a UTM centre a median 39.9 m away -- and
the cross-check passed it, because the check confirmed that the producer evaluates *source* cell
centres, which is true, and says nothing about the consumer's displayed cell. A check that
confirms a true proposition adjacent to the claim is not a check on the claim. See instance 51. The 30-second-unit question the docstring named is now an owner-owed decision in the
progress note rather than a sentence waiting in a comment.

### Fiftieth: an index is not a location until it names its grid

The audit sheet has columns called `row` and `col`. They index the UTM `GridSpec` the pipeline
computes on. The published raster is a **different grid** -- WGS84 lon/lat, 514 x 643, its own
origin and its own indexing -- and it also has a cell (286, 129), about 400 m from the UTM one.

`measure_drawn_pixel.py` wrote a probe called `the_walked_cell` at
`west + (129 + 0.5) * col_w, north - (286 + 0.5) * row_h`: the sheet's numbers, read as indices
into the published raster. The sheet's own `query_lon` and `query_lat` were in the same row and
were not used. The two cells disagree about every single thing a walker would check:

| | the cell the query coordinate is in | the index read as published |
|---|---|---|
| minutes | 14 | 24 |
| at the 15-minute band | PASS | FAIL |
| restricted route | flagged | not flagged |
| destination | Hill's Family Asian Markets | Seal The Seasons |

And the probe's own text called its card "the one a person can check against a walk".

**I wrote "nothing internal could have found it", and that was wrong** -- Codex pass 55. The
sheet coordinate, the source grid and the published grid were all in this repository; an internal
consistency check between a sheet row's index and its own coordinate would have found it without
any browser. What the browser session did was *prompt* the comparison. That is worth something and
it is not the same claim. The paragraph as written is kept below so the overstatement is visible,
with its last sentence corrected.

The probe was self-consistent. Its expectations were
re-derived from the published bytes by a second code path that does not share the generator's
helpers -- the control this project added precisely so an oracle cannot agree with itself. A
browser then ran against it and agreed at all eleven probes with zero disagreements. Every check
passed, because every check was about whether the probe was consistent, and none could ask
whether it was *where it said it was*.

> An index into a grid is not a place. It is a place only together with the grid that produced
> it, and two grids over the same ground will both answer to the same pair of numbers with
> different land. Carry the coordinate; where an index has to travel, make it carry the name of
> its grid. And note what this costs to detect: a reference that is merely consistent is not
> thereby correct, so something has to compare it against a fact it did not generate. That
> comparison does not have to come from outside the system -- the coordinate and both grids were
> already in the repository. It has to come from outside the *assumption*.

It was found by reading the page at that cell before the owner re-walked it -- a step taken
because a reviewer said the sheet's own number should not be assumed to authenticate what a
household is shown at a real door. The probe now derives from the journey's query coordinate, the
walk instruction in three documents gives that coordinate instead of the index, and the sheet's
README says which grid its columns are in.

**And the repair carried its own version of the same error.** Six places then called that
coordinate "the recorded door". It is `query_lon`/`query_lat`, the centre of the UTM cell the
journey was computed for; the row's `start_lon` and `start_lat` are blank and filling them is the
whole point of the re-walk. Having just learned that an index is not a location, I promoted a
query point into a door in the same commit.

### Fifty-first: a check on a true neighbouring fact is not a check on the claim

Fixing an overclaim, I wrote a new disclosure: *"Times are estimates: measured from the centre of
this cell, and rounded up to the whole minute."* Then, knowing that a card suite comparing the
card against its own string is a tautology, I wrote the cross-check I thought closed it -- a test
that reads the sentence out of the running `card.js` and the rounding rule out of the running
`encode_minutes`, plus:

```python
src = inspect.getsource(build_layer_surface)
assert "cell_centers_xy()" in src
```

That assertion is **true**. The producer does evaluate cell centres. It is also about the **UTM**
grid, and the sentence is about the cell the **card** names, which is a cell of the reprojected
WGS84 raster. A published cell carries a time measured at some UTM cell's centre -- a median
**39.9 m** from its own centre, up to **70.6 m**, the same order as the 36 m placement error this
page was built to measure. The disclosure written to stop the product overclaiming was itself
false, in a sentence that answers "where does this journey begin?", and the test I wrote to
prevent exactly that waved it through.

> A check that confirms a true fact *next to* the claim is not a check on the claim, and it is
> more dangerous than no check, because it is reported as coverage. When a sentence names a
> thing -- this cell, this address, this route -- the check has to pin the **referent**, not the
> mechanism that produced the value. Ask what the sentence would have to mean to be false, and
> test that.

The repair measures the gap instead of asserting the premise, and fails if the two grids ever
align -- which is the one condition under which the retired wording would become sayable again.

### Fifty-second: I repaired "an index is not a location" by inventing a location

Instance 50 was found on 2026-11-16: the audit sheet's `(286, 129)` is a UTM index and had been
read as a published one. In the same commit that recorded that lesson, I described the sheet's
`query_lon`/`query_lat` as **"the door recorded for `band15min_pass-03`"** -- in the oracle
generator, the probe's own text, a new experiment record, a new test, the progress note, the
audit README and the decision report, and then in the instruction telling the owner where to
walk from.

It is not a door. It is the journey's query point, the centre of the UTM cell the time was
computed for. That row's `start_lon` and `start_lat` are **blank**, and filling them is the
entire purpose of the re-walk. Codex pass 55 found it by opening the CSV.

> The repair for a precision failure is where the next precision failure goes. Having just
> learned that an index is not a location, I promoted a query point into a door -- a *more*
> specific claim than the data carried, made while writing the lesson about claims more specific
> than the data carries. Check the words of the fix against the same source you checked the bug
> against, in the same sitting.

### Fifty-third: "every" meant "the one I have"

`project-phase1-s0-complete.md` carried this, in bold, as a result:

> **NO_PATH is unreachable in every shipped configuration.** `symmetrise` runs before
> `largest_component`, so the retained walk graph is 1 strongly connected component...

The reason is sound and it is about **walk**. `symmetrise` runs for walk only; a drive or bike
graph stays directed, and a node in a directed dead end reaches nothing. The claim was quantified
over *every shipped configuration* while every configuration that had ever shipped was a walk
layer, so the quantifier cost nothing to write and bought a result it had not earned. On
2026-11-16 four non-walk layers were published and the status appeared in all four: **57 cells per
drive layer, 95 in the bike layer.**

> A universal claim is cheap exactly when the set has one member. Before writing "every", ask
> what else is *in* the set — and when the set is "everything we have shipped so far", say that
> instead, because it is the true statement and it stays true. The justification here was
> mode-specific and the sentence above it was not, and nothing in between flagged the gap.

Unlike instances 51 and 52 this one was not found by a reviewer or by an owner. It fell out of
**doing the thing the claim quantified over** — shipping a configuration that had never shipped.
Which is the same lesson as the walked journey, one level up: the cheapest test of a claim about
every case is to produce a case.

### Fifty-fourth: every overstatement was a true number attached to the wrong population

The owner read the seven-criterion page, reported two anomalies, and then said they were sceptical
of my answers and asked for a critical review. Two reviewers ran independently — Codex
`gpt-6.1-sol` and Antigravity/Gemini `gemini-4-hydrogen-xhigh` — against twenty numbered claims.
**Eleven confirmed, seven overstated, two wrong.** The findings survived; a lot of the precision
did not.

What makes it worth an entry is that the seven overstatements are **the same mistake seven times**,
and it is not sloppiness about the numbers. Every number was correct. Each was attached to a
population it did not describe:

| I said | true of | not true of |
|---|---|---|
| "56,034 then flat" | the count at 20 minutes | the plateau, which is 56,036 from 21 |
| "17.4% of cells, 0.71% of buildings" | the UTM source grid | the published grid the browser paints: 16.95% and 0.67% |
| "125 holes" | the UTM grid | the screen, where it is 121 |
| "every hole has status OK" | the walk layers | `grocery/drive`, which has 14 `NO_PATH` holes — printed by my own script |
| "the whole gap is in `atnode`" | its being the dominant term | hole one, where the on-edge leg is 32% of the gap |
| "removes 23% of the holes" | the 20-minute threshold | 10 and 15 minutes, where it is nearly 39% |
| "33 m away" | the **east neighbour's** access leg | the hole, which is 105.94 m from that road |
| "41 Apache records already shipped" | the accepted input | the shipped side table, which holds 35 |

> A number does not carry its population with it. Every one of these was lifted from a table that
> knew which grid, which threshold, which layer, which row and which pipeline stage it described,
> and written into a sentence that did not say. The fix is not to be more careful; it is to make
> the sentence name the population — **"121 on the published grid", "23% at 20 minutes", "35 in
> the shipped table"** — because a claim that names its population can be checked and one that
> does not cannot.

This is instance **50** again — *an index is not a location until it names its grid* — generalised
from indices to every measured quantity, and instance **52** again in the 33 m case, where I read a
value off a neighbouring row of my own table. Third time for that one.

**One claim was not an overstatement but a straightforward error, and the owner was closer to right
than I was.** I wrote that adding nodes along an edge "would change nothing", because subdividing
does not change shortest-path distances. `speeds.py:133` charges the restricted-access penalty
**per edge**, so splitting a restricted edge doubles it. Codex built the counterexample, Gemini ran
it on the real graph — 74,930 cells move — and I reproduced it through the production
`add_travel_times`. The lesson is narrower than the others and worth having: **an invariance
borrowed from a textbook problem has to be checked against the pipeline's own cost function**,
which here is not the textbook's.

Fifty-four instances now.

### Fifty-fifth: the experiment could not have produced the result that would have falsified it

Pass 57, 2026-11-16. Pass 56's eight overstatements were true numbers pointed at the wrong
population. This one is worse, because the number was not even wrong — it was **empty**.

I told the owner that multi-candidate snapping "makes 77% of cells faster and **no cell slower**",
and offered the second half as the reassuring part: a change that only improves things. Codex
looked at how the candidate experiment selects, and the experiment **takes the minimum reported
time across the candidate set, today's answer included**. A minimum over a set containing the
current value cannot exceed the current value. **No cell could have come out slower.** The claim is
a tautology wearing a measurement's clothes, and I reported it as evidence.

Re-selected on **cost** — which is what `speeds.py` actually does, because selection is by cost and
reporting is by time — **3,202 UTM OK cells are slower**. The real experiment answers the question;
mine could only ever agree with me.

> **The check is not "is this number right" but "could this instrument have returned the
> answer I did not want".** If the construction forbids the falsifying outcome, the result is not
> evidence, however carefully it was computed. An experiment that cannot fail has not been run.

This is distinct from instances 50, 52 and 54, which are all *the number describes something other
than what the sentence says*. Here the sentence and the number agree and the **design** is empty.
The nearest relative is instance 51 — *a check on a true neighbouring fact is not a check on the
claim* — one level up: there I verified the wrong proposition, here I built an instrument that
could only verify.

**Two repeats came with it**, both in what I said to the owner rather than in a note, which is its
own lesson about where claims escape review. I gave the OFF_NETWORK area as **560 km²** by
multiplying 56,036 published cells by 100 m squares; published cells are WGS84 lon/lat averaging
**9,544 m²**, so the geodesic figure is **535.0 km²** — instance **50** again, *the published grid
is not the UTM grid*, now for the third time. And I quoted park/walk at a **20-minute** limit when
the layer ships a **15-minute** default and is not even enabled on open — instance **54** again.
The hatch figures happen to be nearly identical at both thresholds, which is exactly why nobody
noticed; a coincidence is not a check either.

Fifty-five instances now.

### Fifty-sixth: the overstatement was in the review prompt, handed to the reviewer as a premise

2026-11-17, the V1 places module. The Codex prompt stated the module's guarantee as

> a provider failure can no longer be cached as a negative result

and asked the reviewer to find a way around it. **That is not a universal guarantee.**
`ResultCache.store` is public and accepts `None`, so a caller that catches its own
`ProviderUnavailable` and returns nothing can still write a negative entry. What the module
guarantees is narrower: a failure that is **propagated** is never cached.

Codex found **no path** where a correctly propagated failure becomes a negative entry -- the code
was right -- and refuted the claim anyway. The defect was in the sentence, and the sentence was in
the one document whose whole job was to be attacked.

> An overstated claim in a review prompt is worse than the same claim in a note, because the
> prompt sets the reviewer's search space. "X is guaranteed, find a hole in X" sends a reviewer
> looking for holes in X. "X holds for propagated failures, and `store` is public" sends them to
> the public method. Overstating it removes the ground the real weakness stands on.

Same family as instances 50 and 54 -- *a claim that does not name its population* -- with the
population being **which paths**. The new part is where it happened: the document most likely to
carry an overstatement is the one I write to invite correction, because that is where I am
describing what I have just built and want to be true. The narrower claim is what the docstring
says now.

Fifty-six instances now.
## Instance 57, 2026-11-18: one case was promoted to a mechanism, and the mechanism was measured away

`KBI Biopharma` -- a contract biologics manufacturer that FSQ labels `Retail > Pharmacy` at 0.0 m
with name agreement 1.00, and that our own Overture-derived candidate list also carries as a
pharmacy candidate -- is a real false positive. From that single case I wrote a mechanism:
Foursquare feeds Overture, our places are Overture-derived, therefore **"shared lineage is not
independent confirmation"**, and committed it in `785e76a`.

Then I gave it two falsifiable tests and it failed both. Coordinate coincidence came back at 7.0%
and 4.9%, not the high share a shared upstream record would produce. The branded/brandless
agreement gap came back +6.7 for grocery and **-2.7 for pharmacy**, not the consistent positive the
reading predicts.

> **One case tells you the failure exists. It does not tell you what produces it.** The jump from
> "here is a false positive, and here is a plausible mechanism" to "the mechanism is operating" is
> the whole error, and it is invisible because the mechanism is *true in the abstract* -- Foursquare
> really does feed Overture. What was never checked is whether it operates at a scale that matters
> here.

Same family as instances 50, 54 and 56; the population this time is **which records**, and the
sample was one. What rescued it was that the claim had been written down sharply enough to be
testable at all: "shared lineage is not independent confirmation" names a measurable consequence,
so the next run could refute it. A vaguer sentence -- "FSQ may not be fully independent" -- would
have survived indefinitely.

The lesson is not "do not hypothesise". It is **predict a number before believing a mechanism**,
and say in the note which number would refute it.

## A fifty-eighth, 2026-11-18: the code was careful and the prose was not

The name-agreement floor exists because `name_agreement` returns 0.0 for two different facts, and
I built a three-valued `match_verdict` so the two could never be confused. Eighteen tests. Then I
wrote the note that explains it, and in the note I said **"42 of 338 of OSM's proposals rest on a
match with name agreement 0.00, a different business"** -- conflating exactly the two facts the
code had just been built to separate.

An adversarial review found it, along with three more overclaims in the same note and two real
defects in the code the tests had not caught:

* **`A&C Supermarket` against an OSM feature of the SAME NAME 12.0 m away scored `unverified`**
  and had its correct proposal withheld, because `a` and `c` fall to the length rule and
  `supermarket` is a stop-word, so both token sets emptied. The code read "nothing to compare"
  where there was plenty to compare -- `unverified` was dressing a bug as a category.
* **The "weak" caveat was concatenated onto an EMPTY proposal**, so twelve pharmacy rows held
  warning text in a proposal cell, and my measurement counted all twelve as proposals: 28.4%
  where the truth is 18.9%.
* **"63% of the proposals were not evidence"** stated a *withholding rate* as a *wrong-match
  rate*, which it is not, in both directions.
* **"a Jaccard threshold is the wrong knob"** was partly refuted by arithmetic I had not done: an
  inclusive floor at 0.25 keeps all twelve correct matches in the band *and* rejects the false
  pair at 0.20.

> **Tests check what you thought of. Prose is where the thing you did not think of gets asserted
> anyway** -- and it is read more often than the code. The defects and the overclaims are the same
> failure wearing two coats: in both, a distinction I had established was quietly dropped at the
> point of use.

The cheap countermeasure already existed and worked: the review prompt was committed before launch
and its item 6 asked the reviewer, in those words, to attack the note's "63%" phrasing. The prompt
found its own author out. **Write the attack on your own strongest claim into the prompt, before
you see what comes back.**

## A fifty-ninth, 2026-11-18: the page already contained the rule that worked

The published review copy did not paint its overlay, and the MapLibre attribution control had
vanished. Diagnosis, correct: the map container had no definite height when the map was
constructed, and a `canvas` source needs a laid-out container.

The fix I wrote the first time rewrote the ancestors' heights in `svh` units, added `min-height`
to three selectors, and made things worse -- the mask stayed broken and the attribution control
disappeared. **`styles.css` already gave `#map` a definite height** (`height: 52vh;
min-height: 260px`) which needs no ancestor height and works untouched. Only one narrower rule, in
a `@media (min-width: 880px)` block, overrode it. The entire fix was to put the base rule back
above 880px.

Then I got it wrong a second time in the same five minutes, by overriding `flex` as well as the
height, which let `#map`'s `width: 100%` take the whole row and pushed the criteria panel
off-screen.

> **When something is broken by an override, the fix is to remove the override's effect, not to
> invent a replacement for the thing underneath it.** Inventing a replacement means two rules now
> compete where one worked, and the new one has had no testing at all.

Related to instance 47 in shape -- both are about what is already written down being more reliable
than what I am about to write -- but the population here is CSS rather than notes. Fifty-nine
instances now.
## A sixtieth, 2026-11-18: I verified the mechanism and asserted the consequence

The name recovery put 13 records into `NAME_CONFIRMED_SUPERMARKETS`, and I measured it there: 13
rows, 272 -> 259, 33 tests, every entry carrying its own evidence string. Then I wrote that it
"writes 13 records into a published grocery layer" and that the published artifact was therefore
ODbL share-alike.

The third adversarial review measured the other end. **`supermarket` 235 -> 242. `grocery`
543 -> 543.** The published manifest has no `supermarket` layer, and `categories.py` carries a
comment, written before any of this work, saying exactly why: *"`grocery` below is left exactly as
it was, because the published layer is built from it."* Nothing published depends on a footprint,
which is what `d39141e` had itself said -- *"authorised, not yet exercised"* -- one commit before
`d224945` claimed the opposite.

Every number I checked was right. The numbers I did not check were in the sentence that mattered.

> **Measure the end of the pipeline, not the end of your change.** A change ends where you stopped
> typing. A consequence is a claim about a system, and the system is longer than the diff.

The same review found the same shape in the geometry: `corroboration` was taking the largest
building within 120 m, so **8 of the 13** rested on a building their point was not inside --
Discount Tire 105 m from a `Lowes Foods`, New Hope Baptist Church 115 m from an `ALDI`, Europa
Center 67 m and 81 m from two `Wal Mart` records. I had even written, about one of them, *"possibly
a point on a neighbouring structure"*, and filed it as a curiosity rather than following it. And
the claim that protected all 13 -- *"every one checked by name before it went in"* -- was TRUE and
IRRELEVANT: reading a name cannot tell you which building a point sits in, and that was the only
thing the acceptance rested on.

Two things that worked, and both were cheap:

* **The prompt found its own author out again**, as in instance 58. Item 1 said *"find one that
  should not be there -- look for one I have not flagged"* and item 7 said *"the previous review
  caught me conflating two populations in exactly this way."* Both invitations were taken and both
  landed. Writing the attack on your own strongest claim is now two for two.
* **Reproducing before believing.** The reviewer's numbers came back identical in four independent
  places -- 20 vs 33 candidates, 235 -> 248, 543 -> 543, and four buildings it named -- which is
  why its external citations (a state WARN filing, an NCDA plant number) were credited rather than
  taken on trust. One of its claims I could NOT confirm on the street number, and that one is
  recorded as a doubt attached to the record instead of acted on.

Sixty instances now.
