# Codex adversarial review, pass 14 — the S2.3 rebuild, the resolver benchmark, the S3 design

**Date:** 2026-11-04. **Model:** gpt-6.1-sol. **Head at review:** `17c44f8`. **Prompt:**
`codex-pass14-prompt.md` (scratchpad).

**Sixteen defects: 7 High, 7 Medium, 2 Low.** The opening sentence is the one that matters:

> "The headline numbers reproduce. **The rebuild still does not establish the claimed
> private-through-traffic or building-coverage bound, and the expanded benchmark misses three of the
> four targeted merge regressions.** I also reproduced another resolver over-correction."

So: the rebuilt audit's *arithmetic* is right and its *claim* was still too strong — the second time
on the same question — the benchmark I built to catch merge regressions did not catch three of
them, and my own fix from last round manufactured a confident wrong answer.

## What survived attack

Recorded because a review that lists only failures misrepresents what was checked.

- **The language is its own reverse by algebra**, so there is no length-7 counterexample; my
  brute-force enumeration to length 6 is supplementary.
- Product-edge direction, `state*n+i` indexing, destination seeding in state 0, and minimising
  across accepting states are all **correct**.
- `min_time` groups directed pairs and applies `minimum.reduceat` correctly, and **time-minimum
  versus time-minimum is the appropriate counterfactual** for this abstract policy.
- Splitting directed restricted edges preserves original-node paths and additive weights, including
  parallel alternatives, and **holding destinations fixed is correct for that test**.
- Every measured figure reproduced: 2,700 both-class pairs, 2,833/539,814 = 0.5248%, 38,939
  slowdowns, 12.3106 s median, 2,092/507,037 = 0.4126%. Split difference **1.46 × 10⁻¹¹ s** — I had
  reported it as 0.000000 s, which is rounding, not the figure.
- The statistical arithmetic: 4.8703% at *n*=60 and 31.2344% at *n*=8 one-sided exact, and 385 for
  five points.

## H1 — `R* O* R*` does not establish "not through-traffic over private land"

**I withdrew the lawfulness claim once already, and the replacement was still too strong.**

Codex's counterexample: an origin in estate A, a destination in estate C, joined by a continuous
restricted road through *unrelated* estate B. That is `RRR`, which the language **accepts**, while
B is plainly being used for through traffic. The automaton sees edge *classes*; it cannot see whose
access chain an edge belongs to, so it cannot distinguish a driveway from somebody else's private
road. Conversely `ORO` may describe an entitled traveller using a connection they are allowed to
use.

And the obvious repair fails: **requiring a non-empty open middle would wrongly reject** a resident
walking across their own estate.

**Absorbed.** `policy.py` now says the module decides membership in an edge-class language and
nothing else; the contract and the plan say the same. Two withdrawn framings in two passes on one
question is worth naming for itself: the pull each time was to convert a computable property into
the product claim I wanted, and the computable property was never that claim.

## H2 — the building figure is a nearest-node proxy

Assigning each building to its nearest node within 200 m assumes a connector that is **zero-time,
unrestricted and traversable**. None of those is established: a straight line to the nearest node
may cross a fence or another property, and **the connector's travel time is not added at all**, so
a node at 7,190 s with a 100 m connector still counts inside a 120-minute horizon. Destination
snapping makes the matching assumption at the other end — a grocery becomes a zero-cost destination
node up to 300 m away.

I had chosen the building weighting specifically to *avoid* the cell-snapping defect of pass-13 H1,
and it reintroduced an unverified connector at the same place.

**Absorbed.** 2,092 is labelled a nearest-node proxy everywhere it appears, and the contract's
"under half a percent of buildings" conclusion is withdrawn. Claiming building *service* needs both
endpoint connectors modelled with their classes carried through the automaton.

## H3 — `symmetrise` discards reverse alternatives, in production

The one that reaches beyond the audit. `speeds.symmetrise` asked `G.has_edge(v, u)`, so the
existence of **any** edge from *v* to *u* suppressed the reverse of **every** road from *u* to *v*.

