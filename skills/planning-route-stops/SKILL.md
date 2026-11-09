---
name: planning-route-stops
description: Use when recommending where to stop, stay, or spend time along a journey between two points on given dates - overnight stops, layovers, charging or meal stops, multi-day halts - especially when options are compared on drive time, detour cost, arrival time or opening hours.
---

# Planning route stops

## Overview

A route recommendation is **a set of options, a table of numbers, and a set of claims**.
Finding good places and spotting constraints is already a strength — baseline testing showed
agents doing it well unprompted. Three things fail reproducibly:

- **Shape** (rule 1) — the work collapses into one recommendation and a defence of it, when the
  question had no single answer.
- **Bookkeeping** (rules 2–7) — numbers from different instruments compared as if alike, derived
  figures left stale when a route changes, caveats that evaporate before the final page,
  an arrival time printed beside an opening time without being compared.
- **Arithmetic** (rule 8) — the figures you computed yourself, carrying correct provenance
  labels and wrong values. On this project that was the *largest* source of false statements,
  and the last one anybody looked for.

This skill is those three. It does not teach travel knowledge.

## The eight rules

### 1. The traveller weighs; you measure

Detour minutes, ticket cost, opening hours, how much of the day the party wants to be outdoors,
what hour they will tolerate arriving — these trade against each other, and **the weights belong
to the traveller**. Measuring the trade is the work. Choosing among them is not.

Ship **two to four itineraries that differ in kind**, each measured end to end, and make
switching between them cheap.

> Worked example — the failure this rule exists to stop. A one-day family drive produced one
> plan, an "alternatives" table framed as swaps against it, and two options struck out as
> "over budget" in red. The tell sat upstream of the page: the script that *measured* the
> itineraries named one of them `"RECOMMENDED:"` on line 29, before a word of comparison had
> been written. Once the verdict is in the measuring code, every later number arranges itself
> behind it, and honest-looking status labels end up decorating a conclusion the reader never
> got to make.

Four specific traps:

- **Naming a winner before the comparison exists.** Label variants by what distinguishes them
  (`fewest-stops`, `most-outdoors`, `cheapest`), never by rank. If your script says
  `RECOMMENDED`, you have stopped comparing.
- **An options table whose last column argues against the options.** "Why / why not" is a list
  of reasons to reject. Give each option the column that lets someone *pick* it: what it costs,
  what it buys, who it suits.
- **Hardening a soft budget.** "Maybe an hour of extra driving" is a preference, not a
  constraint. Price the option that exceeds it and say by how much; do not strike it out. A
  family may happily spend 1h26 on the thing the kids will still be talking about. Treat a
  figure as hard only where the traveller said it was, or where it is physically binding — last
  entry, a ferry, sunset.
- **Options that differ by one swapped stop.** Six variations on one plan are not a choice.
  Options differ *in kind*: fewest stops, most time outdoors, cheapest, earliest arrival, one
  big destination versus several small ones — and, where the geography allows it, **a different
  road entirely** (rule 6). Seven options that are all the same corridor plus excursions is one
  option with seven footnotes.

A single recommendation is right only when the traveller asked which one to take, or when the
measurements genuinely collapse the field — and then say *that*, showing the numbers that
collapsed it.

### 2. One instrument per comparison, and provenance down to the number

Measure every leg with the same engine. Two engines in one table produced an **hour-wide
disagreement** on a single leg, presented as comparable.

If a figure appears in a table it was **measured**, or it is **marked as an estimate**. A
four-row table of drive times accurate to the minute, with one leg sourced, is the
characteristic failure: *precision without provenance*.

**Every recommendation carries a link to the operator's own page — in the final output, not
just the research notes.** A status label is not a substitute for a source.

