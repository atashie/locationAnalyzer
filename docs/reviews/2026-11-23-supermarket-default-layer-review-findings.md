---
title: "Review findings: the supermarket default layer, and a building dataset with holes in it"
date: 2026-11-23
reviewer: Codex (gpt-6.1-sol)
status: findings recorded before any repair
---

# What the review found

Prompt: `2026-11-23-supermarket-default-layer-review-prompt.md`. Codex reviewed five commits
read-only and could not run Python, so every checkable claim was reproduced here before being
credited. All of the ones below reproduced. Recorded before any repair, per the standing rule.

Two findings change what the owner was told. One is a defect in code written the same day. One
reaches a long way past the thing being reviewed.

---

## 1. Ticking "Any grocery shop" cannot broaden the map. CONFIRMED, and it undoes how ask 13(a) was described

Ask 13(a) was put to the owner, and answered, as *the 262 weekly shops by default, **everything
else switchable on***. The report after implementing it said the smaller shops "stay one click
away".

**They do not.** Criteria are INTERSECTED, not unioned. `worker.js` folds every enabled layer's
per-cell outcome into `anyFail`, and `if (anyFail)` excludes the cell:

```
482:          if (o === O_FAIL) anyFail = 1;
485:        if (anyFail) {
```

The checkboxes are independent (`app.js` builds one per layer), so ticking *Any grocery shop*
leaves *Supermarket* ticked and the cell is excluded if the supermarket criterion fails. Adding the
broader criterion can only narrow the result or leave it unchanged. **It can never broaden it.**

To see the broader answer a household must UNTICK *Supermarket* and TICK *Any grocery shop*. That
is a switch-over, not a switch-on, and nothing on the screen says so.

So the published layer does contain all 553 shops, and the claim that the default view can be
widened by adding a criterion is false. The data is available; the interaction described to the
owner is not. **This is the owner's to decide** and is raised as an ask rather than repaired: the
options are a scope CHOICE (*Supermarkets* against *Any grocery*, one or the other) or having the
broader criterion replace the narrower one when selected.

## 2. Half the `REFUTED` footprint verdicts are missing building data, not empty ground. CONFIRMED, and it is the furthest-reaching finding here

Codex noticed that `grocery-name-recovery.csv` already recorded **no qualifying building** for the
three records I proposed to corroborate with host buildings, and that this challenged the plan.
It does. Measuring the nearest building of ANY size — not just the 650 m² weekly-shop floor —
shows why:

| record | nearest building of any size | buildings within 500 m |
|---|---:|---:|
| `Publix Super Market at Middle Creek Crossings` | **10,606 m** | **0** |
| `Walmart Supercenter`, Clayton | **2,857 m** | **0** |
| `Publix Super Market at Buffaloe Bend` | 203 m (32 m²) | 38 |

A Walmart Supercenter is a building of roughly 20,000 m². Our data has **nothing within 2.8 km of
it**. The sheet nevertheless recorded, for all three:

> *"named for Publix, but the largest building within 120 m is 0 m2, under the 650 m2 floor. No
> supermarket stands here, whatever this record calls itself"*

That sentence asserts absence from missing data. OSM maps a `shop=supermarket` named
*Walmart Supercenter* **6.6 m** from that point, and Walmart's own locator lists the store.

**It contaminates the triage of the 76 published uncorroborated records**, reported to the owner on
2026-11-22 as 23 CORROBORATED / 23 NEIGHBOUR / 30 REFUTED:

* **15 of those 30 `REFUTED` records have no building of any size within 500 m.** Half the verdicts
  in that column mean *we hold no building data here*.
* They are all at the edge of the metro — Mebane, Moncure, Graham, Haw River, Fuquay-Varina,
  Willow Spring, Clayton, Timberlake, Zebulon, Wake Forest, Youngsville, Rougemont.
* 13 of the 15 answer **0 cells**, so published numbers barely move. The two that do are
  `ABC Meats` (2,897 cells) and `KismetCrackers` (499).

`footprint.py` states its asymmetry carefully and the project has twice written down that `REFUTED`
means *not a supermarket* rather than *no shop here*. Neither is enough, because both readings
assume the building data is PRESENT. A third state is needed: *no building data here*, which
supports no conclusion in either direction. This is the ledger's own shape for the fourth time:
**an absence in our data read as a fact about the world.**

## 3. A failed export has already overwritten the published bundle. CONFIRMED, and it is mine, from today

`export_published_layers.py` writes the planes (line 695), the licence bundle (799) and the
manifest (843), and only then checks for undeclared files (855). So the refusal added today fires
*after* the served bundle has been replaced: the export reports failure and the publication has
changed anyway.

Codex's exact state: a bundle holding `left_behind.value.bin`, otherwise valid inputs. `main()`
rewrites everything, then raises. The four new tests exercise `undeclared_files` and not the
refusal's placement, which is why they pass while this is broken.

The check must run before anything is written, or the build must go to a staging directory and be
promoted.

## 4. The coverage table was reported as losses when it is a net, and as lost answers when it is a failed threshold. CONFIRMED in mechanism, small in size