Codex's executed input: `P→B` open/5 s, `A→B` open/100 s, `B→A` restricted/1 s, `A→D` open/5 s. The
open `A→B` road gets no walkable reverse, so P is unreachable under any policy that declines the
restricted edge; adding the missing open reverse makes the journey **110 s**.

> "Separating classes on the multigraph cannot recover an alternative already lost upstream."

**Absorbed.** Reverses are now added per **physical road**, deduplicated by `osmid` and length
rather than endpoint-pair existence. This changes the shipped walk graph, so the S2.3 and S2.4
figures were re-measured on the corrected graph.

## H4 — my own fix manufactured confidence

The leading-tier promotion I added last round ran inside `_merge_corroborating`, so `_decide` saw
the promoted order. Codex's executed input: query `Northside Durham`, an OSM bus stop named exactly
that at 1.00 on the intact reading, and a restaurant `Acme` aliased `Northside` at 0.95 on a
stripped reading. Promotion put the restaurant first and `_decide` then read its sole locality match
as decisive — **resolved to Acme**. Unpromoted the same input is ambiguous, which is correct.

Codex also corrected a premise in my own prompt: I had asked whether `_decide` ran before
promotion, and it did not.

**Absorbed.** The outcome is decided on the canonical score ranking; promotion is applied
afterwards, for presentation only. A reordering intended to improve a chooser must never be able to
remove the chooser.

## H5–H7 and M4–M6 — the S3 design

Revision 1 was predeclared and wrong in six ways, so it is now revision 2 with a change log in its
own §10.

- **H5, the strata overlap.** A building can be boundary-adjacent *and* within one encoding
  increment *and* in the whole-frame sample at once, so pooling with `N_h / n_h` counts the same
  population mass repeatedly. Now: two **self-weighting simple random samples** estimate the
  populations, and the four former strata are **diagnostics that are never pooled**.
- **H6, a building frame cannot estimate all-cell rates.** A cell with no buildings has zero
  selection probability; one with a hundred has a hundred chances. Swapping `N_h` does not fix it.
  Now two frames, each reporting only its own estimand, with frame C sampling a cell and then a
  uniformly random point inside it.
- **H7, the gate had no acceptance rule**, so the verdict stayed selectable after the fact. Now
  explicit: E1a ≤ 2.0% and E1b ≤ 1.0% on the one-sided 95% upper bound, an INCONCLUSIVE outcome, and
  every mode, threshold and frame must pass.
- **M4, DEFF is inestimable at zero failures** — the expected case. Now fixed 2 km blocks, a named
  variance estimator, a minimum of 5 sampled points per block, and a **predeclared DEFF = 2.0
  fallback**. One interval convention throughout (one-sided exact), with the Wilson alternatives
  tabulated so the choice is visible.
