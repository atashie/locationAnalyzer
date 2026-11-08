---
name: feedback-maps-need-a-basemap
description: "Every map this user is shown must carry a basemap - roads, political boundaries, place labels - because geometry floating on blank ground cannot be sanity-checked"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7b2884de-c576-4048-9933-aa7a65c6a0cf
  modified: 2026-11-06T22:40:09.318Z
---

Stated 2026-11-06, on a route-comparison artifact: **"all maps should have roads / traffic /
political boundaries basemaps."** Not a one-off request for that page — a standing expectation
for any map I produce.

**Why:** a route drawn on blank ground is unfalsifiable. The reader cannot tell a correct line
from one decoded at the wrong polyline precision, projected with a sign error, or simply routed
somewhere else. State lines and labelled interstates turn the map into something that can be
checked at a glance — which is the same reason I had already been asserting the projection
numerically. The basemap is the reader's version of that assertion.

**How to apply:** Artifact pages block every external fetch, so tiles can never load and
Leaflet renders blank — the basemap has to be **baked at build time**, not requested at view
time. What worked (`skills/planning-route-stops/basemap.py`):

- **State/political outlines** — US Census TIGERweb `State_County` MapServer, `f=geojson`,
  `geometryPrecision=3`. Keyless, fast, 3 MB for seven states.
- **Roads** — OSM via Overpass, `way["highway"="motorway"]["ref"~"^I 95$|..."]`. **Stitch the
  fragments before simplifying.** OSM splits a motorway at every junction and carries each
  carriageway separately: a ref query returned 8473 two-point fragments, which RDP cannot
  reduce at all. Chaining them on rounded endpoints first took 77k points to 636 and the baked
  file from 389 KB to 22 KB. My own endpoint-notes.md already warned about this and I did it
  wrong anyway.
- **Simplify hard.** 193k raw state points to 371 (0.19%) at eps 0.02 deg is invisible at a
  state-scale map. Budget the whole basemap at a couple of thousand points.
- **Clip into runs, never by dropping points** — dropping off-view vertices draws a false
  straight line across the map. Split into runs with one lead-in/lead-out point each.
- **Pad the projection window** beyond the routes' own extent (0.45 deg worked), or the basemap
  is clipped flush to the outermost route and provides no context.
- Open clipped runs must be stroked, **not filled** — a filled open polyline renders as a
  nonsense blob.

**Traffic specifically:** there is no keyless traffic source these tools reach, and a page
cannot call one at view time. More importantly, for a trip weeks away live traffic is a fact
about now, not about the travel date — any layer drawn today is decoration. Say that plainly
and keep the free-flow caveat instead of faking a layer. See
[[project-v2-rethink-decisions]], [[feedback-computable-property-is-not-the-claim]].
