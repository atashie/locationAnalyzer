# Codex adversarial review, pass 47 — the pass 46 repairs, and the FAILED verdict

You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at commit
`1a72551` plus one uncommitted addition to `docs/s3-decision-report.md` described in §A. Python:
`v2/.venv/Scripts/python.exe`. **Do not create temporary directories inside the repository** — pass
pytest an explicit `--basetemp` outside it, or skip the full suite and say so. A graph load takes
about 100 seconds.

**This reviews the repairs to your pass 46, and one new claim.** Your report is at
`docs/research/47-codex-review-pass46-counterexamples/REPORT.md`. For each of your findings the
question is whether the repair **closes, narrows or moves** it. A repair that moves a defect is
worth more to me than a new finding elsewhere.

| your finding | what I did |
|---|---|
| F1, the scorer says FAILED | the report now leads with `score_e3`'s own output; "engine disagreement is reported" became "not measured in this release" |
| F2, the wrong unit | the script always computes both units and labels the published cell as the only one a disclosure may use; headline is now 7,271 / 80,067 (9.1%) |
| F3, endpoint disclosure | `cell_route_flag` excludes zero-length matched-edge traversal using `_snap_network`'s own `_NODE_EPS` overrides; fixture added |
| F4, attachment row | corrected to A/C/D, B marked not implemented, 843,685 census points |
| F5, household prevalence and the ranking | reworded to structures; the ordering is labelled a proposed prioritisation |
| F6, "nearest grocery" | restated as "the grocery the routing cost rule selects"; the upper-bound sentence narrowed to the modelled cell-centre journey |
| F7, release prerequisites | a prerequisite list added, naming the unpersisted flag, the unpersisted destination, node-is-not-a-shop, the unbuilt card, phone latency, the recomputation UI, the geocoding audit, and that `g3-render` is a spike |

## The claims to attack, hardest first

**A. The new robustness claim, which I added after your pass and which you have not seen.** The
report now says: the observation is "~25 minutes", the outcome flips to `FAILED` at **16.9
minutes**, and it would take the real walk being under 17 minutes to return `UNVERIFIED`. Attack
it:

* is 16.9 the real boundary, and is it the boundary of **both** limbs or only the binding one?
* is `Journey("band15min_pass-03", 810.8186, 1500)` the right **pair of numbers**? Where does
  810.8186 come from, is it this cell's published answer or the audit sheet's prediction, and is it
  the quantity `score_e3` expects? If the reported figure is a cell-centre answer and the walk
  started at a door, the pair may not be comparable at all — which would make the verdict
  inadmissible rather than robust.
* does feeding a **single approximate** observation into a scorer designed for a set of journeys
  misuse it? Check what `score_e3` assumes about its input, including whether the median limb is
  meaningful at *n* = 1, and whether `walked=1` with `planned=0` is the state it expects.
* **and the question I most want answered: should this verdict appear in the report at all?** If
  the right answer is "the scorer cannot be applied to this observation", say so in those words —
  that would mean my correction over-corrected, and I would rather know.

**B. Is "engine disagreement: not measured" now wrong in the other direction?** `v2/data/layers/`
holds `matrix_grocery_*.json` and Valhalla layers, and G1 compared engines. If a magnitude exists
anywhere in the repository, the report should cite and qualify it rather than say nothing was
measured. Find it or confirm there is none at this extent.

**C. Does the F3 fix cover every zero-traversal case?** It excludes the matched edge's flag when
`took_end & at_end` or `took_start & at_start`. Attack the cases I may have missed: a point at a
node that is *also* the loop-edge fallback; a point within `_NODE_EPS` but not exactly at a node; a
point whose access distance is zero but whose matched edge is still partly walked; and whether the
**node** flag can itself over-disclose at an endpoint the way the edge flag did.

**D. The published-cell unit.** The script now clips the row/column into range with `np.clip`.
Does that silently relocate a structure outside the footprint into an edge cell — the thing
`GridSpec.cell_for_xy` refuses to do by returning `None`? Check how many structures are affected
and whether any figure moves.

**E. The report as a document a person will act on.** Read it as the owner would.
* Is the FAILED verdict now stated so prominently that a reader could conclude the product is
  broken everywhere, when the measurement is one journey on a restricted route?
* The prerequisite list says no disclosure can be delivered today. Does any sentence elsewhere
  still imply otherwise?
* Is anything now **under**-stated — over-warning is also a failure of a decision document, and I
  have just over-corrected once.
* Does the report give the owner enough to decide, or does it only give them reasons to wait?

**F. Anything the repairs introduced.** The sensitivity sweep, the three-population script, the
corrected prerequisite list, and `test_route_flag.py`'s 14th fixture are all new. Review them as
new code and new prose, not as repairs.

## Output

For each finding: severity, the exact file and line, a **runnable reproducer**, and what it costs —
a number that moves, or a claim that must be withdrawn. For each pass 46 finding, say whether the
repair closes, narrows or moves it. Say which claims you checked and could not break. If the E3
verdict is inadmissible on this observation, say so in those words.
