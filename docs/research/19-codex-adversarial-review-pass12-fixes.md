# Codex adversarial review, pass 12 — the pass-11 fixes, and the claims I corrected because of them

**Date:** 2026-11-04. **Model:** gpt-6.1-sol. **Head at review:** `6d1702c`. **Prompt:**
`codex-pass12-prompt.md` (scratchpad). Two halves: whether I implemented pass 11's fixes correctly,
and whether the claims I rewrote because of them are now true.

**Nine defects: 4 High, 4 Medium, 1 Low. All confirmed and reproduced by Codex with concrete
inputs, and all now fixed.** The paired destination measurement survived, and was verified more strictly than I had
verified it myself.

## What Codex verified rather than found

Worth recording separately, because a review that only lists failures gives a false picture of what
was checked.

- **The M3 paired transition matrix reproduces exactly**: 253,678 / 1 / 3,074 / 16,208 / 57,541.
- **The reconstruction holds, for a better reason than mine.** I argued it from the count matching
  at 452. Codex checked the stored raw **bbox predicates** and found they select exactly the same
  452 ids — and pointed out that "all 550 geometries are points" was *not* sufficient proof on its
  own, because their stored bboxes have non-zero width.
- **The lost cell is the mechanism I claimed.** Snap distance unchanged at 125.7155 m; selected
  network cost **falls** 7,147.8639 → 7,127.0519 while network time **rises** 7,027.8639 →
  7,127.0519. Cheaper-but-slower displacement, not a snapping or tie artefact.
- `OFF_NETWORK` is necessarily unchanged "for these two non-empty destination sets on the same
  geometric index and access cap" — the qualification matters and I had not stated it.
- Current index 107,484 / 113,720 / 229; buildings 522,160 with source and licence counts exactly
  matching the registry; 22.3145% nodata; the penalty sweep; the H2 bracket (24,745 / 40.0 / 129.7 /
  668.6) and its threshold counts (205 / 329 / 363 / 265) all reproduce.
- H3's membership bookkeeping works as claimed.
- No further supersession-scope defect in the notices. Codex notes that overwritten historical
  artifacts limit independent verification of the older totals, which is a real and permanent
  consequence of having overwritten them.

## The one claim it broke

**"Nothing crosses a 10/15/25/45-minute threshold in the losing direction"** was true and I let it
imply more than it supports. Codex searched thresholds I had not tested and found cell
**(126, 612)** going 2,752.6122 → 2,847.0805 s, which fails at **47 minutes**. Four clean
thresholds are four data points, not a property.

## The nine defects

### H1 — a live acquisition can lose its lock (`acquire.py`)

`LOCK_STALE_S` was 3600 s and `LOCK_TIMEOUT_S` 1800 s, so a waiter breaks a lock still held by a
live 45-minute download *before its own timeout expires*; the original holder's `finally` then
unlinks the **replacement** lock and admits a third process. Two stale waiters can likewise unlink
each other's locks. Codex reproduced all three ownership failures by ageing a held lock. A PID in
the file does not help: PIDs are reused and are meaningless across machines.

> "The consumer-race disclaimer is accurate, but the claimed serialization still exceeds the
> implementation."

**Fixed** by making the lock **OS-owned** for the holder's lifetime — `msvcrt.locking` on Windows,
`fcntl.flock` elsewhere, on a handle held open for the duration. The kernel releases it on process
death however that happens, so there is no staleness threshold to tune and nothing to reclaim. The
lock file is now **never unlinked**, because unlinking is what let one process release another's
lock. Two new tests, both cross-process, because an OS lock is held per process: a competitor that
must time out, and a child that dies holding the lock without cleanup.

### H2 — corroboration erases the new reading priority (`resolve.py`)

Reconstructing the merged `Candidate` defaults `reading` to zero, promoting a stripped
interpretation to the status of an intact-query match. Input: `Durham Coffee`, with an OSM **Durham
Coffee** in Raleigh and a **Coffee** in Durham — ambiguous, correctly. Add an Overture copy of
Coffee within 60 m and it becomes a confident **Coffee**.

**Fixed.** The merged candidate now carries the `reading` of the member that supplied the
*evidence* — `max((kept, cand), key=lambda c: (c.score, -c.reading))` — rather than letting it
default. Locality was already ORed across members. Verified against Codex's input: without the
Overture copy the outcome is `ambiguous` with `Durham Coffee` (reading 0) leading `Coffee`
(reading 1); with the copy, `Coffee` is correctly marked `corroborated_by=('overture',)` and the
outcome is still `ambiguous` with `Durham Coffee` leading. Corroboration now changes what we know
about a place without changing which reading of the query matched it.

### H3 — boundary stripping still destroys names (`resolve.py`)

`_split_locality` stripped the boundary connective *inside itself*, so the ladder never contained
the rung "locality removed, connective intact". `Durham The Coffee` therefore produced only
`Coffee`, which matched a different shop at **1.000** while **The Coffee** scored 0.725.