Testing caught this skill displacing exactly that. Two runs under an earlier draft shipped
**0 and 5 outbound links**, where the *unaided* baseline had cited about 16 operator pages;
adding the sentence above took the next run to **55 links across 41 hosts**. One post-fix run, so
treat it as a signal rather than a proven effect — but the mechanism is not subtle: the
verification-status rule gave the model a way to *sound* careful, and it stopped doing the thing
that made it careful. **Status says how sure you are; the link says why. Ship both.**

Keep **corridor experiments separate from stop itineraries** (rule 6 measures both). A route
forced through three cities cost +1:55; stopping in the middle city cost +1:22. Quoting one as
the other shipped.

### 3. Change a leg, recompute the whole row

Detour, share-of-trip and arrival time are all **derived** from the legs. Change a route
variant and every one of them moves.

> Worked example: a Sunday leg was revised 4:04 → 4:19 to avoid a motorway. Detour stayed
> "+41 min" and share stayed "55%". Correct values: **+56 min and 53%** — which moved the stop
> outside the traveller's stated detour budget. Nobody noticed for two revisions.

Several options multiply this: **N options means N full recomputations**, and a detour
**cannot in general be obtained by summing its stops' individual detours**. In one run the
per-stop detours summed to +43 min while the routed itinerary measured **+51**. The two can
coincide — independent dead-end spurs off an otherwise unchanged route sum exactly — but shared
access makes the combined detour smaller and routing interactions or a different stop order make
it larger, and you cannot tell which case you are in without routing it. Route each option as a
single multi-point request and read the total off that.

### 4. Verification status travels all the way to the output

Three states. Never collapse them:

| Status | Means |
|---|---|
| **Confirmed for the date** | Checked against the operator for *that* date |
| **Standing hours** | Published routine; the specific date not checked |
| **Could not determine** | Looked, failed. Say so. |

These three are for **external facts** — what a venue or operator does. Values you compute
carry a different label: *measured* (routed or read directly), *derived* (calculated from
measured values plus an assumption — say which), or *calculated* (from a model). Do not force
a drive time into "standing hours".

A caveat recorded in research notes must survive into the summary. In one project **four**
were lost on the way to the published page — derived season dates presented as published, an
unconfirmed attraction listed flatly, a verified exception contradicted, and a hedged source
hardened into an absolute.

Status labels belong to the stop, not to the view. A stop that appears in three options carries
its label in all three.

**An absence of data is not a negative finding.** "Could not determine" must never be rendered,
rolled up or summarised as a definite claim about the world. A rollup that collapsed *unknown*
hours into "nothing-open" printed "nothing here is open when you arrive" about a venue whose
hours nobody had published — a flat falsehood, carrying a correct provenance label.

### 5. Reconcile the arrival against the hours, in code

Publishing an arrival time and an opening time side by side is not the same as comparing them.
**Compute it.** For every stop in every option, check the derived arrival against the published
hours and carry the verdict — open on arrival / opens during the halt / shut / closed that
weekday / hours unknown — into the output.

> Worked example. A plan shipped with the same stop first in **all five** options, arriving
> 06:53, against hours of 11:00. The page even printed both numbers in adjacent columns. The
> user caught it: *"I'm confused as to the suggestion to stop at South of the Border, as it opens
> at 11:00 am but you suggest we arrive before 7:00 am."* Adding the computed check then caught a
> **second** collision nobody had noticed — a lunch stop reached at 10:29 that opens at 11:00,
> a half-hour wait sitting in two options.

Four things make this harder than it looks:

- **Last entry is not closing time.** A zoo open until 17:00 with last entry 15:30 is shut
  to a 16:00 arrival while still open to everyone inside. Model them separately or the
  verdict is wrong for exactly the arrivals that matter.
- **Open on arrival is not the same as worth stopping for.** A 16:45 arrival at a 17:00
  close is "open" and gives you fifteen minutes of a seventy-five-minute halt. Carry
  *usable minutes*, not just the verdict.
