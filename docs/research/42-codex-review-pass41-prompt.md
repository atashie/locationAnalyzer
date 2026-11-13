You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: C:\Users\arikt\documents\github\distanceFinder, branch v2-rethink.
Python: v2/.venv/Scripts/python.exe. **Do not create temporary directories inside the repository** —
pass pytest an explicit `--basetemp` outside it, or skip the full suite and say so.

## What to review: phase 4b.0, the search-semantics spike

`v2/scripts/spike_search_semantics.py` and `docs/experiments/search-semantics-spike.json`, plus the
4b.0 sections of `docs/plans/2026-11-11-step4-comparator-plan.md` and the design's §12 amendment
item 6.

**The conclusion I have drawn, which is what I want attacked.** §12 item 6 (from your pass 37 F3)
says §2.4's lexicographic ranking "is not a property any single-scalar shortest-path implementation
has". The spike claims that is **too strong**: the failure is specific to pruning on *cost alone*,
and keying one label per node on the **pair** `(cost, time)` reproduces the normative answer. The
measured figures, over 3,267 random graphs:

| search | wrong cost | wrong reported time | labels per node |
|---|---:|---:|---|
| cost-only scalar | 0 | 119 (3.64%) | 1 |
| lexicographic `(cost, time)` | 0 | **0** | 1 |
| band of all cost-minimal labels | 0 | 0 | up to 6 |

and a claimed residual: in **162 of 3,267 (4.96%)** two or more winners tie on *both* cost and time,
so only the route-identity key separates them, and route comparison is **not** prefix-decomposable,
so no per-node label determines it.

## The claims to attack, hardest first

**A. Does a plain weighted graph even model item 6?** I assert that "the geometry, attachment and
connector layers contribute terms to a journey's totals and nothing to how a search prunes", and
test paths in a plain digraph instead of journeys. Attack that abstraction:
* A real journey is origin connector + entry + path + exit + destination connector, over **multiple
  destinations** with *different* connector costs. §2.4's key is
  `(cost, time, destination_id, route)` — the **destination id** sits between time and route. Does a
  single-source multi-goal search with per-node `(cost, time)` labels still reproduce the rule, or
  can a label for one destination's path prune a path that another destination needed?
* Partial-edge traversals mean the entry and exit terms are not edge weights. Does that change the
  pruning analysis, or only the constants?
* If the abstraction is wrong, the 3.64% and the 0% are both measuring the wrong thing. Say so and
  construct the journey-level counterexample.

**B. Is the `cost_only` search a straw man?** I built it to drop equal-cost arrivals. Anyone writing
it might instead break the tie on time at the node — which *is* the lexicographic label. So is the
3.64% a property of §2.4's rule, or an artefact of my choosing the worst admissible tie-break?
State what the fair baseline is and whether the finding survives it.

**C. Is the lexicographic label actually sound, or merely unfalsified on 3,267 small graphs?**
* My stated reason is cycle removal: costs and times are non-negative, so removing a cycle removes
  non-negative cost and time. Is the argument valid, and is it a proof or a plausibility story?
* **Zero-weight edges and zero-cost cycles are explicitly admissible in this design** (§2.4
  discusses zero-weight edges at length). Attack there.
* Check the implementation, not just the idea: the stale-label test is
  `if (c, t) != best.get(node): continue`. Can a node be improved after being popped, so that a
  correct answer is skipped? Can the heap order and the `best` dict disagree?
* Try larger graphs, denser graphs, wider and narrower weight ranges, and graphs where time and cost
  are strongly anti-correlated — which is the regime the rule exists for. Does 0 hold?

**D. Is the 4.96% residual the right residual?** I measure complete paths tying on `(cost, time)` at
the optimum, and claim route comparison is not prefix-decomposable.
* Verify the non-decomposability claim with a concrete pair of prefixes that order one way alone and
  the other way after completion.
* Is a route tie the *only* residual? What about the destination-id key, and what about §2.4's note
  that the six keys do not determine the **traversal**?
* I call this "a provenance ambiguity, not a wrong reported number". Attack that, the way pass 39 R4
  attacked the same phrasing about the T0 adoption: is there a route from an undetermined route
  identity to a changed reported quantity, given §12 persists the route and T10 consumes it?

**E. Does the population license anything?** 5–7 nodes, a spanning path plus 3–8 random arcs,
integer weights from a small range, chosen so exact ties are common.
* Is 3.64% presented as transferable to the Triangle graph anywhere it should not be? Check the
  plan and the design text as well as the script.
* Would the figure move materially under a different population, and is the script's own
  qualification adequate?

**F. The recommendation.** I conclude that the plan's three options collapse: adopt the
lexicographic label for the numbers, and decide the route identity separately in 4b.
* Is that the right call, or does something in §2.4 or §12 make the band necessary anyway?
* Is there a *fourth* option I have not considered?

## How to report

Severity (High / Medium / Low), the claim refuted quoted from the artifact, a **runnable**
reproducer, and the numbers it produces. Put reproducers under
docs/research/42-codex-review-pass41-counterexamples/ with a REPORT.md.

If a claim survives, say so explicitly and say what you ran. I am about to narrow a normative design
item on the strength of this spike, so a confirmed claim is as valuable to me as a defect — and a
wrongly narrowed gate is the most expensive mistake available here.