- **M5, no executable comparator.** Now specified: origin, destination set, direction (origin →
  destination, *not* the surface's internal direction, because a one-way road breaks the symmetry),
  both selection objectives, datetime, connectors — plus a **verdict table for every status**, in
  which a definitive "no path" against a product *pass* is scored as E1b rather than filed under
  missing, and the unknown bucket is **bounded both ways** with an INCONCLUSIVE result if the bounds
  straddle a threshold.
- **M6, E3 was unfalsifiable.** "UNVERIFIED whatever these journeys show" meant eight journeys each
  taking three times the prediction could not produce the `failed` outcome the design advertises.
  Now a predeclared magnitude-based falsification rule, with the population *rate* still
  UNVERIFIED. Codex also notes the binomial bound does not strictly apply to an owner-chosen
  convenience sample, which is now stated.

## M1–M3 — the benchmark's own weaknesses

**M2 is the one that stings:** Codex reverted each historical merge over-correction in memory and
measured which benchmark assertion turned red.

| reintroduced regression | newly red benchmark assertion |
|---|---|
| pass-10 H4, equal raw categories | `Harris Teeter Carrboro` |
| pass-11 M1, raw subsidiary set | **none** |
| pass-12 H4, subsidiary-vs-parent boolean | **none** |
| pass-13 M7, `halt→stop`, `kiosk`/`information`→fixture | **none** |

I built the benchmark to guard exactly those. **I then ran the same four reversions against the
unit tests, and all four are caught there** — so the guard exists, in `tests/test_resolve.py`, and
my claim that the *benchmark* was the guard was wrong. The division is now stated: unit tests are
the regression guards on constructed fixtures; the benchmark is the instrument on the real index.
A real-index merge tripwire was added as well (`min_corroborated`), so a merge regression also
shows up there.

**M1 and M3: several assertions could be satisfied by a wrong answer**, with executed examples — a
`dessert_shop` 731 m from the mall reference passing "Southpoint" on a 5 km check; a Raleigh bus
stop leading while a *different* candidate supplied the proximity; `Train Station` in Raleigh passing
"Durham train station" on role membership alone. Codex audited all 41 rows and found the weakness
systematic.

Absorbed by adding assertion kinds that **pin location and identity to the same candidate** —
`lead_near`, `lead_name_contains`, `offered_named_near`, `no_candidates`, `min_corroborated` — and
tightening nineteen rows. Codex also found an assertion in the *other* failure mode: the Weaver
Street branch requirement would have **rejected a correct Hillsborough or Raleigh branch**. An
assertion no correct answer can pass is as bad as one a wrong answer can; it is now identity-only.

**Tightening them immediately exposed two more live defects** that had been passing:

- `Duke Hospital bus stop` led with a stop **34.9 km away**, because its name contains all four
  query words while the Durham platform actually called "Duke Hospital" matches two. The transport
  phrase is *intent*, so the phrase-free form is now a further reading on the ladder.
- `Durham train station` resolved **confidently** to a place named `Train Station` **32 km away**
  whose locality field is empty — so a contradiction test would not have fired. A typed locality
  must now be **confirmed** for confidence, not merely un-contradicted.

The second of those took two attempts: my first version tested `locality_match`, which is a
*per-reading* flag, so a leader that won on the intact query has it False even when its locality is
exactly what the user typed — which made "market carrboro" ambiguous although Carrboro Farmers
Market is in Carrboro. Six existing tests caught it. It now reads the locality **field**.

## M3 and L1 — the smaller ones

- **The bare-locality explanation was false.** I wrote that a POI index cannot hold a place with a
  locality's name. Codex counted **62 records whose normalised names equal 29 distinct locality
  strings** in this index — Burlington stores, a Gulf fuel station — and they are legitimate
  businesses. The *behaviour* stands (abstain) but the reason is **entity-type ambiguity**, not
  absence, and a business whose entire name is a locality is now reachable but never confident,
  which is a cost recorded rather than hidden. Codex also counts **228** localities, not 229.
- **L1, the apostrophe fix missed U+00B4.** `_INTRAWORD` ran *after* NFKD, which decomposes the
  acute accent into a space plus a combining mark; the mark was stripped and the space survived, so
  `Trader Joe´s` normalised to `trader joe s`. Now removed before NFKD. Codex notes deletion cannot
  universally represent a word boundary — `fish'n'chips` becomes `fishnchips` — which is recorded as
  a known limit, since the possessive dominates real names.
- **L2, stale labels**: "lawful but slower" omitted sub-second slowdowns and is now "more than one
  second slower"; the plan still called the withdrawn 5,533 cells / 4,881 buildings "the real
  figure"; E2 was defined against reported time and compared against the float surface.

## The test-count discrepancy

Codex reports 302 passes with acquisition-test failures from sandbox filesystem permissions, and
could not confirm the stated 320. Locally the suite is **328 passed** after this round's additions.
The acquisition tests need real file locking, which its sandbox denies; that is an environment
difference, not a disputed result, and the two new cross-process lock tests are the ones affected.
