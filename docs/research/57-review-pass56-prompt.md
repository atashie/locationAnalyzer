# Pass 56 review prompt: two anomalies the owner found, and the claims I made about them

**Written 2026-11-16, committed before either reviewer was launched.** Two reviewers, independently
and without seeing each other's output: **Codex** (`gpt-6.1-sol`) and **Antigravity/Gemini**
(`gemini-4-hydrogen-xhigh`).

**The owner is sceptical of these findings and asked for this review.** That is the right
starting posture and the prompt is written to serve it: every claim below is numbered, and a
reviewer's job is to try to break each one by *running it*, not by reasoning about it.

## Context

`v2/` is a location-finder. It publishes uint8 minute rasters per criterion; the browser spike in
`v2/spikes/g3-render/` ANDs them at user thresholds and paints a mask. On 2026-11-16 the bundle
went from one criterion to seven (commit `9cfa6c3`). The owner opened the page and reported two
anomalies. Commit `a5ff969` is my answer to them; the note is
`docs/engineering-notes/project-phase1-s3-donut-holes.md`.

Everything is reproducible from the repo. Scripts, all runnable from `v2/`:

```
python scripts/measure_unknown_hatch.py          # claims 1-5
python scripts/measure_donut_holes.py            # claims 6-9
python scripts/explain_donut_hole.py --target park --mode walk --threshold 20 --holes 3
python scripts/measure_access_candidates.py --target park --mode walk   # claims 12-16
python scripts/measure_hole_edge_classes.py --target park --mode walk --threshold 20
```

The last three load a 540k-node graph and take about 90 s before producing anything.

**Environment.** Use `v2/.venv/Scripts/python.exe`; a bare `python` on PATH is the Windows Store
stub. Run pytest with `-o addopts=""`. The working copy is CRLF; a few files are LF and a patch
must preserve each file's own endings. Do not edit `~/.codex/config.toml`.

## The claims, numbered. Attack each one.

### Anomaly 1 — grey diagonal pixels

1. The diagonal is the renderer's deliberate hatch for UNKNOWN: `worker.js` paints
   `(row + col) & 7 < 2` in `rgba(60,60,60,130)`. It is not an artefact of the data.
2. On walk layers UNKNOWN comes **entirely** from `OFF_NETWORK`, never from `BEYOND_HORIZON`,
   because `horizon_s` (7200) >= 60 x threshold for every threshold the slider offers.
3. The hatched set is **identical across all three walk layers** (grocery, park, school), because
   `OFF_NETWORK` is a property of the cell's distance to the network, not of the destination
   category. So it is *not* specific to Park, which is what the owner reported.
4. The hatched count grows with the limit and then saturates: measured in the live page,
   38,834 cells at 5 min, 53,764 at 10, 56,034 at 20, then flat. The saturation is because the
   largest published lower bound on an `OFF_NETWORK` cell is **21 minutes**.
5. It covers 17.4% of cells and **0.71% of buildings** (3,657 of 512,633).

### Anomaly 2 — donut holes

6. A "hole" is an EXCLUDED cell whose **eight** neighbours are all INCLUDED. On `park/walk` at
   20 min there are **125**; grocery/walk 20 min, 113; school/walk 20 min, 132.
7. Every hole has status `OK` — these are computed times, not off-network artefacts.
8. A hole is a median **241 s** slower than the mean of its eight neighbours, max 753 s
   (park/walk, 20 min).
9. The 125 holes hold **414 buildings**, and **75** of them contain at least one.
10. The cause is `snap._snap_network` calling `idx.tree.nearest(pts)`, which considers **exactly
    one** edge per cell. In the three largest holes the whole gap is in the arrival at the matched
    edge's chosen endpoint (`atnode`), not in the access leg and not in the on-edge walk.
11. The owner's proposed mechanism is wrong: on-edge travel is `(1 - frac) * fwd_t`, strictly
    proportional, so a mid-edge cell pays half the edge and is **not** penalised to the nearest
    node. And their proposed fix — artificial nodes along long edges — would change nothing,
    because subdividing an edge does not change shortest-path distances.
12. Taking the best edge within the existing 200 m access cap: holes 125 -> 30, **210,533 cells
    (77.1%)** improve by more than 1 s, median 46 s, p99 1,312 s, and **0** cells get slower.
