# Pass 57 review prompt: four decisions put to the owner, and the owner's leanings

**Written 2026-11-16, committed before either reviewer was launched.** Two reviewers,
independently and without seeing each other's output: **Codex** (`gpt-6.1-sol`) and
**Antigravity/Gemini** (`gemini-4-hydrogen-xhigh`).

**This pass is different from pass 56.** Pass 56 judged twenty factual claims about two anomalies,
and it went badly for me: 11 confirmed, 7 overstated, 2 wrong. This pass judges the **analysis
built on top of the corrected facts** — four decisions I put to the owner, the mechanisms I said
cause them, the options I listed, and the recommendations I made. The owner has stated a leaning on
three of them and has explicitly asked for your input before committing; the fourth they raised
after the analysis was written, and it has already produced a measurement that contradicts
something I told them in pass 56.

**The owner's leanings are stated below. Your job is to try to break them, not to agree with
them.** A reviewer handed a hypothesis tends to hand it back confirmed, and the owner asked for
this review precisely to avoid that. If a leaning is right, say what would have made it wrong and
show that it is not. If it is wrong, say so plainly — the owner's pass-56 scepticism was correct
and they would rather hear it now than after a rebuild.

## Context

`v2/` is a location-finder. It publishes a uint8 minute raster per criterion; the browser spike in
`v2/spikes/g3-render/` ANDs them at user-chosen thresholds and paints a mask. The bundle holds
seven criteria as of commit `9cfa6c3`: grocery/walk, park/walk, school/walk, grocery/drive,
coffee/bike, Duke Hospital/drive, RDU/drive.

Governing principle: **selection is by cost, reporting is by time.** `cost = travel_time +
access_penalty_s(...)` (`v2/locfinder/traveltime/speeds.py:133`). A route is chosen on cost; the
household is shown real seconds.

Two grids exist and confusing them was the dominant error of pass 56: the **UTM source grid**
(EPSG:32617, 100 m cells) and the **published WGS84 lon/lat grid** the browser paints. Both happen
to be 514x643 = 330,502 cells. **Every number below must say which grid it is on.**

Relevant notes:

- `docs/engineering-notes/project-phase1-s3-donut-holes.md` — decision 1
- `docs/engineering-notes/project-phase1-s3-soft-way-dependence.md` — decision 2
- `docs/engineering-notes/project-phase1-s3-criteria-build.md` — decision 3
- `docs/research/57-review-pass56/` — the pass-56 reviews, both of them
- `docs/engineering-notes/feedback-verify-the-shape-of-the-risk.md` — the error ledger, 54 instances

**Environment.** Use `v2/.venv/Scripts/python.exe`; a bare `python` on PATH is the Windows Store
stub. Run pytest with `-o addopts=""`. The working copy is CRLF; `v2/scripts/explain_journey.py`
is LF. A patch must preserve each file's own endings. Do not edit `~/.codex/config.toml`.

Scripts, all runnable from `v2/`. The ones that load the 540k-node graph take about 90 s before
printing anything.

```
python scripts/measure_donut_holes.py
python scripts/explain_donut_hole.py --target park --mode walk --threshold 20 --holes 3
python scripts/measure_access_candidates.py --target park --mode walk
python scripts/measure_hole_edge_classes.py --target park --mode walk --threshold 20
python scripts/measure_restricted_walk_policy.py
python scripts/explain_journey.py            # prints OSM way ids per hop
python scripts/measure_unknown_hatch.py
python scripts/measure_hatch_visibility.py   # new with this prompt; no graph, runs in a second
```

The layer builder, where destinations are snapped: `v2/spikes/g1_own_graph_layer.py:102-109`.

---

# Decision 1 — the donut holes

A "hole" is an excluded cell whose eight neighbours are all included: a red parcel ringed by green.

## Claims

1. **Mechanism.** `snap._snap_network` calls `idx.tree.nearest(pts)`, which returns **exactly one**
   candidate edge per cell. A cell therefore inherits its nearest road's connectivity however bad
   that road is, while its neighbour snaps to a different road and gets a good answer.
2. **Size, published grid.** 121 holes on park/walk at 20 minutes, holding **356 buildings** across
   76 of the 121; the other 45 hold none. That is **0.07%** of the 500,451 buildings the published
   grid covers. (UTM source grid: 125 holes, 414 buildings.)
