# A rule that reads an OSM tag the extract drops is not conservative, it is dead

**2026-11-10.** Found while adding `surface` to `EXTRA_WAY_TAGS`, by writing the invariant down as
a test instead of by looking for the bug.

## Two instances of one failure, an hour apart

**`surface`.** The owner walked an audited journey and found 25 minutes against a published 13.5.
Two rounds of measurement then asked *which highway classes to delete* — `track`, `path`,
`footway`, `service` — and Codex pass 34 was right that this measures tag sensitivity rather than
usability. The reason the question came out that shape is mechanical: **highway class was the only
evidence the extracted graph held.** `surface` is the tag that would judge paving, 166,067 way tags
in the Triangle extract carry it, and osmnx was never told to keep it, so no rule could have used
it however the rule was written.

**`vehicle`.** `access.classify_access` consults OSM's access hierarchy narrowest-first,
`access` < `vehicle` < `motor_vehicle` < `motorcar`, and `_MODE_TAG_ORDER` lists `vehicle` for both
the drive and bike modes. `vehicle` was never in `EXTRA_WAY_TAGS` and is not in osmnx's default
`useful_tags_way` either, so **that branch has never fired on any layer this project has built.**
102 ways in the Triangle extract carry it, 92 of them `vehicle=no`. The walk layer is unaffected —
walk consults `foot` alone — so this does not touch the walked finding; it is a defect in the drive
and bike layers, and the correction runs in the strict direction: ways you may not legally drive
stop being free to drive down.

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