13. For the 90,040 cells improved by more than 60 s, the **winning** edge's access leg is a
    median **169 m** straight line, p90 196 m, with only **1.0%** within 50 m — against a median
    38 m for today's nearest-edge leg. This is why I did not recommend the fix.
14. Restricting alternatives to "nearly as close as the nearest" (+50 m) removes only **23%** of
    the holes.
15. No tag class explains it: `service=parking_aisle` is 2.8x enriched but only 10.4% of holes;
    the largest single share is `residential` at 35.2%.
16. One hole traced to OSM by hand: its matched edge is way 461005440/461005460,
    `service=parking_aisle`, which **shares no node** with way 746439842 (Atlantic Avenue,
    `secondary`) 33 m away.

## Where I think I am weakest. Start here.

**W1 — the one I most want checked.** `measure_access_candidates.py` builds `cur_total` by
**recomputing** `_snap_network` on a freshly loaded graph, and compares the multi-candidate rule
against *that*, not against the committed `own_triangle_park_walk.npy`. **I never checked that my
recomputation reproduces the published surface.** If it does not, claims 12-14 are measured against
a reconstruction and the numbers do not describe the product. Check it, and if it diverges, say by
how much and where.

**W2.** `shapely.STRtree.query(pts, predicate="dwithin", distance=...)` returns a 2-row array and
I assumed row 0 is the *input* index and row 1 the *tree* index. If that is the wrong way round,
every number in claims 12-15 is garbage. Verify it rather than trusting the docstring.

**W3.** The hole mask uses `np.roll`, which **wraps**. I zero the first and last row and column of
the ring to handle it. Convince yourself that is sufficient and that no interior cell is affected
by wrap-around, or show a case where it is.

**W4.** In `measure_access_candidates.py` the winning candidate's access distance (claim 13) is
recovered with `np.lexsort((cand_total, pi))` plus a `first` mask. That is fiddly index code and a
mistake there would make claim 13 — the claim that killed the recommendation — wrong.

**W5.** Claim 3 says the hatched set is identical across walk layers. I verified the *counts* were
identical at each threshold, which is weaker than identical *sets*. Check the sets.

**W6.** My first in-browser measurement of claim 4 was non-monotonic (57,237 at 5 min falling to
38,834 at 15) because I read the DOM before the recompute landed; I re-read with a settle loop and
got the monotone figures above. The settled numbers may still be wrong in some other way. They
also disagree slightly with the UTM-grid figures from `measure_unknown_hatch.py` (55,102 / 57,243 /
57,541) because one is the published WGS84 grid and the other the UTM source grid. Check that this
explanation is actually true and not a cover for a real discrepancy.

**W7.** Claim 11's second half — "subdividing an edge does not change shortest-path distances" — is
stated as self-evident. It is true for a plain shortest-path problem. Is it true for *this*
pipeline, where cells snap to edges and a per-edge access penalty and `symmetrise` are involved?
If adding a node would change a snap, the claim is wrong and the owner's suggestion has merit.

## Also in scope, from the commit before (`9cfa6c3`)

17. `NO_PATH` now ships for the first time: 57 cells per drive layer, 95 in the bike layer, on the
    UTM grid; 39 and 80 after reprojection. A note claimed in bold that `NO_PATH` was "unreachable
    in every shipped configuration"; I corrected it and logged ledger instance 53.
18. The seven-criterion bundle would have opened on a blank map (every manifest entry starts
    enabled); `default_on` / `default_threshold_min` were added, absent-safe.
19. The card named criteria by layer id (`own_triangle_duke-hospital_drive`) rather than the
    published label.
20. Publishing destination tables for park, school and coffee would add **137** Apache-licensed
    place records to the 41 already shipped, against a manifest that declares them not cleared for
    redistribution.

## What a useful review looks like

- **Run things.** A counterexample that executes beats an argument. If you can make a claim fail,
  give the command and its output.
- **Per claim: CONFIRMED, WRONG, or OVERSTATED**, with the evidence. "Overstated" is a real verdict
  and this project's ledger says I reach for it too rarely: in pass 48 four of five of my own
  entries were overstated, in pass 55 two of two.
- **Say what is right too.** A review that only lists faults cannot be weighed.
- Rank by **product risk retired**, not by defect severity. The plan's §0 orders work that way.
- If you think the *recommendation* (do nothing yet; test the connectivity hypothesis first) is
  wrong, say so and say what you would do instead.

Do not change code. This pass is a judgement on claims, and the owner has taken no option yet.
