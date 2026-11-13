# Codex adversarial review, pass 46 — the restricted-route disclosure and the decision report

You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at commit
`972abb7` plus one uncommitted correction to `docs/s3-decision-report.md` noted below. Python:
`v2/.venv/Scripts/python.exe`. **Do not create temporary directories inside the repository** — pass
pytest an explicit `--basetemp` outside it, or skip the full suite and say so. A graph load takes
about 90 seconds.

## What to review: step 8

* `v2/locfinder/traveltime/arrival.py` — `arrival_with_route_flag` and the new shared
  `_arrival_sweep`, which `arrival_with_selected_destination` now delegates to
* `v2/locfinder/traveltime/csr.py` — `graph_to_cost_time_flag_csr` and the extracted
  `_cost_time_core`
* `v2/locfinder/traveltime/snap.py` — `EdgeIndex.fwd_flag`/`rev_flag`, `_Snapped.matched_idx`
  and `took_end`, and `cell_route_flag`
* `v2/scripts/flag_restricted_routes.py`, `docs/experiments/s3-8-restricted-routes.json`
* `docs/s3-decision-report.md` and step 8's row and outcome block in
  `docs/plans/2026-11-04-s3-execution-plan.md`
* `v2/tests/test_route_flag.py` — 13 fixtures

Context: `docs/engineering-notes/project-phase1-s3-soft-way-dependence.md` (the owner's 2026-11-10
decision and what it made conditional), and §S3.4's three-outcome honesty mechanism.

## The claims to attack, hardest first

**A. Is the flag the flag of the route the product published?** This is the whole claim. Three
places could break it:

* `_arrival_sweep` propagates `flagged[node] = flagged[pred] or flag_t[pred, node]` over scipy's
  predecessor forest, in increasing-cost order. Is that forest the path whose **time** is reported?
  Among **equal-cost** paths scipy's choice is taken as given — the existing docstring admits the
  reported time of a tie is insertion-order dependent. Does the flag inherit that, and can a tie
  therefore disclose a restricted route for a journey whose published seconds came from an
  unrestricted one, or the reverse?
* `cell_route_flag` reads `snapped.took_end` to pick a direction. Verify that walking toward
  `e_idx` really traverses the geometry forwards given how `_snap_network` builds `time_end` from
  `fwd_t`, and that the loop-edge fallback (`s_idx == e_idx` → OR both) is reachable rather than
  dead.
* `EdgeIndex.fwd_flag` defaults to `None`, so the four hand-built indices in `expansion.py`,
  `data/pass11_edges.py` and `spikes/s1_expansion_directions.py` silently contribute **no edge
  flag**. Is that a live under-disclosure path, or unreachable from the published pipeline?

**B. Did the refactor change anything?** `arrival_with_selected_destination`'s body was replaced by
a call into `_arrival_sweep`. One fixture asserts the seconds and selected destination are
identical on a three-node chain. Attack that: compare old and new on the real graph, or on random
graphs with ties, one-way edges, parallel edges, unreachable nodes and a cutoff. The old body is in
git at `0cf91ea`.

**C. Are the published percentages the right quantity?** The headline is "the route depends on a
restricted way for 8,033 of the 78,627 structures included at ten minutes (10.2%)". Attack the
denominator — included structures rather than all answered ones — and check whether the flag is
being read at the structure's own coordinate or at the cell the product publishes for it, which
pass 44 and 45 both found mattered. Reproduce the four rows.

**D. The claim that the flag is not monotone.** A fixture asserts a cheaper route can be flagged
where a dearer one is not. Is the fixture actually exercising that, or does it pass for an
unrelated reason? And is there any *other* direction-of-effect claim left in step 8's code or
documents — instance twenty-two is the cost/time conflation appearing twice, so a third would be
worth finding.

**E. The decision report, which is the document a person will act on.** It is one page and it is
meant to be readable by the owner, not by me. Find:
* anything in the **"What is established"** table that is not established. I have already
  downgraded the attachment row myself — prevalence is measured, the A/B/C/D choice is open on
  verdict impact — and that correction is uncommitted at the time of this prompt; look for others
  of the same kind.
* anything in **"What is not established"** that is actually fine, since over-warning is also a
  failure of a decision document;
* whether "about one household in ten" is a fair reading of 10.2%–11.8%;
* whether the three things owed to each household are sufficient and actually deliverable, given
  that the flag is **not published in the layer bundle** — the report says so, but does it make
  clear that disclosure cannot happen today?
* whether the ranking in "what would change the verdict most per hour" is supported, or is a
  guess dressed as a finding.

**F. What step 8 has not done.** The flag is computed and not published; adding it is a wire-format
change. Is anything else in §0's step 8 scope silently unaddressed? Does the report omit a known
defect that belongs in a release decision — for instance the `spikes/g3-render` page being a spike
rather than a product, or anything in S3.5's open list?

## Output

For each finding: severity, the exact file and line, a **runnable reproducer**, and what it costs —
a number that moves, or a claim that must be withdrawn. Say which of my claims you checked and
could not break. If the decision report should not be handed to the owner in its current form, say
so in those words and say what is missing.
