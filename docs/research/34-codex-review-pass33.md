# Codex adversarial review, pass 33 — destination recovery

**2026-11-10.** Reviewed `aeef909`, `00b597e`, `592df76` on `v2-rethink`. Six findings: one P1,
four P2, one P3. All six reproduced and fixed in the commit that follows this note.

The counterexamples Codex retained are committed beside this note in
`34-codex-review-pass33-counterexamples/` — `real_review.py`, `fullcheck.py`, `survivors.py`,
`ties.py`. They were left in an untracked `v2/.review33/` and would have been lost; the repo's rule
is that anything needed to reproduce a result is committed with it.

## The findings

**F1 [P1] The recovery silently overwrote walked observations.** `recover_audit_destinations.py`
opened its output with `"w"` and no existence guard, so rerunning the command documented in the
sheet's own README would erase anything the owner had typed into
`*-with-destinations.csv`. Codex reproduced it on a private copy: an output containing an
observation was overwritten and the script returned 0. `audit_recommendations.py` already refuses
to overwrite a sheet *for exactly this reason* and this script did not copy that. Now refuses,
with `--force`.

**F2 [P2] My proof of configuration identity did not hold** — and I had already found half of it
independently while building an unrelated baseline. Two separate defeats:

- The destination check compared three **counts** against s0's recorded provenance. Replacing
  destination node 539680 with 500268 preserves every sampled value in both sheets while changing
  **1,798 node arrival times**. The provenance does not store the node set, so no available check
  can establish set identity.
- A current-code rebuild differs from the committed raster on **7,246 of 330,502 cells**, max
  2,316.8 s, finiteness unchanged, 10 cells changing verdict at ten minutes. Cell (0, 425): stored
  942.5269165, rebuilt 925.9172974. **None of the 35 audit rows is among them**, which is why the
  sampled check passed. The stored raster still matches the sheet metadata's SHA-256, so the sheets
  did come from it.

Codex also built a synthetic tie that changes the selected shop while preserving the seconds
exactly, so numeric agreement cannot establish historical identity even in principle. The cause of
the 7,246 is in [[project-phase1-s3-stale-walk-raster]]: `ab01ffa` fixed `symmetrise` eight hours
after the raster was built.

**F3 [P2] A verification failure still wrote the sheet.** `mismatches` was checked *after* writing.
Injecting a one-second discrepancy produced 16 mismatches, wrote the complete output, then returned
1 — so a failed run could replace a good sheet with unverified destinations, while the docstring
claimed it refused to write. Now verifies before opening the output; confirmed by a tampered
private copy that is caught and writes nothing.

**F4 [P2] `recheck_matches_sheet=yes` did not check the sheet.** It compared the rebuild against
the raster only. Setting a row to `seconds=1.0, outcome_10min=FAIL` still produced
`predicted_seconds_recheck=578.0` and `recheck_matches_sheet=yes`. A stale or edited sheet could
receive destinations for a different prediction and be told they agreed. Now compares against both
the raster and the sheet's own column, and reports which failed.

**F5 [P2] Two wrong implementations survived all tests**, including the fixture guard I had just
added for the sixth instance of this pattern:

- **Name the endpoint chosen by *time* while reporting seconds chosen by *cost*.** My
  `test_the_two_endpoints_select_different_shops` guarantees a different shop behind each endpoint,
  which I had asserted as the property that made the branch observable. It is not sufficient: on
  that fixture the two selection rules pick the same endpoint. With the forward road's cost raised
  to 1000, the reported journey is 91 s via shopS while the mutation names shopE at 19 s. This is
  the defect that matters on the ground — it prints our seconds beside a shop they are not about.
- **Remove the cell-level cutoff mask**, so a cell with infinite seconds still names a shop. The
  node is inside the budget and the cell is not, because access is charged after the node search.

Both now have tests and both are in the harness: **10 mutations, all caught.**

**F6 [P3] The engineering note miscounted three ways.** Nine physical destinations under seven
names (Harris Teeter and Food Lion are two shops each); my enumeration omitted the journey to The
Fresh Market; and **531 of 550**, not all 550, carry taxonomy primary `grocery_store` — the other
19 carry more specific grocery primaries and satisfy the rule through the hierarchy. All three
verified against the data before correcting.

## What it confirmed

The risk I ranked first — that `cell_seconds_from_arrival` might attribute a journey to a different
branch than `cell_arrival_with_provenance` — **did not reproduce**: the two agree on all 330,502
cells including horizon handling. Cell-centre indexing is correct and the 0.069 m rounding
explanation reproduces. Neither sheet has an equal-nearest-edge tie, and reversing source and node
order changed no sampled destination. Both mutation harnesses caught their listed mutations and
restored their sources byte-identically. 1,164 passed / 24 skipped. No tracked file was changed.

## The pattern, again

Four of the six findings are in the verification rather than the computation: a check that wrote
before verifying, a check that compared the wrong pair, a check that compared counts and was read
as comparing sets, and a mutation set that missed the two cases that mattered. The destination
recovery itself was essentially sound.

That is the same distribution as passes 31 and 32, and the same as the sixth instance recorded in
[[feedback-verify-the-shape-of-the-risk]] — to which F5 adds a sharper version: **asserting a
property of the fixture is not enough if it is the wrong property.** I added
`test_the_two_endpoints_select_different_shops` specifically to stop a degenerate fixture, and the
degeneracy that mattered was a different one.