Codex: the model selects minimum **cost** and reports that route's **time**, so a supermarket pass
need not be a subset of a grocery pass, and a net difference is not a count of losses. Measured:

| threshold | grocery | supermarket | **gross lost** | **gained** | net |
|---|---:|---:|---:|---:|---:|
| 10 min | 80,613 | 42,236 | 38,381 | 4 | −38,377 |
| 15 min | 165,866 | 102,651 | 63,254 | 39 | −63,215 |
| **20 min** | 243,908 | 176,983 | **66,929** | **4** | −66,925 |
| 25 min | 301,616 | 245,651 | 55,966 | 1 | −55,965 |
| 45 min | 428,566 | 401,711 | 26,855 | 0 | −26,855 |
| any answer (120-min horizon) | 498,981 | 492,149 | 6,832 | 0 | −6,832 |

The mechanism is real and the quantity is four buildings at the threshold that matters. The
reported figure stands; the right number to quote is the gross 66,929.

**The wording was wrong in a way that matters more than the four.** At a threshold a building
**fails the threshold**; it does not lose its answer. Only the 6,832 at the 120-minute horizon lose
an answer at all. Saying "66,925 buildings lose their answer" overstates what happened to them: a
building that goes from 19 to 21 minutes still has a perfectly good answer.

Two further limits Codex is right to insist on, and which the report did not carry:

* These are **source-grid** counts, binned before the exporter reprojects and crops.
  `measure_export_regrid.py` already documents that the exported and browser lookups differ, so
  these are not exactly what a household meets.
* The denominator is **512,633 structures**, and Overture carries no residential flag here, so a
  shed and a tower block count alike. The figure is a diagnostic. It cannot be restated as
  households.
* "The default layer is 100% classified `supermarket`" is **circular** — it follows from the
  class filter. It is a description of the selector, not independent validation. Likewise the zero
  overlap with the 76-record residue is weak evidence, because that screen sets recognised chains
  aside by construction.

## 5. The flag writer stamps a fingerprint it has not verified. CONFIRMED by inspection, pre-existing

`flag_restricted_routes.py` fingerprints whatever stored surface sits at the stem, without checking
that its own recomputation matches that surface. The destination writer does make that check
(`compare` against the stored seconds). So a flag computed against a different graph state can be
stamped with the stored surface's fingerprint, and the exporter's fingerprint check then has
nothing to catch. Predates today's commits; today's parameterisation makes it easier to reach.

## 6. The ask-14 guard skips on a clean checkout. CONFIRMED

`test_no_published_grocery_record_is_one_our_own_classifier_refuses` is
`skipif(not ACCEPTED_PLACES_PARQUET.exists())`, and that parquet is gitignored. A green suite on a
fresh clone therefore does not establish that the guard ran. The guard is sound where the data is
present — Codex confirmed it is reachable, and that `grocery` having no class filter is what makes
a newly refused brand reach the assertion.

## 7. What Codex examined and found sound

* **The inclusion ordering** (`(taxonomy OR admission) AND class`, then exclusions) implements the
  stated distinction correctly, and moving the admission earlier does not change `grocery`, which
  has no class filter. The 555 → 553 move belongs to ask 14, not to the reordering.
* **`symmetrise_for_mode`** preserves walk behaviour, leaves drive and bike directed, and rejects
  unknown modes. No live non-walk misuse among the remaining callers. Codex notes the phrase "all
  remaining callers are walk-mode" is imprecise — some support drive and bike safely — and that
  migrating them is not needed to fix a current defect.
* **The footprint reasoning in both new ask-14 exclusion entries.** Neither uses a building's
  presence as evidence that the record is a shop, nor as support for the removal.
* **The declared set in the exporter is complete** for everything the exporter writes. The
  suspected gap was not real; the sequencing was.
* **The module globals** are consistent within one CLI invocation, and no ordinary serial path
  writes a drive destination plane under a walk stem. Codex found one re-entry wrinkle: calling
  `main(["--mode", "drive"])` changes the defaults a later `main([])` reads, which matters only if
  repeated in-process invocation is ever supported.

## What changes as a result

Repairs, in order of what they protect:

1. The exporter must check for undeclared files **before** it writes. Finding 3, and it blocks the
   republish.
2. `footprint.py` needs a verdict for *no building data here*, and the two sheets that recorded
   "no supermarket stands here" from missing data need correcting. Finding 2.
3. The coverage figures are restated as gross, as threshold failures rather than lost answers, and
   with the source-grid and building-denominator limits attached. Finding 4.

Owner asks, because they are decisions and not repairs:

* **The intersection behaviour** (finding 1) — a scope choice, or the broader criterion replacing
  the narrower.
* **The three admitted chain stores** — the plan to corroborate them with host buildings is dead;
  finding 2 shows there is no building data at two of the three sites. Each already carries OSM and
  own-locator evidence in its inclusion reason. Codex's recommendation, which is better than the
  original plan: record the classification by id against that existing evidence, and keep it in a
  CURATED table rather than `NAME_CONFIRMED_SUPERMARKETS`, which `recover_brandless_by_name.py`
  regenerates and would erase.