- **Clocks are local to the stop, not to the traveller.** Hours belong to the venue's time
  zone; a corridor crossing one shifts every verdict by an hour if you check against the
  origin's clock. The same applies past midnight: the weekday has to advance with the
  accumulated time, or a 01:00 arrival is checked against yesterday.
- **A stop is not one thing with one schedule.** One roadside stop had *seven* facilities on
  five different schedules: pumps open 24 h, restrooms from 07:00, shops from 08:00, an
  observation tower from 11:00, and the best attraction closed Tuesday–Thursday. Model
  facilities, not stops — otherwise "closed" and "open" are both wrong.
- **"Nothing is open" is a finding, not a disqualification.** Say what *is* reachable at that
  hour: a 24 h pump, an outdoor space with no hours, a view at first light. The stop above
  survived on exactly that — and the restrooms opened six minutes into the halt, which only the
  computed check revealed.

Where the arrival lands outside the hours, the fix is to move the stop, change the departure
hour, or say plainly what the stop is for. Never to leave the collision for the reader to spot.

### 6. Sweep alternative corridors, then off-corridor stops

Two sweeps, in this order. Skipping the first is the deeper miss, because it silently fixes
which stops are even candidates.

**The corridors.** Measure each plausible long-distance route *bare* — no stops, forced through
its defining cities — before shortlisting anything. On one 540-mile drive: coastal 8h41 (the
direct route), fall line +40 min, Atlanta +1h00, Jacksonville +1h08. Only then do you know what
a corridor costs as a corridor.

> Worked example — the failure this half exists to stop. A comparison shipped with seven
> options that were all the same road plus small excursions. The corridor alternatives *had*
> been measured and were then dismissed in prose — "the stops over there are thinner" — which
> was an assertion, never a measurement. The traveller pushed back. Measured properly, the fall
> line carried a major zoo and a free national monument for **the same +52 min** as the best
> coastal option.

**Then the stops, per corridor.** A stop's detour is meaningless without naming the corridor it
is measured against. The same zoo was **+46 min** off the coastal line and essentially **free**
on the fall line. A shortlist scored against one corridor is not a shortlist for another.

A dead-end spur costs its detour **twice**. Route to it and back before judging: one national
park looked tempting on both corridors and measured **+2h45** either way.

**Check what road each option actually uses.** Naming a corridor from the cities you picked is
guesswork. Reading `maneuvers[].street_names` caught an option labelled "piedmont via Atlanta"
that the router had sent down I-77 and I-20 instead — the same corridor as the fall line, 6
miles apart. A genuine Atlanta route needed Atlanta itself as a waypoint.

**Corridor choice can set the departure time.** One corridor's first stop was a 24-hour fuel
station beside an hours-free outdoor curiosity, which rewards a 04:45 start; the others opened
at 09:00, so the same early start just means waiting in a car park. Those options had to leave
33 and 120 minutes later, and every minute landed on the far end after sunset. Give each option
its own departure hour or the comparison is rigged toward whichever corridor suits the one you
picked.

### 7. Publish what you could not verify

A short "not verified" list, plus the calls worth making. Booking engines return 403/429 to
automation: "no live rate was obtainable" is the honest result, not a reason to substitute a
stale headline price.

When no stop was checked against the date, **say so in one sentence** rather than letting a page
of "standing hours" labels imply otherwise.

### 8. Check your own arithmetic the way you check a venue's hours

Rules 2 and 4 govern facts you got from the world: where they came from, how sure you are.
Nothing in them touches the figures **you computed yourself**, and those turned out to be
the larger source of false statements.

> Worked example. Two adversarial reviews of this skill's own tooling returned **20
> findings**. Twelve had already reached a published page as confident statements: a venue
> whose hours were simply *unknown* rendered as "nothing here is open when you arrive"; a
> "the corridors are 185 miles apart" figure that became 223 if you reordered the list;
> a drive time quoted as 8h41 that was 8h42, because every duration truncated seconds
> instead of rounding; two 17-mile stretches of I-75 silently deleted from the map by a
> filter that mistook vertex count for importance. Provenance labels were correct on all
> of them. They were measured, by one instrument, and wrong.

