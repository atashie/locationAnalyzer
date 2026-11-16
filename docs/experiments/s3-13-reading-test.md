# The reading test: what someone who did not build this concludes from the map

**Status: protocol written 2026-11-16, not yet run.** Results go at the bottom, in this file.

Every check this project has is of one shape: *the page says what we intended it to say*. 1,544
Python tests, 41 card checks, 87 browser conformance checks and four mutation suites all check
that. **Nothing has ever checked what a reader concludes.** Codex passes 54 and 55 both ranked this
the highest-value unblocked item, and every browser session so far was driven by the model that
wrote the sentences — which is the worst possible test subject, because it already knows what each
one is hedging against.

The owner's addition, 2026-11-16: the reader should be somewhere they **know**, looking at things
they **know about**, so they can catch errors as well as read words. That turns one test into two.

| what it tests | how we would otherwise find out |
|---|---|
| does the wording lead to a correct belief? | no other way at all |
| does a local catch a wrong answer? | only by the owner walking it, one journey at a time |

## What the reader sees

Seven criteria, built 2026-11-16 for this test. One is switched on when the page opens; the rest
are there to be switched on, which is also how somebody actually searches.

| criterion | mode | opens | on at start |
|---|---|---|---|
| Grocery shop | walk | 20 min | **yes** |
| Park | walk | 15 min | no |
| School | walk | 20 min | no |
| Grocery shop | drive | 10 min | no |
| Coffee shop | bike | 15 min | no |
| Duke University Hospital | drive | 30 min | no |
| RDU airport | drive | 40 min | no |

Area: the Triangle, bounded `[-79.2, 35.7, -78.5, 36.15]` — Chapel Hill, Carrboro, Durham, Cary
and most of Raleigh. The reader works in the part of it they know.

## What counts as failing

Written down before the test runs, so it cannot be rationalised afterwards. The test **fails** on
any of these:

1. The reader's own words for an INCLUDED verdict claim more certainty than we hold — "it is a
   12-minute walk" rather than "it reckons about 12 minutes".
2. The reader does not notice the estimate line under the verdict without being pointed at it.
3. The reader cannot say what the restriction warning changes for them.
4. The reader cannot say what the map has ruled out. Excluded ground carries no card, and a wrong
   exclusion is the failure a household never sees.
5. The reader reaches a confident wrong belief about a place they know, and the words gave them no
   reason to doubt it.

Anything else is a finding, not a failure.

## What the owner must not do

The whole value is in what the reader works out alone.

- **Do not explain the model** until Part 5. Not the grid, not the rounding, not the restricted
  ways, not what UNKNOWN means.
- **Do not defend a wrong answer.** If they say a result is wrong, write down why they think so and
  move on. Arguing turns a finding into a negotiation.
- **Do not paraphrase.** Write their words. "He thought it was fine" is not data; "that's bang on,
  I walk that" is.
- **Do not steer them to a good cell.** Let them pick.
- Say "what do you make of that?" and then be quiet.

## The script

Roughly 30 minutes. The owner reads the **bolded** words aloud and writes down what comes back.

### Part 0 — setup, before they arrive
Serve the page, open it, leave it on the opening view. One criterion on. Nothing explained.

### Part 1 — first contact (5 min)
> **"This is a map for finding somewhere to live. Have a look. Tell me what you think it's for and
> what you'd do first."**

Then be quiet. Record, in order:
- the first thing they touch;
- whether they find the criteria list unprompted;
- whether they hover a cell unprompted;
- anything they say.

### Part 2 — three places they know (15 min)
> **"Find somewhere you know well. A street you've lived on, or near."**

For each of three places, **before** they look at the card:
1. **"Would you keep this home on your shortlist?"**
2. **"How long do you think the walk to a shop is from there?"**
3. **"Which shop do you think you'd be walking to?"**

Then let them hover it and read the card. Ask:
4. **"Does that match what you expected?"** — and if not, **"what do you think is wrong?"**
5. If the card shows the restriction warning: **"What does that line change for you?"**

Record their minutes and ours, their shop and ours, and every disagreement **with their reason**.

### Part 3 — what has it ruled out (5 min)
> **"Turn on a second criterion — whichever you'd actually care about."**

Then:
> **"Point at somewhere this map has ruled out. What do you think it's telling you about that
> place?"**

This is the one with no card. Record whether they can find excluded ground at all, and what they
think the exclusion means. A reader who says "there's nothing there" has read it as a fact about
the world; a reader who says "it reckons you can't get to a shop from there in twenty minutes" has
read it as a model result.

### Part 4 — the words (5 min)
Point at the grey line under a verdict — **without reading it to them**:
> **"Read that out and tell me what it means."**

