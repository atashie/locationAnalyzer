---
name: planning-route-stops
description: Use when recommending where to stop, stay, or spend time along a journey between two points on given dates - overnight stops, layovers, charging or meal stops, multi-day halts - especially when options are compared on drive time, detour cost, arrival time or opening hours.
---

# Planning route stops

## Overview

A route recommendation is **a set of options, a table of numbers, and a set of claims**.
Finding good places and spotting constraints is already a strength — baseline testing showed
agents doing it well unprompted. Two things fail reproducibly:

- **Shape** — the work collapses into one recommendation and a defence of it, when the question
  had no single answer.
- **Bookkeeping** — numbers from different instruments compared as if alike, derived figures left
  stale when a route changes, caveats that evaporate before the final page.

This skill is those two. It does not teach travel knowledge.

## The six rules

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
  big destination versus several small ones.

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

Keep **corridor experiments separate from stop itineraries**. A route forced through three
cities cost +1:55; stopping in the middle city cost +1:22. Quoting one as the other shipped.

### 3. Change a leg, recompute the whole row

Detour, share-of-trip and arrival time are all **derived** from the legs. Change a route
variant and every one of them moves.

> Worked example: a Sunday leg was revised 4:04 → 4:19 to avoid a motorway. Detour stayed
> "+41 min" and share stayed "55%". Correct values: **+56 min and 53%** — which moved the stop
> outside the traveller's stated detour budget. Nobody noticed for two revisions.

Several options multiply this: **N options means N full recomputations**, and a detour is never
the sum of its stops' individual detours. In one run the per-stop detours summed to +43 min
while the routed itinerary measured **+51**. Route each option as a single multi-point request
and read the total off that.

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

### 5. Sweep off-corridor before you accept the corridor

Enumerate candidates **off** the obvious road and price each one's detour against the direct
route. Assuming the corridor is the most common structural miss: a baseline considered four
towns on one interstate and never priced a detour at all. In a real case the winning stop sat
**+49 minutes off the fastest line** — unreachable by corridor-only thinking.

A dead-end spur costs its detour **twice**. Route to it and back before judging.

### 6. Publish what you could not verify

A short "not verified" list, plus the calls worth making. Booking engines return 403/429 to
automation: "no live rate was obtainable" is the honest result, not a reason to substitute a
stale headline price.

When no stop was checked against the date, **say so in one sentence** rather than letting a page
of "standing hours" labels imply otherwise.

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
  But expect the routes to nearly coincide: options on one corridor use the same roads, and on a
  real five-option drive two were **geometrically identical** and the widest pairwise separation
  was 0.5°. Measure the separation before you design around it, and when it is small, say so in
  the legend rather than letting five overlapping lines imply a divergence that is not there.
- **Something that carries the comparison the map cannot.** When the routes coincide, what
  differs is how the day is carved up. One **leg-rhythm strip** per option — all on a shared time
  axis, driving in one tone and stopped in another, labelled with arrival and *longest single
  leg* — shows the actual trade in a glance: fewer halts buys an earlier arrival and costs a
  longer stretch in the car. That longest-leg number is what decides whether a plan survives a
  small child.
- **All options' totals visible at once.** A compact row of drive time / added time / cost /
  arrival, every option side by side, so switching is not the only way to compare.
- **Per-stop links and status labels in every view.** Rules 2 and 4 do not relax inside a tab.
- **Soft figures shown as soft.** An option over the traveller's rough budget is annotated with
  the overage, in the same type as everything else. No strike-through, no red, no "rejected".
- **Suggestive copy.** "Fewest stops, earliest arrival" beats "Recommended". Describe what an
  option *is*, and let the reader conclude.

### Map mechanics

Four things that silently ruin a baked map. `comparison-page.md` has the working code for all of
it, plus the projection, the rhythm strips and the copy rules.

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
construction, since a generated page cannot carry a retyped or stale figure.

## Scale the effort, never the honesty

Match the work to the question, and let each piece be earned separately:

- **Always:** measure the candidates, measure each option end to end, and apply the six rules.
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
  arrival clocks, and simplified geometry for the map, all from one engine. `--help` for usage.
- `corridor_scan.py` — candidates → detour, share, arrival vs sunset, in one instrument. Use it
  to shortlist stops, then `itinerary_compare.py` to assemble options from them.
- `research-brief.md` — the per-region brief that forces the three-state status back out.
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

**Numbers**

- A time in a table you cannot name the source of
- A route variant changed, and the detour column untouched
- A detour quoted as the sum of its stops' individual detours
- Two engines, one table
- Every candidate on one road

**Claims**

- "No mosquitoes" where the source said "generally not a problem"
- A recommendation with no "unverified" section
- **Status labels everywhere and almost no links** — the vocabulary has replaced the evidence