3. **The decisive unknown is not measured by anything in the repository: how many of the 121 are
   actually wrong.** A hole is the correct answer for a real cul-de-sac whose entrance is a mile
   round. The structural signal — a cell whose nearest edge's endpoint is far worse than an
   alternative inside the 200 m access cap — fires on about **90,000** cells, most of which will
   not be defects.
4. **A net hole count is not a repair count.** Filling one hole can complete a ring elsewhere and
   create a new one. Nothing in the work tracks hole identity, so no measurement so far states how
   many *original* holes any candidate fix repairs.
5. **No tag class explains it.** `service=parking_aisle` is 2.9x enriched and only 10.4% of holes;
   the largest single share is `residential` at 35.2%. Excluding a class would not fix it.
6. **Option 2 (multi-candidate snapping at the full 200 m cap, straight-line scored)** fixes 76% of
   holes and makes 77% of cells faster by a median 46 s with 0 cells slower, but the winning
   candidate's access leg is a median **169 m straight line** — through buildings, fences and
   gardens. It trades a visible wrong answer for an invisible one.
7. **Option 4 (find out whether the holes are OSM noding gaps first) is the only one of the four
   options that measures the unknown in claim 3.** The other three are bets on a number nobody has.
   This is my recommendation.
8. **The noding-gap question is answerable at a desk, across all 121 holes, with no code change and
   without taking any option.** "Do these two ways meet on the map without sharing a junction" is
   pure topology.

## The owner's leaning

> **"Measure first."**

## Where I think I am weakest on decision 1

**W1 — claim 8 may promise a measurement that cannot be conclusive.** A noding gap is not the same
thing as a walkable connection. OSM legitimately has ways that cross without a shared node:
bridges, tunnels, a path on the far side of a fence, a wall between two car parks. If the desk test
cannot separate "router bug" from "correctly unconnected", then option 4 produces a suggestive
number and not a decision, and recommending it is a stall dressed as rigour. **Say exactly what the
desk test should be, what it can and cannot conclude, and whether a sharper test exists.**

**W2 — option 4 may be the cheapest thing to recommend rather than the right thing.** Suppose the
answer comes back "60% of the holes are noding gaps". What then? Editing OSM upstream takes months
to propagate and is governed by this project's Decision 17 on sourcing. Make the adversarial case
that option 1 (disclose and move on) or option 3 (routed access leg) should simply be chosen now,
and that measuring first is a way of not deciding.

**W3 — "0.07% of buildings" may be the wrong way to express this risk at all.** 45 of the 121 holes
hold nothing, so the harm is concentrated in 76 parcels. Averaging over half a million buildings
may be the same category of error as the seven overstatements in pass 56: a true number attached to
a population that does not describe the harm. Propose a better statement of the risk if there is
one.

---

# Decision 2 — should the restricted-road penalty be per edge at all?

## Claims

9. **How it works.** `access_penalty_s` returns a flat `RESTRICTED_PENALTY_S[mode]` for a
   restricted edge: **120 s walk, 120 s bike, 450 s drive**
   (`v2/locfinder/traveltime/access.py:42,98-100`). It is added to **cost** only, never to reported
   time. These are declared priors, not measurements.
10. **It is charged per graph edge.** `speeds.py:133` adds it inside the per-edge loop.
11. **The walked audit route paid 360 s for 159 m of private track**, because that 159 m is three
    graph edges on **two** OSM ways. The identical 159 m drawn as one way would have been charged
    120 s. Counted from `explain_journey.py`, not estimated.
12. **Therefore the effective penalty is `120 s x (number of restricted segments crossed)`, which
    is a property of OSM's node density and not of the journey.** Two identical walks get different
    answers depending on how finely a mapper drew the road. For driving the multiplier sits on
    450 s, so the arbitrariness is nearly four times larger.
13. **The existing calibration table measures the wrong parameter.**
    `measure_restricted_walk_policy.py` reports that a 600 s penalty fixes the walked cell and
    costs 1.10% of 15-minute PASS buildings. That run varied `RESTRICTED_PENALTY_S` with the
    per-edge rule in place, so those rows describe `penalty x segment count`, not a per-journey
    penalty. **Deciding how big the number should be, before deciding what it is charged per, is
    calibrating a quantity that does not exist.**