None were hard to catch. **They were never looked for.** The checks that find this class
are cheap, and `selftest.py` now runs them — extend it rather than re-deriving them:

- **Round-trip anything you decode.** Encode a known polyline, decode it, compare.
- **Assert landmarks and bounds on anything projected.** Named places in the right
  quadrant, no point outside the viewBox.
- **Swap the arguments of anything that should be symmetric.** `sep(a,b)` versus
  `sep(b,a)` is how the order-dependent separation surfaced.
- **Test rounding at the boundaries**: ±30 s, exactly an hour, a small negative. A small
  negative once rendered as `-1h59`.
- **Feed the degenerate case**: zero epsilon, a two-point line, a venue open past
  midnight, a stop with no hours at all, a closed weekday.
- **Re-derive one published figure by hand** from the raw response, end to end.
- **Grep the generator for numeric literals.** Prose is not covered by a data pipeline.

Two rules of thumb that would have prevented most of them:

- **An absence of data is not a negative finding.** Unknown hours are not "closed"; an
  unpriced ticket is not "free". Every collapse of unknown into a definite claim on this
  project produced a confident falsehood.
- **Never filter on a proxy for the thing you care about.** Vertex count is not road
  importance — a straight interstate simplifies to two points. Filter on the quantity you
  actually mean, here visible length.

And the discipline that makes it stick: **a fix needs a failing test first**, exactly as a
skill does. Every case in `selftest.py` is a defect that shipped; each was reproduced
before it was fixed. A fix without a test beside it is a fix that comes back.

## The deliverable

A route comparison is **operated, not read**. Its job is letting someone flip between options
and see what changes — which is why terminal scrollback and a linear document both fail at it,
and why the usual "does this even need a page?" hesitation does not apply here. **Two or more
options means build the page.** A single-stop question, or one answered in a sentence, does not.

What the page owes the reader:

- **One control that switches everything.** A segmented control or radio row at the top,
  switching map, timeline and totals together. Not tabs below the fold; not one section per
  option stacked down the page.
- **A map that redraws per option** — to *orient*, not to compare. Draw every option at once,
  unselected de-emphasised and selected lifted, with markers on the selected option's stops.
  **Measure the separation before designing around it** — it decides what the map is for. Within
  one corridor, options nearly coincide: on one drive two were *geometrically identical* and the
  widest pairwise gap was 0.5°, so the map could only orient, and the legend had to say so. Add
  genuinely alternative corridors and the same measurement came back at **2.7° — about 185
  miles** — and the map became the clearest thing on the page. Same test, opposite conclusion;
  run it, don't assume either way.
- **Something that carries the comparison the map cannot.** When the routes coincide, what
  differs is how the day is carved up. One **leg-rhythm strip** per option — all on a shared time
  axis, driving in one tone and stopped in another, labelled with arrival and *longest single
  leg* — shows the actual trade in a glance: fewer halts buys an earlier arrival and costs a
  longer stretch in the car. That longest-leg number is what decides whether a plan survives a
  small child.
- **All options' totals visible at once.** A compact row of drive time / added time / cost /
  arrival, every option side by side, so switching is not the only way to compare.
- **Per-facility hours verdicts in every view.** Each stop lists what is open on arrival, what
  opens during the halt, and what is shut, computed not eyeballed. When a stop is shut on
  arrival, that belongs next to the stop, not in a note further down the page.
- **Per-stop links and status labels in every view.** Rules 2, 4 and 5 do not relax inside a tab.
- **Soft figures shown as soft.** An option over the traveller's rough budget is annotated with
  the overage, in the same type as everything else. No strike-through, no red, no "rejected".
- **Suggestive copy.** "Fewest stops, earliest arrival" beats "Recommended". Describe what an
  option *is*, and let the reader conclude.