**Fixed.** `_split_locality` now returns the raw remainder and the trimmed form is a further, more
destructive rung. Verified against Codex's input: before, `Coffee` 1.0 leads and `The Coffee` is
0.725; after, both score 1.0 and `The Coffee` wins on the reading tiebreak.

### H4 — role normalisation permits new false corroborations (`resolve.py`)

**My third attempt at this rule, and the second over-correction.** Equal *categories* broke real
de-duplication. The subsidiary-vs-parent boolean that replaced it is too coarse the other way:
`parking` and `fuel` are deliberately *not* subsidiary, because a car park is a destination in its
own right, so both answered "not subsidiary" and merged. Codex reproduced two pairs:

- OSM **RDU** `parking` + Overture **RDU** `airport` → one confidently resolved car park,
  "corroborated" by the airport.
- OSM **Acme** `pharmacy_counter` + Overture **Acme** `pharmacy` → one confidently resolved counter.

`pharmacy_counter` had been separated by the old raw-category set and fell through to `facility`
when roles replaced it.

**Fixed** by requiring **equal roles** to merge, and restoring `pharmacy_counter` (plus
`service_desk`, `information`, `ticket_office`, `kiosk`) as fixtures. Roles are coarse enough to
span two taxonomies — OSM `supermarket` and Overture `grocery_store` are both `facility` and still
merge — and fine enough that a car park is not an airport. Codex suggested a compatibility matrix;
equality is better, because there is no pair of *different* roles that should collapse and a matrix
would only be somewhere to hide one.

### M5 — explicit stop queries are unnecessarily rejected (`resolve.py`)

`Franklin Street bus stop` matches a bus stop exactly at 1.000 with a cafe at 0.830, and returns
ambiguous. **Another over-correction**, this time of pass-11 H4.

**Fixed** with a narrow literal test on words the user typed (`STOP_INTENT_WORDS`): the
mixed-reference abstention is suppressed when the query itself names a stop. The `Duke Hospital`
guard is unaffected and still abstains.

### M6 — four corners do not generally bound the grid (`grid.py`)

A UTM rectangle's top edge is a curve in latitude whose maximum is in the *interior* of the edge,
near the central meridian. Codex's counterexample
`GridSpec("EPSG:32617", 450000, 4000000, 100, 1000, 10)` puts **806 cell centres north of the
corner-derived bound**.

> "The Triangle's four-corner result matched my dense boundary check; this is a defect in the
> general method, not evidence that its 522,160-building count is wrong."

**Fixed** by sampling 256 points along each side and padding outward by 1e-6°. Verified: the
counterexample now has 0 centres outside, with the bound at 36.144719 against a maximum centre
latitude of 36.1442673112 — Codex's figure exactly. The Triangle envelope moves only by the
padding, so the acquired buildings did not need re-downloading.

### M7 — ordering changes results even with unequal costs (`snap.py`)

`cost_end < cost_start` won outright while the time preference applied only inside an `np.isclose`
band, so the rule was **asymmetric** and reversing an edge's stored geometry changed the answer.
Codex's input: a two-way 10 m segment, both endpoints destinations, forward 180/1000 and reverse
20/1000.004, evaluated at its midpoint — **90 s versus 10 s** depending on insertion order.

**Fixed** with a symmetric comparison: exact cost equality, ties broken by the lower time. The
relative tolerance was wrong on its own terms as well — at a 7,000 s cost it treated a 70 ms cost
difference as a tie, while the contract says choose on cost. Codex also notes the pass-11 M2
enumeration omitted **nearest-edge STRtree ties** and **equal-size component selection**; both are
added to S4.1.

### M8 — "the access fix is worth 1.7%" is unsupported (plan, `verify_two_weight.py`)

Codex reproduced 4,420 / 256,752 and 4,178 private, but they are outputs of a **length-keyed
approximation**: a public and a restricted edge with equal rounded lengths are both classified
restricted, and a restricted edge whose projected length differs from its stored OSM length is
missed. More importantly they count edges that are *nearby*, not cells the intervention recovered.

> "Measuring recovery requires paired before/after surfaces."

**Addressed by S2.3**, which was written for this and is reported below; the old figure is now
labelled an approximate proximity statistic.

### L9 — the artifact tolerance accepts differences beyond float32 rounding (`s0` spike)

Stored float32 `600.005` against rebuilt `599.999` is a 0.006005 s difference that passed the 0.01 s
tolerance, although the two fall on **opposite sides of a 600-second threshold**.

**Fixed.** float32 quantisation is a known function, not an unknown error to absorb: the check now
casts this run's seconds to float32 and requires **exact** equality, and the report records
`verification_bypassed` when `--allow-artifact-mismatch` is used, so a bypassed run cannot be read
as a verified one.

## Test-suite note

Codex reports "the 252 tests outside acquisition passed" and that the acquisition tests hit
temporary-directory permission errors in its environment, which it did not count as product
failures. Re-run here after the H1 rewrite: **16 of 16 acquisition tests pass**, including the two
new cross-process ones.
