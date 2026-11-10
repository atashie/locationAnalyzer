# A rule that reads an OSM tag the extract drops is not conservative, it is dead

**2026-11-10.** Found while adding `surface` to `EXTRA_WAY_TAGS`, by writing the invariant down as
a test instead of by looking for the bug.

## Two instances of one failure, an hour apart

**`surface`.** The owner walked an audited journey and found 25 minutes against a published 13.5.
Two rounds of measurement then asked *which highway classes to delete* — `track`, `path`,
`footway`, `service` — and Codex pass 34 was right that this measures tag sensitivity rather than
usability. The reason the question came out that shape is mechanical: **highway class was the only
evidence the extracted graph held.** `surface` is the tag that would judge paving, **165,549 ways**
in the Triangle extract carry it, and osmnx was never told to keep it, so no rule could have used
it however the rule was written.

**`vehicle`.** `access.classify_access` consults OSM's access hierarchy narrowest-first,
`access` < `vehicle` < `motor_vehicle` < `motorcar`, and `_MODE_TAG_ORDER` lists `vehicle` for both
the drive and bike modes. `vehicle` was never in `EXTRA_WAY_TAGS` and is not in osmnx's default
`useful_tags_way` either, so **that branch has never fired on any layer this project has built.**
**98 ways** in the Triangle XML carry it — 88 `no`, 8 `forestry`, 2 `yes` — which is **332
directed edges** in the simplified graph (278 `no`, 38 `yes`, 16 `forestry`), because one way
becomes several edges.

> **The first version of this note said 166,067 and 102 "way tags", and those are element-blind
> counts.** They came from `grep -c 'k="surface"'` over the XML, which counts the tag on nodes as
> well: 165,549 ways + 518 nodes = 166,067, and 98 ways + 4 nodes = 102. Codex pass 35 parsed the
> XML element-aware and I reproduced it. The 332 edge figure was right, and so was every measured
> consequence — nothing downstream was computed from the wrong number — but a count is a count *of*
> something and these were counts of the wrong thing. Same class of error as
> [[feedback-decide-by-measurement-not-by-argument]]'s 2026-11-10 entry, on the same day it was
> written.

Measured rather than assumed, with `scripts/measure_vehicle_tag_effect.py`:

| mode | edges changing class | on a highway the mode may use | which way |
|---|---|---|---|
| walk | **0** | 0 | walk consults `foot` alone |
| drive | 234 | **24** | **12 stricter, 12 more permissive** |
| bike | 28 | 28 | 14 more permissive, 14 stricter |

**I wrote "the correction runs in the strict direction" before measuring it, and that is wrong.**
Half of drive's usable changes are `forbidden -> restricted`: a way tagged `access=no` with
`vehicle=forestry` was being **removed outright** and now survives with a penalty, which *restores*
an edge the old rule deleted. The tag is a three-valued override in both directions, so honouring
it both removes and restores. The walk layer really is untouched, and that half of the claim held.

The shared shape: **the code's rules and the data's contents were two separate claims, and nothing
compared them.** Either half alone looks right. `classify_access` reads `vehicle` correctly. The
extract is a perfectly good extract. The bug lives only in the join.

## The second trap, which would have made the fix a no-op

`spikes/g1_own_graph_layer.load_graph` returned the 670 MB `roads.graphml` cache **whenever the file
existed**. A graphml file does not record which way tags were retained when the XML was parsed. So
adding `surface` to `EXTRA_WAY_TAGS` would have changed the profile digest, changed the code, passed
every test — and routed on the old graph, because the cache was still there. Every downstream
measurement would have agreed with every other one. Fifteen scripts load that cache.

Fixed by making reuse a *checked* claim rather than an assumed one: `write_graph_cache_manifest`
writes `roads.tags.json` beside the cache, `graph_cache_complaint` says why a cache cannot answer
for today's rules, and `load_roads_graph` refuses **before** reading the graph. Only
`g1_own_graph_layer.py` rebuilds it; everything else fails loudly. The rule is asymmetric on
purpose: a cache parsed with *more* tags than the rules need carries everything they ask for and is
usable; one missing a tag cannot answer for a rule that reads it, whether or not any rule reads it
yet.