**Updating a page you published before** — republish to its existing URL rather than making a
second one, and record that URL beside the trip's inputs so a later session can find it. The
example's README keeps its own. Everything needed to rebuild a published page must be committed
too: the spec and the generator for one real trip lived only in a session temp directory, one
cleanup away from being unrecoverable.

### Map mechanics

**Every map carries a basemap** — political boundaries, major roads, place labels. A route drawn
on blank ground is unfalsifiable: nobody can tell a correct line from one decoded at the wrong
polyline precision or projected with a sign error. The basemap is the reader's version of the
numerical assertion you should already be making. `basemap.py` builds one from keyless sources
(US Census TIGERweb for boundaries, OSM via Overpass for motorways) and writes bakeable JSON.

Three traps it exists to handle:

- **Stitch OSM road fragments before simplifying.** OSM splits a motorway at every junction and
  carries each carriageway separately: one `ref` query returned **8473 two-point fragments**,
  which RDP cannot reduce at all. Chaining them on rounded endpoints first turned 8473
  fragments into 118 chains, 73.5k points into 673, and the baked file from 389 KB to 22 KB.
  `endpoint-notes.md` already warned about this and the first attempt did it wrong anyway.
- **Clip into runs, never by dropping points.** Dropping off-view vertices draws a false
  straight line across the map. Split into runs, each with one lead-in and lead-out point — and
  stroke those open runs rather than filling them, or a clipped ring renders as a blob.
- **Pad the projection window** past the routes' own extent (0.45° worked), or the basemap is
  clipped flush to the outermost route and provides no context at all.

**Traffic cannot be baked, and usually should not be claimed.** There is no keyless traffic
source these tools reach, and a page cannot call one at view time. More to the point, for a trip
weeks out live traffic is a fact about *now*, not about the travel date — a layer drawn today is
decoration. Say so, and keep the free-flow caveat instead.

Four more things that silently ruin a baked map. `comparison-page.md` has the working code for
all of it, plus the projection, the rhythm strips and the copy rules.

- Artifact pages block external fetches, so **tiles never load and Leaflet renders blank**. Bake
  the geometry in and draw inline SVG.
- **Emit finished `<path d="M…">` markup, not coordinates plus in-page projection code.** A test
  run obeyed "bake the geometry in" by embedding 324 lat/lon pairs and building the paths at
  runtime with `createElementNS` — leaving `<svg>` *empty in the markup*, so the map is blank in
  the first frame, the thumbnail and any screenshot. Project in the generator; the page should
  contain no geometry logic at all.
- Valhalla's `trip.legs[].shape` is an encoded polyline at **precision 6**, not the usual 5.
  Decoding at 5 puts the route in roughly the wrong hemisphere — and on blank ground that looks
  like a plausible map.
- Simplify with **iterative** Ramer–Douglas–Peucker; recursion blows the stack on long routes.
- **Verify the projection numerically, not by eye.** `file://` URLs cannot be screenshotted by
  the browser extension, and arithmetic is the better check anyway: assert that known landmarks
  land in the right relative positions and that no point escapes the viewBox.

`itinerary_compare.py` emits measured legs per option plus simplified, ready-to-bake geometry.
**Generate the page from its JSON rather than hand-writing it** — that is rule 3 enforced by
construction **for every value the generator actually derives**. It does nothing for prose: one
generator held 14 numeric literals in its own sentences, and a second review found four more
after the first sweep. Derive the numbers in the copy too, and grep the generator for stray
digits before publishing.

## Scale the effort, never the honesty

Match the work to the question, and let each piece be earned separately:

- **Always:** measure the candidates, measure each option end to end, and apply the eight rules.
- **Commission per-region research** only when the deciding facts are local and unknown
  (opening hours on a date, a seasonal programme), not merely because there are several stops.