14. **Three definitions, and what each costs.**
    - **(a) per edge** — today. Zero work. Incoherent: see claim 12.
    - **(b) once per continuous restricted stretch** — the faithful model, since what is being
      priced is the *decision* to use a private route. **I claimed a plain shortest-path search
      over edge costs cannot express this and that it needs the search to carry state (whether the
      predecessor edge was already restricted).**
    - **(c) per metre of restricted road** — a rate. Invariant to how roads are cut, because
      lengths sum. A one-line change. Arguable as behaviour: is 2 km of private track really ten
      times worse than 200 m?
15. **Calibration stays open either way.** The only evidence is the owner's own walk: published
    13.5 min, observed ~25 min. That says the current setting is too weak, but it says it through
    the per-segment lens, so it is not usable as a calibration until "per what" is settled.

## The owner's leaning

> **"Per stretch."** (option b)

## Where I think I am weakest on decision 2

**W4 — the most likely overstatement in the whole analysis, and the one I most want checked.**
Claim 13 says the distinction matters. **I never measured the distribution of restricted-edge
counts along selected routes.** If the median selected route that touches restricted ground crosses
exactly **one** restricted edge, then per-edge and per-stretch are nearly the same rule, claim 13
is noise, and the owner's leaning buys a state-expanded search for no behavioural change. **Measure
it:** over the published walk layers, for cells whose selected route crosses at least one restricted
edge, what is the distribution of restricted-edge counts, and of restricted *runs*? And what share
of published cells is affected at all? If it is 2% of cells this is a small decision; if it is 30%
it is the largest of the three.

**W5 — claim 14(b)'s cost is asserted from first principles, not from this codebase.** Verify it.
This pipeline already runs a **two-weight** search (`arrival_seconds_two_weight` over a `(cost,
time)` CSR pair) over ~540k nodes. Questions I could not answer: (i) is there an exact formulation
of per-stretch that avoids doubling the state space — for instance charging on entry to restricted
ground only, by splitting nodes or by a transition cost? (ii) does per-stretch break the
**admissibility / lower-bound** property the published `min_possible_s` plane and the
`BEYOND_HORIZON` status depend on, and would it break the 30/30 admissibility tests? (iii) what
does it cost in build time and memory at this scale? **A per-stretch rule is path-dependent, and
path-dependent costs break plain Dijkstra optimality unless the state is expanded — say exactly
what the state space must be, or show that a cheaper exact trick exists.**

**W6 — I may have the ordering wrong, and by the project's own rule.** The execution plan's §0
orders work by **product risk retired**, not defect severity. I presented these three decisions in
the order 1, 2, 3 — holes first — because that is the order the owner asked about them. But the
holes affect 0.07% of buildings on one layer, the penalty affects the *selected route* for every
walking journey that touches restricted ground, and the park bug silently removes destinations from
a published layer. **Rank the three by product risk retired and say whether my presentation order
is defensible.**

---

# Decision 3 — seven parks are missing, and every park is measured to its middle

## Claims

16. **How destinations are placed.** `g1_own_graph_layer.py:104-107` takes each place's
    **centroid**, snaps it to the nearest **node** with `ox.nearest_nodes`, and **drops** it if the
    nearest node is more than `POI_SNAP_MAX_M = 300 m` away.
17. **7 of 746 parks were dropped** and are simply absent from the park layer, with nothing on the
    page indicating anything is missing.
18. **One of the seven sits 0.2 m from an edge and 356.4 m from any node** (Gemini, pass 56, park
    `#456`). It is next to a path and was dropped because that path has no nearby junction.
19. **The asymmetry is the defect.** Origins snap to the nearest **edge** (`MAX_ACCESS_M = 200 m`);
    destinations snap to the nearest **node** (300 m). There is no stated reason for the
    difference. Making destinations behave like origins recovers **6 of the 7**.
20. **Gemini's subdivision route reaches the same 6 by manufacturing junctions** — splitting all
    302,067 edges over 100 m, which moves 74,930 OK cells and makes holes **worse** (125 -> 134 on
    the UTM grid). I would fix the attachment rule instead of the map.
21. **The centroid overstates distance for a large park.** For the 739 parks that *are* in the
    layer we measure to the middle, which for a large park can be several hundred metres past the
    gate. The answer is conservative and still wrong. Options: nearest point on the park boundary,
    a mapped entrance where OSM has one, or keep the centroid and disclose it.
