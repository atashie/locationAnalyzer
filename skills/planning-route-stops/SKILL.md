---
name: planning-route-stops
description: Use when recommending where to stop, stay, or spend time along a journey between two points on given dates - overnight stops, layovers, charging or meal stops, multi-day halts - especially when options are compared on drive time, detour cost, arrival time or opening hours.
---

# Planning route stops

## Overview

A route recommendation is **a table of numbers plus a set of claims**. Finding good places and
spotting constraints is already a strength — baseline testing showed agents doing it well
unprompted. What fails reproducibly is **bookkeeping**: numbers from different instruments
compared as if alike, derived figures left stale when a route changes, and caveats that
evaporate between research notes and the final page.

This skill is that bookkeeping. It does not teach travel knowledge.

## The five rules

### 1. One instrument per comparison, and provenance down to the number

Measure every leg with the same engine. Two engines in one table produced an **hour-wide
disagreement** on a single leg, presented as comparable.

If a figure appears in a table it was **measured**, or it is **marked as an estimate**. A
four-row table of drive times accurate to the minute, with one leg sourced, is the
characteristic failure: *precision without provenance*.

**Every recommendation carries a link to the operator's own page — in the final output, not
just the research notes.** A status label is not a substitute for a source.

Testing this skill caught it displacing exactly that. Two runs under an earlier draft shipped
**0 and 5 outbound links** (4 distinct hosts between them), where the *unaided* baseline had
cited about 16 operator pages; adding this sentence took the next run to **55 links across 41
hosts** with no measured loss elsewhere. One post-fix run, so read it as a promising signal
rather than a proven effect — but the direction is clear, and the mechanism is not subtle:
Rule 3 gave the model a way to *sound* careful, and it stopped doing the thing that made it
careful. **Status says how sure you are; the link says why. Ship both.**

Keep **corridor experiments separate from stop itineraries**. A route forced through three
cities cost +1:55; stopping in the middle city cost +1:22. Quoting one as the other shipped.

### 2. Change a leg, recompute the whole row

Detour, share-of-trip and arrival time are all **derived** from the legs. Change a route
variant and every one of them moves.

> Worked example: a Sunday leg was revised 4:04 → 4:19 to avoid a motorway. Detour stayed
> "+41 min" and share stayed "55%". Correct values: **+56 min and 53%** — which moved the stop
> outside the traveller's stated detour budget. Nobody noticed for two revisions.

### 3. Verification status travels all the way to the output

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

### 4. Sweep off-corridor before you accept the corridor

Enumerate candidates **off** the obvious road and price each one's detour against the direct
route. Assuming the corridor is the most common structural miss: a baseline considered four
towns on one interstate and never priced a detour at all. In a real case the winning stop sat
**+49 minutes off the fastest line** — unreachable by corridor-only thinking.

A dead-end spur costs its detour **twice**. Route to it and back before judging.

### 5. Publish what you could not verify

A short "not verified" list, plus the calls worth making. Booking engines return 403/429 to
automation: "no live rate was obtainable" is the honest result, not a reason to substitute a
stale headline price.

## Scale the effort, never the honesty

Match the work to the question, and let each piece be earned separately rather than unlocked
by a score:

- **Always:** measure the candidates, and apply the five rules.
- **Write a document** when the comparison is too big to hold in a paragraph — several
  candidates, or competing constraints the reader needs to weigh.
- **Commission per-region research** only when the deciding facts are local and unknown
  (opening hours on a date, a seasonal programme), not merely because there are several stops.
- **Build a shareable page** only when someone other than the asker will actually use it, or
  they ask. An overnight family comparison usually does not need one.

A concise question deserves a concise answer. **The most likely way this skill makes work
worse is ceremony:** exhaustive status labelling and regional research consuming the attention
that a single decisive calculation or citation needed. If you are labelling more than you are
checking, stop labelling.

## Tools

- `corridor_scan.py` — candidates → detour, share, arrival vs sunset, in one instrument.
  Public endpoints, no keys. `--help` for usage.
- `research-brief.md` — the per-region brief that forces the three-state status back out.
- `endpoint-notes.md` — public-endpoint limits worth knowing before you hit them.

## Red flags

- A time in a table you cannot name the source of
- A route variant changed, and the detour column untouched
- "No mosquitoes" where the source said "generally not a problem"
- Every candidate on one road
- A recommendation with no "unverified" section
- Two engines, one table
- **Status labels everywhere and almost no links** — the vocabulary has replaced the evidence
