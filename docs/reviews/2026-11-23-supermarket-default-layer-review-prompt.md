---
title: "Adversarial review prompt: the supermarket default layer, asks 13(a), 14 and 16"
date: 2026-11-23
reviewer: Codex (gpt-6.1-sol)
status: prompt committed before the review was launched
---

# What to attack

Five commits on `v2-rethink`, 2026-11-23, implementing four owner decisions. Review them
adversarially. I am looking for defects, not approval. Where you can, name the exact input that
would produce the wrong output.

```
5152cd0  fix(v2): ask 13(a) would have dropped all 23 owner admissions from the default layer
053dc97  feat(v2): ask 14 -- the two records our own classifier refused are out of the layer
aed88c8  feat(v2): the destination writer can target a layer, and the one-way rule gets a home
890856c  feat(v2): the restricted-route flag writer can target a layer too
bd87cc2  feat(v2): ask 13(a) in the exporter, and it stops leaving files behind
```

## The decisions being implemented

The owner answered on 2026-11-23:

* **13(a)** -- the layer a household is served by default becomes `supermarket` (*"a supermarket
  you could do a weekly shop at"*, their definition of 2026-11-17), with the broader `grocery` set
  switchable on rather than deleted.
* **14** -- remove the two published records our own `classify_grocery` calls `not_a_grocery`.
* **15** -- remove the clear non-shops, per record with evidence, explicitly NOT touching any
  tienda, tortilleria or ethnic market. **NOT YET IMPLEMENTED**, so it is out of scope here except
  where the groundwork is wrong.
* **16** -- rebuild the published drive layer and give it the destination plane it has never had.
  Surfaces are rebuilt but the bundle is not re-exported at these commits.

## Standing constraints you should hold me to

* **2026-11-18, narrowed not reversed:** *"still refused: parsing a name to guess what KIND of
  shop something is; now allowed: looking a name up in the SAME EXPLICIT TABLE the brand is looked
  up in."* Adding a chain stays a decision, never a side effect of a name.
* Decision 17: nothing contractually restricted (Google place ids, RentCast, MLS/IDX, portals) may
  enter an ODbL-published artifact.
* Trust order: experimental results > research > priors.

## Specific things I think might be wrong

1. **The inclusion ordering.** `select_overture` now admits owner inclusions BEFORE the
   `grocery_classes` filter rather than OR-ing them in after it, and `supermarket` and
   `specialty_grocery` inherit `grocery`'s inclusions via a new `inclusions_from` key. Result:
   `supermarket` 242 -> 262. The alternative was to let an inclusion bypass the class filter,
   giving 265. I chose 262 on the grounds that an admission answers *is this a grocery* and not
   *is this a weekly shop*. **Is that the right reading, and does the new order break any other
   category?** `grocery` has no class filter, so I claim it is unaffected at 553 -- check that.

2. **Three owner admissions still do not reach the default layer**: two Publix and one Walmart
   Supercenter, all with an EMPTY Overture `brand` field and a name carrying a chain that IS in
   `SUPERMARKET_BRANDS`. A supermarket layer missing two Publix stores is indefensible. My plan is
   `NAME_CONFIRMED_SUPERMARKETS` entries with host-building evidence, as an owner ask. **Is there
   a defect in leaving them out meanwhile, and is the name-table route consistent with the
   2026-11-18 narrowing?**

3. **Ask 14 as a guard, not a filter.** I did NOT give `grocery` a class filter that would drop
   `not_a_grocery`, because the next brand added to `NOT_A_GROCERY_BRANDS` would then silently
   remove published records. Instead two explicit id exclusions plus a test that fails if a third
   contradiction appears. **Is the guard reachable, and does it actually bite?** Also: both
   removals sit inside buildings, so `corroboration` returns CORROBORATED for each, and I wrote
   into both reasons that this means *a building is here* and NOT *a shop is here*. **Check I have
   not smuggled the footprint in as support in either direction.**

4. **`symmetrise_for_mode`.** `symmetrise` adds a reverse edge to every one-way road and is valid
   only for walking. The rule lived in comments at 26 call sites in three spellings, two of them
   unconditional. I added one function, used it at the two sites I was already changing, and left
   the other 25 alone. **Is leaving 25 call sites on the old pattern the wrong call? Is there a
   live defect among them I have missed -- any script whose MODE is not "walk"?**

5. **Module-global mutation.** `persist_selected_destination.py` and `flag_restricted_routes.py`
   now set `MODE`, `CATEGORY` and `STEM` as globals from argparse inside `main`. Ugly. **Can it
   produce a wrong artifact -- for instance a destination plane written beside the wrong surface
   -- rather than merely being ugly?** Note both scripts check the surface exists before the graph
   build, and derive the stem from one `layer_stem()` expression.

6. **The exporter's new refusal.** `undeclared_files` lists files in the bundle directory the
   manifest does not declare, and the export refuses unless `--allow-undeclared`. It currently
   catches two real orphans from 2026-11-13. **Is the declared set complete?** I build it from
   `manifest.json`, the licence bundle's `files`, and each entry's `value_file`, `status_file`,
   `dest_file`, `dest_table` and `flag_file`. If the exporter writes anything else, the refusal
   fires on a legitimate file and blocks every future publish.

7. **THE MEASUREMENT, and this is the one I most want attacked.** The cost of 13(a), by buildings:

   | threshold | any grocery | supermarket | difference |
   |---|---:|---:|---:|
   | 10 min | 80,613 | 42,236 | -38,377 |
   | 15 min | 165,866 | 102,651 | -63,215 |
   | **20 min (the opening value)** | **243,908** | **176,983** | **-66,925** |
   | 25 min | 301,616 | 245,651 | -55,965 |
   | 45 min | 428,566 | 401,711 | -26,855 |
   | any answer at all | 498,981 | 492,149 | -6,832 |

   I first read the last row (-1.3 points) as "a cheap trade" and was wrong: at the threshold the
   layer actually opens on, 27% of the buildings that have an answer today lose it. **Is the
   20-minute row the honest one to lead with? Is the building denominator defensible given
   Overture carries no residential flag here, so a shed and a tower block count the same? Is there
   a reading of these numbers that would change the recommendation?** Destination counts: 262
   against 553, and the default layer is 100% classified `supermarket` with zero of the 76
   uncorroborated records in it.

## How to answer

Per finding: what is wrong, the exact input or state that shows it, how certain you are, and what
you would do instead. Rank by what would most change a published number a household sees. Say so
plainly if a thing I flagged is fine -- I would rather have a short list I can act on than a long
one I have to triage.