22. **Fixing claim 19 is not free.** It changes every published layer, invalidates numbers quoted
    across the notes, and needs a full rebuild plus the suite.

## The owner's leaning

> **"We should never use a centroid, else large parks would be tagged as unrealistically far away
> from locations they abut (e.g., think Central Park)."**

## Where I think I am weakest on decision 3

**W7 — the owner's reasoning is sound in principle and its magnitude here is unmeasured.** Central
Park is 4 km long; the Triangle's parks are mostly small. **Measure the actual error**: for each
published park, the distance from its centroid to its own boundary, and then — for cells that
*abut* a large park — what the published park/walk layer currently reports against what it would
report if measured to the nearest boundary point. If the median error is 30 m the owner is right in
principle and the fix is low value; if the worst cases are 10 minutes of walking on the published
map, this is the biggest of the three decisions. **Either way, say which, with numbers on the
published grid.**

**W8 — nearest-boundary-point may be the wrong replacement.** A park boundary point can be across a
river, inside a fence line, on the far side of a motorway, or on the opposite side of a railway. It
is reachable in geometry and not on foot. **Is nearest-boundary-point actually better than centroid,
or does it just move the error and make it optimistic instead of pessimistic?** An optimistic error
on a published map is worse than a pessimistic one. Consider mapped entrances
(`barrier=gate`, `entrance=*`), boundary points that lie within the access cap of a road, or a
polygon-aware target, and say what you would do.

**W9 — claim 22 is unquantified.** How many destinations across the seven published criteria
actually move if destinations snap to edges rather than nodes, and how many published cells change?
If the answer is "6 parks and 400 cells" the rebuild argument is overstated; if it is "every layer
moves" it is the dominant cost of the decision.

---

# Decision 4 — the grey diagonal striping

**The owner raised this after the analysis above was written**, and it is the one place where a
pass-56 verdict now looks wrong. In pass 56 I told them the hatch was "the renderer working as
designed" and both reviewers CONFIRMED the claim it rested on. The owner disagreed with the
*judgement*:

> **"I disagree that the grey diagonal lines of nodata are okay — those striping effects are
> problematic and should be rectified."**

Taking the complaint seriously produced a measurement nobody had taken. **`v2/scripts/measure_hatch_visibility.py`
is new with this prompt**; run it, it needs no graph and finishes in a second.

## Claims

23. **The paint rule.** `worker.js:473` paints an UNKNOWN cell `PX_NODATA` only where
    `(row + col) & 7 < 2`, and `PX_OUT` otherwise. `PX_OUT` is `0` — fully transparent, the
    **byte-identical** value given to an EXCLUDED cell. `row`/`col` are published-grid indices.