- **Skip the page** for a single-stop question, or one answered in a sentence.

A concise question deserves a concise answer. **The most likely way this skill makes work
worse is ceremony:** exhaustive status labelling and regional research consuming the attention
that a single decisive calculation or citation needed. If you are labelling more than you are
checking, stop labelling.

The previous draft of this skill had five rules, every one about being right about numbers, and
a line discouraging a page — and its output shape duly defaulted to a verdict. **Rules
redistribute attention; whatever they do not mention gets the leftovers.**

## Tools

- `itinerary_compare.py` — several named itineraries → measured legs, detour vs direct, derived
  arrival clocks, per-facility opening-hours verdicts (with last-entry and usable minutes), and
  simplified geometry for the map, all from one engine. Options may each carry their own
  `depart_h`, which is what makes comparing corridors fair; stops may carry their own
  `utc_offset`. Validates the whole spec before spending a request, and caches routing responses
  on coordinates and costing so editing a dwell time or an opening hour costs nothing. `--help`
  for usage.
- `corridor_scan.py` — candidates → detour, share, arrival vs sunset, in one instrument. Use it
  to shortlist stops, then `itinerary_compare.py` to assemble options from them.
- `research-brief.md` — the per-region brief that forces the three-state status back out.
- `selftest.py` — 42 invariants for the measuring tools, no network, no fixtures, one second.
  Run it after touching either, and add a case whenever you fix something: every case in it is
  a defect that shipped.
- `examples/chapel-hill-thomasville/` — a complete worked trip: the researched `spec.json`,
  the page generator, and enough measured output to rebuild the page with no network. Read it
  before building a new one; the spec format is easier to copy than to infer.
- `doccheck.py` — checks this prose against this code: files and flags that are named must
  exist, spec fields promised must be read, the rule count must match, and figures quoted about
  a worked example must match its JSON. It caught the docs still claiming a basemap of "636
  points" one commit after a fix made it 673.
- `basemap.py` — keyless basemap builder: Census state outlines + OSM motorways, stitched,
  clipped and simplified into `basemap.json` for baking into the page. Every map gets one.
- `endpoint-notes.md` — public-endpoint limits worth knowing before you hit them.
- `comparison-page.md` — the switcher-and-map page: structure, the bake-the-geometry pattern,
  and the copy rules that keep it suggestive.

## Red flags

**Shape**

- One plan called "recommended" before the alternatives were measured — especially inside the
  code that measures them
- An options table whose last column argues against the options
- An option struck out as "over budget" against a figure the traveller called approximate
- Options that differ by one swapped stop rather than in kind
- A route comparison with no map
- Leaflet, or any tile layer, in an artifact page
- A map with no basemap — route geometry floating on blank ground cannot be checked
- A traffic layer on a map for a date weeks away

**Numbers**

- An opening time compared against the wrong clock — the origin's rather than the stop's
- A venue's closing time used where its last entry is the binding constraint
- A time in a table you cannot name the source of
- A route variant changed, and the detour column untouched
- A detour quoted as the sum of its stops' individual detours
- A corridor alternative dismissed in prose rather than measured
- A stop's detour quoted without naming the corridor it was measured against
- A corridor named from the cities you chose rather than the roads the router returned
- Every option sharing one departure time when their first stops open hours apart
- An arrival time and an opening time printed side by side without being compared
- One set of hours attached to a site that has several facilities on different schedules
- Two engines, one table
- Every candidate on one road

**Claims**

- A computed figure published without one assertion behind it
- "Unknown" rendered as "closed", "unpriced" rendered as "free"
- A filter on a proxy (vertex count) for the property you mean (visible length)
- A fix with no failing test written before it
- A number in the prose that `doccheck.py` cannot trace to the code or the measurement
- "No mosquitoes" where the source said "generally not a problem"
- A recommendation with no "unverified" section
- **Status labels everywhere and almost no links** — the vocabulary has replaced the evidence