### And the fix had the bug's own shape — revision 2, Codex pass 35 F1

The first manifest declared a tag set and **nothing said which graph it described**. Codex wrote a
valid pair, replaced only the graphml with a graph lacking `vehicle`, and `load_roads_graph`
accepted it, keeping a drive edge that `vehicle=no` should remove. That is the same defect one level
up: the bug was that the code's rules and the data's contents were two unconnected claims, and the
guard then made a third unconnected claim *about the data*. `g1` also wrote the graph and the
manifest separately, so an interrupted run left a pair that did not belong together.

Revision 2:

- the manifest records `graphml_bytes` and `graphml_sha256`, and **both are checked** before the
  graph is read — 0.5 s to hash 695 MB, against a 35 s load;
- `graph_declared_edge_attrs` reads the graphml's own `<key>` declarations, so the **writer** refuses
  to certify a graph that does not declare a tag `EXTRA_WAY_TAGS` adds deliberately. This consults
  the graph, not a claim about it. A graphml declares a key only if some element carries it, so a
  missing declaration cannot prove absence of intent — `landuse` is an osmnx default no highway way
  carries — which is why osmnx's defaults are recorded as provenance rather than required, and why
  only the parsing process may assert `requested_but_absent`;
- the required set now includes **osmnx's defaults**, not only our additions: removing the default
  retention of `oneway`, which orients every edge, survived the first invariant test;
- the `parse` options (`simplify`, `retain_all`) are recorded and checked;
- `g1` **deletes the manifest before writing the graph**, so an interrupted run leaves a graph with
  no manifest and the next run re-parses. The guard fails closed.

**What it still does not establish: parsing semantics.** A retained tag does not say how it was
interpreted, and the manifest records the parse options it knows rather than every osmnx setting in
effect. The claim is the narrow one: *the guard refuses an incompatible declared tag set, and a
graph whose bytes the manifest does not describe.*

And the tests needed the same treatment. Pass 35 killed three of them — rejecting a missing
`surface` while waving every other missing tag through; calling `load_graphml`, swallowing the
exception and then validating; loading a valid graph twice. All three are now caught, by
parameterising the missing-tag test over the whole required set and replacing a stub that raises
with a **call recorder** asserting the exact call list. `scripts/mutate_graph_cache_guard.py` then
found a twelfth mutation the twelve tests still missed — *ignore the graph's sha256* — because every
swap test changed the file's length and the size check caught them first. **12 of 12 caught.**

## The rule

**For every tag a rule consults, something must assert that extraction keeps it.** In
`v2/tests/test_graph_cache_manifest.py`:

```python
consulted = {k for keys in access._MODE_TAG_ORDER.values() for k in keys} | {"access", ...}
available = set(ox.settings.useful_tags_way) | set(speeds.EXTRA_WAY_TAGS)
assert consulted <= available
```

Derived from `_MODE_TAG_ORDER` rather than retyped, so adding a tier to the hierarchy without
adding it to the extract fails the test. It failed on `vehicle` the first time it ran, which is the
only reason that defect is in this note instead of still in the code.

**And a cache must record what it was built from.** The generalisation is not about graphml: an
artifact whose inputs are not written beside it cannot be invalidated, so a fix to those inputs is
indistinguishable from no fix at all. Same lesson as
[[project-phase1-s3-stale-walk-raster]], where the raster predated a `symmetrise` fix by eight
hours and nothing said so. Third instance in this project.

Related: [[feedback-verify-the-shape-of-the-risk]],
[[feedback-decide-by-measurement-not-by-argument]],
[[project-phase1-s3-soft-way-dependence]], [[project-phase1-s3-design]].