Then:
> **"Does this map tell you how long your walk will take?"**

Record whether they distinguish *our estimate for a nearby grid point* from *your walk from your
door*.

### Part 5 — the decision, then you may explain (2 min)
> **"If you were actually looking for a house, would you use this? What would you still need?"**

Only now, explain anything they ask about.

## Recording sheet

Fill `docs/experiments/audit/reading-test-01.csv`. One row per probe. The columns:

| column | what goes in it |
|---|---|
| `probe` | `first-contact`, `place-1`..`place-3`, `exclusion`, `words`, `decision` |
| `lon`, `lat` | where they hovered, if anywhere |
| `their_minutes` | the number they said before seeing the card |
| `our_minutes` | what the card said |
| `their_shop` | the shop they expected |
| `our_shop` | the shop the card named |
| `agreed` | `yes`, `no`, `partly` |
| `their_words` | **verbatim.** The most valuable column in the file |
| `failure_criterion` | 1-5 above, or blank |
| `notes` | anything else |

## Why the opening view shows one criterion

Found while building this, and worth recording because only a real criteria set exposes it.

Pass 43 F4 established that **every manifest entry starts enabled in the page**. With one
criterion that was harmless. With seven it makes the opening view the **intersection of all
seven**, at seven default minutes — and "drive to RDU in under 10 minutes" is empty from anywhere
in Chapel Hill. The first thing a reader would have met is a blank map, and the first thing they
would have concluded is that the thing is broken. `resetAll` had the same bug a button press away:
it switched every criterion on.

The manifest now carries `default_on` and `default_threshold_min` per layer, both optional and
both absent-safe, and `card.js` owns the two rules so Node can check them. A bundle that publishes
neither field behaves exactly as it did before.

**This is what the reading test is for, found a day early by preparing it.** No test in the suite
could have caught it: every one of them checks a layer, a message or a sentence, and this was a
property of the *set*.

## Two things to watch for that are known, not surprises

Both are limitations of the model that a local is well placed to notice. They are recorded here so
the owner is not caught out, and **must not be mentioned to the reader**.

* **Drive times carry no congestion.** The profile is static speeds with no intersection
  penalties and no turn restrictions. Chapel Hill to RDU reads **24.9 minutes**; at eight in the
  morning it is not. A reader who says "that's a half-hour at rush hour" is right, and that is a
  finding about what the number means, not an error in it.
* **Parks snap to the polygon centroid.** A large park's walk time is to its *middle*, not to a
  gate. 7 of 746 parks were dropped for sitting more than 300 m from any road.

* **Grey diagonal hatching marks UNKNOWN**, and there is a lot of it. **17.0% of the cells the
  browser paints** are more than 200 m from any road we hold, so no journey was ever measured from
  them and the map can only say "we cannot say". It grows as the limit rises -- 38,834 cells at a
  5-minute limit, 56,034 at 20, 56,036 from 21 on -- because a cell we could confidently rule out
  at 5 minutes cannot be ruled out at 20. That is the correct reading of a lower bound, and it
  looks like a fault. It covers **0.67% of buildings**. *(Every figure in this bullet is on the
  published WGS84 grid, which is what is on screen. The UTM source grid gives 17.4% and 0.71%, and
  an earlier version of this paragraph mixed the two — pass 56, claims 4 and 5.)* The owner read it as an anomaly on first sight, which is the reading test working a
  day early. The legend calls it *"nodata in an enabled layer"* -- three words of jargon in a row,
  on the one thing a reader is most likely to ask about.
* **Donut holes: a parcel ruled out with every neighbour around it included.** Real, measured, and
  caused by the access-snapping rule considering only the single nearest edge. **121** of them on
  Park / walk at 20 minutes on the published grid, holding **356 buildings** across 76 of them.
  *(125 and 414 are the UTM-grid figures.)* See [[project-phase1-s3-donut-holes]]. If a
  reader points at one, they are right and it is not their misreading.

Also known: of the seven criteria only *Grocery shop, walk* names a destination or discloses a
restricted route, so the other six print two "this criterion does not say" lines each. That is
honest and it is also a lot of text. Whether a reader finds it careful or noisy is worth recording
either way.

## The second defect this preparation found

Hovering **one cell** on the built page, the card read `own_triangle_duke-hospital_drive PASS 20
min`. The manifest had carried the label *Duke University Hospital, drive* all along and the card
had never used it. One ugly line at one criterion; most of the card at four. Fixed, with three
checks and two mutations.

Two defects, both found by building the thing the test needed rather than by running a test.
Neither was reachable by the suite, which checks layers, messages and sentences — and both of
these were properties of the **set**.

## Results

*(Not yet run.)*