24. **So the hatch marks a quarter of the cells it is supposed to mark.** Published grid,
    park/walk at 20 min: **56,034 UNKNOWN cells, 14,023 painted (25.03%), 42,011 painted exactly
    like a confident "no".** (14,023 independently matches Gemini's pass-56 count.)
25. **A third of the UNKNOWN regions carry no mark at all.** 8-connected: **1,075** UNKNOWN
    regions, of which **369 (34.3%)** contain not one painted cell, covering 975 cells. On screen
    those regions are indistinguishable from EXCLUDED. The disclosure silently fails.
26. **Invisibility is concentrated in the small regions, and the design works for the big ones.**
    Of single-cell regions, **73.1%** are wholly invisible; of 2-3 cell regions, **64.6%**; of
    9-16, **12.9%**; of regions of **65+ cells, 0%** — all 166 of those are marked. Median region
    size is 7 cells.
27. **Therefore "the renderer working as designed" was wrong for a third of the regions**, and
    pass 56 did not catch it because it checked that the hatch *rule* was deliberate (claim 1,
    CONFIRMED, correctly) and never asked whether the rule marks the set it names.
28. **Not Park-specific.** All three walk layers hold the same 56,036 OFF_NETWORK cells and give
    identical counts at every threshold, which re-confirms pass-56 claim 3.
29. **The underlying condition is real and is not a rendering bug.** 56,036 of 330,502 published
    cells (**16.95%**) are more than `MAX_ACCESS_M = 200 m` from any road in our graph, so no
    journey was ever measured from them and the published `value` is a lower bound.
30. **Two separate fixes exist, and the owner's complaint could be satisfied by either**: change
    how UNKNOWN is drawn, or shrink the UNKNOWN set. They have different costs and different
    honesty properties.

## Options I can see

**Rendering:**

- **(i) A solid translucent fill in a distinct colour.** Every UNKNOWN cell gets marked, claim 25
  goes away, no aliasing. Cost: ~17% of the map becomes a flat grey wash.
- **(ii) Keep a texture but guarantee every region is marked** — e.g. hatch, then force at least
  one marked cell per connected region, or outline each region.
- **(iii) Outline or stipple region boundaries only**, leaving interiors clear.
- **(iv) Compute the pattern in screen space after the map's scaling**, instead of in grid space,
  which is what makes it alias.

**Shrinking the UNKNOWN set:**

- **(v) Raise `MAX_ACCESS_M` above 200 m.** Same lever as donut-hole option 2 and the same
  straight-line-access objection; it buys fewer UNKNOWN cells with less honest times.
- **(vi) Clip the published region to the networked area** and stop publishing cells we were never
  going to be able to answer. 56,036 cells is ~560 km² of mostly rural land.
- **(vii) Leave them transparent and disclose the count in the legend** rather than on the map.

## Where I think I am weakest on decision 4

**W10 — I do not know which visual artefact the owner is objecting to, and the fix differs by
cause.** The hatch is computed in **grid space** and the canvas is then scaled by the map, so what
a reader sees depends on zoom: at low zoom the 2-in-8 pattern resamples against the screen grid and
should moiré; at high zoom it should render as chunky diagonal bands; and the small regions in
claim 26 should appear as isolated grey specks at any zoom. **Say which of these the code predicts
at which zoom level**, and which one the phrase "striping effects" most likely describes. Do not
assume my reading of the complaint is right.

**W11 — I do not know that a solid fill is better.** Making 17% of the map a flat grey may read
worse than striping, and it may read as *data* rather than as absence. This is a design judgement
and I am poorly placed to make it. Say what you would do and why.

**W12 — challenge the premise.** Is UNKNOWN even the right verdict for these cells? A cell more
than 200 m from any road on a 100 m grid is usually not a place anybody lives: only **0.67%** of
published-grid buildings sit in them. Option (vi) — publish a smaller region and stop claiming
anything about land we never modelled — may be more honest than any rendering of it, and it
removes a whole category of reader confusion rather than restyling it. Argue against this if it is
wrong.

**W13 — claim 25's harm is in cells, not buildings, and I could not fix that.** The buildings
raster exists only on the UTM grid and the exporter's reprojection is nearest-neighbour, which does
not conserve a count, so **how many buildings sit in the 369 invisible regions is unmeasured.**
That is the number that decides whether claim 25 matters. If you can compute a defensible
published-grid building count, do it and say how.

---

# What a useful review looks like

- **Run things.** A counterexample that executes beats an argument. Give the command and its
  output. Gemini could execute Python in pass 56 and that is what settled W7; Codex could not and
  constructed its counterexample by hand, which also worked. Use whatever you have.
- **Per claim: CONFIRMED, WRONG, or OVERSTATED**, with the evidence. "Overstated" is a real verdict
  and this project's ledger records that I reach for it too rarely — pass 56 found seven of them,
  every one a true number attached to a population it did not describe. **If a number here does not
  name its grid, its threshold, its layer or its pipeline stage, that is the defect.**
- **Verdict on each of the four owner positions: SUPPORTED, UNSUPPORTED, or PREMATURE**, and say
  what measurement would move it. "Premature" means the position may well be right and the
  measurement that would justify it has not been taken. Decision 4's position is a product
  judgement the owner is entitled to make regardless of evidence — there, judge the *options* and
  my reading of the complaint, not their right to object.
- **Rank the four decisions by product risk retired** (plan §0), and say whether my ordering is
  wrong. Note that decision 4 arrived last and may well rank first.
- **Say what is right too.** A review that only lists faults cannot be weighed.
- If you think a *recommendation* is wrong, say what you would do instead, concretely.

**Do not change code and do not take an option.** All three decisions are the owner's and none is
taken. Write a judgement, not a patch.
