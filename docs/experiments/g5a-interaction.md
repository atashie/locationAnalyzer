# G5a: early interaction comparison — address-first vs describe-it (protocol)

**Status:** protocol only — no sessions run yet. This file is the test plan and the empty
recording sheet; results get filled in after moderated sessions, not written here in advance.

**Prototypes:** `v2/spikes/g5a-protos/address-first.html` (Variant A) and
`v2/spikes/g5a-protos/describe-it.html` (Variant B), sharing `shared.js` / `shared.css` /
`fixtures.js` / `regions.geojson` / `regions.js` in the same directory. See
`v2/spikes/g5a-protos/index.html` for a one-page summary of both.

---

## 1. The question

**Which entry mode — a short address-first form, or a one-box describe-it text field — gets a
household to a region they say they trust faster, and with fewer undetected errors?**

This is a comparison of *entry mode*, not a test of the full product. Both variants render the
identical criteria-card rail, map, and "why is this out?" behaviour (research doc
`06-ux-and-interaction-model.md` §5.9's wireframe B/C) once criteria exist; they differ only in
how criteria get created in the first place (§5 "three equivalent edit paths" — this gate tests
two of them head-to-head before committing to one as the default).

## 2. What the prototypes do and do not do

**Do:** render editable criteria cards over a map; switch between two real precomputed example
regions depending on which criteria are applied; show a scripted "why is this out?" explanation
with real numbers and a one-tap relax that previews the change in words first; recognise exactly
three scripted sentence patterns in Variant B; flag ambiguous places, places outside the
prototype's coverage box, and infeasible pairs of constraints, every time, by rule.

**Do not:** call any routing engine, geocoder, or language model. Do not compute a new isochrone
for whatever the participant types or enters — the shown region is always one of 20 **real**
precomputed examples (never an invented shape), chosen by nearest-anchor matching, not a live
recomputation of the participant's exact minutes. Do not show rush-hour or worst-case numbers,
home counts, or neighborhood-fit percentages (research doc
`09-codex-adversarial-review-pass2.md` finding A1). Do not persist anything after the tab closes
(no backend, no accounts).

**Region provenance (read before running any session).** Every shaded region is a feature from
`v2/data/g4_regions.geojson`, copied unmodified into `v2/spikes/g5a-protos/regions.geojson` (and
re-expressed as a plain script assignment in `regions.js` so it loads with no fetch/CORS/build
step). Each of the 20 features is the intersection of two real 25-minute drive-time **arrival**
isochrones, computed 2026-11-03 from a self-hosted Valhalla 3.9.1 instance around ten named
Research Triangle anchors (see `docs/experiments/g4-listings.md`). The prototype finds the
nearest of those ten anchors to whatever place a card resolves to, looks up the matching
precomputed pair, and falls back to the largest precomputed example containing that anchor when
no exact pair exists or when a criterion has been muted, deleted, or relaxed (which always
produces a *larger* real example, never a smaller one, matching the required mute/delete
behaviour). The map carries a visible label stating this on every region: *"computed 2026-11-03
from self-hosted Valhalla, fixed example."* Nothing in `fixtures.js` or `shared.js` invents a
polygon.

**Scripted, not AI, and labelled as such.** Variant B's parser (`shared.js`, functions
`parseDescription` / `resolvePlace` / `resolveCategory`) is four regular expressions and a
lookup table — a deterministic string match, never an LLM call. "Why is this out?" distances
(`estimateCard`) are straight-line distance × a fixed circuity factor × a fixed assumed speed per
mode, always labelled "estimated, typical conditions" — never "rush hour," never "worst case."

## 3. The three scripted sentence patterns (Variant B)

Documented identically on `index.html`, inside `describe-it.html`'s help text, and here. Close
wording variants of each are accepted (see `shared.js` regexes `RE_COMMUTE`, `RE_MIN_MODE_TO`,
`RE_MODE_TO_IN`, `RE_MIN_TO`); anything outside these three families is reported as not
understood and listed back to the participant, never guessed.

1. **Commute:** "`<who>` drives / bikes / walks to `<place>` in under `<N>` minutes" — e.g. *"I
   drive to Downtown Durham in under 20 minutes and my partner bikes to Carrboro in under 15
   minutes."*
2. **Amenity or place, time first:** "a `<N>`-minute walk / bike / drive to `<amenity or
   place>`" — e.g. *"A 10-minute walk to a library."*
3. **Place, mode assumed drive:** "`<N>` minutes to `<place>`" — e.g. *"30 minutes to Downtown
   Raleigh."*

## 4. How to run the prototypes

Serve the directory with any static file server and open `index.html`, or open the HTML files
directly from disk (both work; no build step):

```
npx serve v2/spikes/g5a-protos
# or
cd v2/spikes/g5a-protos && python -m http.server 8000
```

URL parameters, both variants: `?log=1` shows a moderator panel (per-task timer, correction /
why-out / relax counters, an event list, and a "Copy log" button that puts a tab-separated log on
the clipboard). `?demo=1` pre-fills a fixed demo scenario and computes immediately, for moderator
screenshots only — **never use it with a participant.** `?seed=1` is Variant-B-only and is
described in Task 5 below.

## 5. Participants

3–5 households, recruited as friends-and-family per research doc `06` §7. At least **two must
be phone-first** (own phone as the primary device for the session, not a loaner); couples
preferred where available, since the matched scenarios are two-commuter households. At least one
household should not work in tech. 30–40 minutes per household, think-aloud, screen- or
phone-recorded with consent.

## 6. Design: within-subject, counterbalanced, no repeated task

Each household does **two blocks**, one per variant, and never sees the same scenario twice.
Variant order, scenario order, and which pair of secondary tasks lands in which block are all
counterbalanced across households so no single confound (always-A-first, always-scenario-1-with-
address-first, etc.) can explain a timing or error difference (research doc
`09-codex-adversarial-review-pass2.md` finding A4). With 3–5 households this is a best-effort
balance, not a powered statistical design — the point is to rule out the cheapest alternative
explanations, not to compute a p-value.

| Household | Block 1 (variant / scenario / secondary tasks) | Block 2 (variant / scenario / secondary tasks) |
|---|---|---|
| H1 | A · Scenario 1 · {impossible search, ambiguous place} | B · Scenario 2 · {outside coverage, why-out/relax} |
| H2 | B · Scenario 1 · {outside coverage, why-out/relax} | A · Scenario 2 · {impossible search, ambiguous place} |
| H3 | A · Scenario 2 · {outside coverage, why-out/relax} | B · Scenario 1 · {impossible search, ambiguous place} |
| H4 | B · Scenario 2 · {impossible search, ambiguous place} | A · Scenario 1 · {outside coverage, why-out/relax} |
| H5 (if recruited) | repeat H1's row | repeat H1's row |

The seeded-misparse task (Task 5) only exists in Variant B — it tests a parsing error, and
Variant A's explicit mode/unit dropdowns have no equivalent failure mode. Run it during
*whichever block of each household is Variant B*, after that block's cold-start task.

## 7. The two matched novel scenarios

Same shape (two commuters, 25-minute drive each, one amenity, 10-minute walk), different places,
different names, so neither a practice effect nor a specific-place memory can explain a
difference between the blocks. Read the scenario to the participant in your own words or theirs —
do not read the bracketed structure, and do not name the entry mode, the parser, or the word
"card."

- **Scenario 1.** "Jordan just took a job at UNC Hospitals and needs to get there in under 25
  minutes by car. Jordan's partner, Sam, is starting a job near Southpoint and also needs to get
  there in under 25 minutes by car. They'd also like to be able to walk to a park in about 10
  minutes. Find an area where this works for both of them."
- **Scenario 2.** "Morgan just took a job in Downtown Durham and needs to get there in under 25
  minutes by car. Morgan's partner, Priya, works near NC State University and also needs to get
  there in under 25 minutes by car. They'd also like to be able to walk to a library in about 10
  minutes. Find an area where this works for both of them."

Verified against the real region data (`node -e` against `shared.js`, 2026-11-03): Scenario 1
matches Gate G4 feature id 3 (UNC Hospitals ↔ Southpoint Mall, 298.81 km²) exactly; muting either
commuter switches to feature id 18 (Carrboro Town Hall ↔ UNC Hospitals, 324.28 km², larger).
Scenario 2 matches feature id 16 (Downtown Durham ↔ NC State Bell Tower, 139.27 km²) exactly;
muting either commuter switches to feature id 17 (Downtown Durham ↔ RTP (Kit Creek Rd), 423.60
km², larger).

## 8. Task list

Give each task as a plain request, in the moderator's or the participant's own words. None of the
wording below names the feature under test (no "try muting a card," no "see if you notice
anything wrong," no "test the why-is-this-out panel") — that wording is for the moderator's
script only, never read aloud (research doc `09` finding A4). A **confident wrong answer counts
as a failure, not a success** — if a participant states they trust a region that is visibly wrong
(the seeded card, an unresolved ambiguous place, an infeasible pair still showing a region), mark
the task failed regardless of how quickly or confidently they finished.

**Task 1 — Cold start (the assigned matched scenario).** Read the household's assigned scenario
(§7) for this block. Measure: time to a region the participant says they trust; whether they
built two separate people or two separate "commute filters" in their own words (listen, do not
prompt); whether they looked at the cards while waiting; number of corrections before they
declared trust.

**Task 2 — Impossible search.** "Imagine instead that one of you needs to be within 20 minutes
of Hillsborough, and the other within 20 minutes of Cary. Find where you could both live." This
pair is infeasible by the scripted distance estimate (≈34 road miles apart; 20 + 20 = 40 minutes
of combined reach at 0.5 mi/min reaches only 20 miles) — the prototype always reports "No area
meets all criteria" with the two relax-to-N suggestions, never a region. Measure: does the
participant accept "no area meets all criteria" as the answer, or do they keep adjusting as if a
region should appear; do they read the explanation; do they use a relax button or change a
workplace instead.

**Task 3 — Ambiguous place.** "You'd like to be able to bike to Whole Foods within about 15
minutes." Three Whole Foods locations exist in the gazetteer; the prototype must not guess.
Measure: does the participant notice the chooser; how do they pick; do they understand the
criterion is not applied until they choose.

**Task 4 — Outside coverage.** "Your cousin lives in Greensboro. Check whether anywhere in your
search area is within 30 minutes of Greensboro by car." Greensboro is outside the prototype's
coverage box. Measure: does the participant understand why nothing is offered; do they try to
force it; do they read the coverage notice.

**Task 5 — Seeded misparse (Variant B block only).** "One more thing — you'd also like to be no
more than 20 minutes from the airport. Add that however you'd naturally say it." Load this
block's URL with `?seed=1`. If the participant's phrasing matches pattern 3 ("20 minutes to the
airport" or close to it), the parser deliberately shows the resulting card as **20 mi** instead of
20 minutes. Measure: does the participant notice the unit on the card or in the echoed "Added:…"
line before declaring trust; if they don't notice unprompted, point at the card after the trust
rating and ask what it says — record whether they catch it only when prompted, or not at all.
If their first phrasing doesn't trigger the bug (no number, or a different place name), prompt
once with "try saying it as a number of minutes" before moving on; record which happened.

**Task 6 — Why is this out, and relax.** Use the spot matched to this block's scenario: for
Scenario 1, "Check whether the Downtown Durham area would work for this search, and if not, see
what it would take to include it" (fails only the UNC Hospitals commuter, estimated ≈27 min
against a 25-minute limit — a near miss). For Scenario 2, "Check whether the Hope Valley area
would work for this search, and if not, see what it would take to include it" (fails only the NC
State commuter, estimated ≈48 min against a 25-minute limit). Measure: do they find the tap-map
or the "Why is a place out?" control; do they read the actual numbers; do they use the "relax to
N" button or edit the card manually; do they understand the preview-before-apply wording.

After every task: ask the Single Ease Question ("Overall, how easy or difficult was this task?"
1 = very difficult, 7 = very easy) and note it before moving on.

## 9. Measures

Built into the prototype's `?log=1` moderator panel (press **Start task** at the start of each
task, **Mark trusted** the moment the participant says, unprompted, that they trust the shown
region, **Copy log** at the end of each block and paste into that participant's results section
below):

- **Time to a trusted region** — moderator presses "Mark trusted"; the panel reports it relative
  to "Start task." Do not accept "I guess this is right" as trust; the participant must say so
  unprompted or after only a neutral "is this what you'd expect?"
- **Number of corrections** — auto-counted (every edit, mute, delete, toggle, and relax after the
  first compute/understand increments it).
- **Whether the seeded error was caught** — auto-flagged when the participant switches the seeded
  card's unit back to minutes; also record whether it was caught unprompted or only after the
  moderator pointed at the card (Task 5).
- **Why-out opens and relax clicks** — auto-counted, informational (did they use the built
  control or work around it).
- **Single Ease Question (1–7)** per task (manual, see §8).
- **Trust rating (1–7)** at the end of each block: "I believe the shaded area is right for what
  I asked." (manual)
- **Qualitative:** vocabulary used in the warm-up and Task 1 (minutes vs. miles vs. neighborhood
  names); whether "two people" or "two filters" is how they describe the household; anything said
  about the region being "real" vs. a guess.

Warm-up question before Task 1 (either block): *"Tell me about the last time you looked for a
place to live. How did you decide which areas to look in?"* Note their own vocabulary before any
task biases it.

## 10. Interview questions (end of session, after both blocks)

- "Does anyone in your household need to use public transit for one of these trips, rather than
  driving, biking, or walking? Would that have changed how you'd search?" (transit dependence —
  this prototype only offers drive/bike/walk; a "yes" here is a direct signal for the transit mode
  backlog item, not evidence to add a feature inside this prototype.)
- "If the app let you say 'the park matters more to me than the commute does,' would you want
  that? What would you actually type or tap?" (whether numeric or ranked weighting belongs in v2 —
  listen for whether they reach for a number, an order, or a sentence; research doc `06` §6 and
  `09` finding A8 both treat this as unresolved.)
- "Which of the two ways of starting — typing a sentence, or filling in the boxes — would you
  use the next time you actually moved? What would you tell your partner it does?"
- Trust rating repeated once more as a single overall number, 1–7, for the session as a whole.

## 11. Fairness check

**Claim to verify:** paired prompts that differ only in a protected-trait cue (a relationship
word, a name commonly associated with a different gender or ethnicity) must produce identical
cards and an identical region — not just similar-looking output, byte-identical place, mode, and
minutes. This prototype has no suggestion engine and no cohort inference to audit (research doc
`09` finding A5 is a risk for a future NL-to-suggestion layer, not for this scripted parser), so
the check here is a regression guarantee: the parser must be provably blind to anything but the
place, mode, and minutes it extracts.

**How to run it (reproducible, already run once for this document, 2026-11-03):**

```js
// from v2/spikes/g5a-protos/
const G = require('./shared.js');
function cardKey(c) { return {kind:c.kind, placeId:c.placeId, category:c.category, mode:c.mode, limit:c.limit, unit:c.unit}; }
const pairs = [
  ['I drive to UNC Hospitals in under 25 minutes and my wife drives to Southpoint in under 25 minutes.',
   'I drive to UNC Hospitals in under 25 minutes and my husband drives to Southpoint in under 25 minutes.'],
  ['Jamal drives to UNC Hospitals in under 25 minutes.',
   'Connor drives to UNC Hospitals in under 25 minutes.'],
  ['My girlfriend drives to Downtown Durham in under 20 minutes.',
   'My fiance drives to Downtown Durham in under 20 minutes.']
];
pairs.forEach(([a, b]) => {
  const ka = G.parseDescription(a, {seed:false}).cards.map(cardKey);
  const kb = G.parseDescription(b, {seed:false}).cards.map(cardKey);
  console.log(JSON.stringify(ka) === JSON.stringify(kb) ? 'MATCH' : 'MISMATCH', a, '|', b);
});
```

**Result when run 2026-11-03:** all three pairs (relationship-word pair: wife/husband; name pair:
Jamal/Connor; relationship-word pair: girlfriend/fiance) returned `MATCH` — identical `placeId`,
`mode`, `limit`, `unit` on every card. Only the cosmetic `who` display label differs (e.g.
"Jamal" vs. "Connor"), and `who` is read solely by display functions (`cardTitle`,
`cardDescription`, the map marker text, the relax-button label) — grep `shared.js` for `.who` to
confirm it is never read by `cardAnchor`, `estimateCard`, `decideRegion`, or `pickFeature`, the
four functions that decide what region gets shown.

**For the live sessions:** after each household's session, re-run the moderator's actual Task 1
phrasing through `parseDescription` twice — once as said, once with the subject swapped to a
different name/relationship-word pair — and record MATCH/MISMATCH below. A MISMATCH on any real
session transcript is a release blocker for the parser, independent of the two-variant comparison
this gate is otherwise about.

| Household | Original Task 1 phrasing (as said) | Swapped phrasing | MATCH / MISMATCH |
|---|---|---|---|
| H1 | | | |
| H2 | | | |
| H3 | | | |
| H4 | | | |

## 12. Success criteria

To treat this comparison as informative enough to set entry-mode prominence in v2 (not to ship
either prototype as-is):

- At least 4 of the 5 tasks that have a correct/incorrect outcome (impossible search, ambiguous
  place, outside coverage, seeded misparse, why-out/relax) are completed **correctly** — a
  confident wrong answer (trusting an unresolved, seeded, or infeasible result) counts as
  incorrect — by a majority of households in **both** variants. If one variant clears this bar
  and the other does not, that is itself the result, not a tie to break.
- The seeded misparse (Task 5) is caught unprompted by at least half of households in the
  Variant-B block; if fewer than half catch it even when prompted, that is a release blocker for
  describe-it regardless of how it compares to address-first.
- Median SEQ ≥ 5 for Task 1 in whichever variant is faster to a trusted region; if the faster
  variant also has the lower median SEQ, speed is not evidence of a better entry mode.
- Every household can state, in their own words, what a muted card does to the map (removes the
  constraint, not just hides it) — this is the direct test of finding A2; any household who
  believes muting only hides the card is a documentation/labelling failure to fix before v2, not
  a close call.
- No MISMATCH in the fairness check (§11) on any real session transcript.

Signals to change course, independent of which variant "wins": any household who never opens a
card in either block (cards are not prominent enough, in either design); any household who asks
"how much more important is the park than the commute" unprompted (bring the weighting interview
answer, §10, forward into the backlog with urgency); any household who completes Task 1 quickly
in one variant but cannot complete the impossible-search or ambiguous-place task in the other
variant (the comparison is about entry mode, but a variant that cannot support the shared card
rail equally well is a prototype bug to fix, not a finding about entry mode).

## 13. What each outcome changes

| If the sessions show… | Then… |
|---|---|
| Address-first reaches a trusted region faster, with equal or fewer undetected errors | Entry-mode prominence in v2 defaults to the short form; a describe-it text box becomes a secondary/optional entry, not the hero control. |
| Describe-it reaches a trusted region faster, with equal or fewer undetected errors | NL stays the hero entry per research doc `06`'s hybrid recommendation, but the seeded-misparse result (§12) sets how much echo/confirmation v2 must show before the region renders. |
| Households consistently build two separate *people* with their own places (not two generic "commute filters") | "Person" is exposed as a first-class object in v2 (a named thing with its own places/modes), matching research doc `06` §5.2's differentiation bet. |
| Households consistently build two generic filters and never refer to "the other person" as an object | "Person" can stay an internal grouping; v2 need not expose it as a user-facing object yet (research doc `09` finding A3's caution). |
| A household unprompted asks to weight one criterion over another (§10 interview or spontaneously) | Numeric or ranked weighting moves from "deferred" to an active v2 candidate (research doc `09` finding A8); still needs its own test before shipping. |
| No household asks for weighting, and all can describe hard/soft-equivalent behaviour (mute vs. delete, relax) in their own words | Weighting stays deferred past v2; hard limits plus mute/delete/relax remains the shipped model. |
| Any household reports transit dependence in §10 | Elevates the transit-mode backlog item's priority; this prototype's drive/bike/walk-only scope is not itself evidence transit is unneeded. |

## 14. Results (one table per participant — empty; fill in after each session)

### Household 1

- Phone-first: Y / N · Couple: Y / N · Works in tech: Y / N
- Block order: ________ · Scenario order: ________ · Secondary-task set: ________
- Consent / recording: ________

| Task | Variant | Correct outcome? | Time to trusted region | Corrections | SEQ (1–7) | Notes |
|---|---|---|---|---|---|---|
| 1 — Cold start | | | | | | |
| 2 — Impossible search | | | | | | |
| 3 — Ambiguous place | | | | | | |
| 4 — Outside coverage | | | | | | |
| 5 — Seeded misparse | | caught unprompted / prompted / missed | | | | |
| 6 — Why-out / relax | | | | | | |

End-of-session trust (1–7): ____ · Transit dependence noted: ____ · Wants weighting: ____ ·
Fairness re-check (§11): MATCH / MISMATCH

### Household 2

- Phone-first: Y / N · Couple: Y / N · Works in tech: Y / N
- Block order: ________ · Scenario order: ________ · Secondary-task set: ________
- Consent / recording: ________

| Task | Variant | Correct outcome? | Time to trusted region | Corrections | SEQ (1–7) | Notes |
|---|---|---|---|---|---|---|
| 1 — Cold start | | | | | | |
| 2 — Impossible search | | | | | | |
| 3 — Ambiguous place | | | | | | |
| 4 — Outside coverage | | | | | | |
| 5 — Seeded misparse | | caught unprompted / prompted / missed | | | | |
| 6 — Why-out / relax | | | | | | |

End-of-session trust (1–7): ____ · Transit dependence noted: ____ · Wants weighting: ____ ·
Fairness re-check (§11): MATCH / MISMATCH

### Household 3

- Phone-first: Y / N · Couple: Y / N · Works in tech: Y / N
- Block order: ________ · Scenario order: ________ · Secondary-task set: ________
- Consent / recording: ________

| Task | Variant | Correct outcome? | Time to trusted region | Corrections | SEQ (1–7) | Notes |
|---|---|---|---|---|---|---|
| 1 — Cold start | | | | | | |
| 2 — Impossible search | | | | | | |
| 3 — Ambiguous place | | | | | | |
| 4 — Outside coverage | | | | | | |
| 5 — Seeded misparse | | caught unprompted / prompted / missed | | | | |
| 6 — Why-out / relax | | | | | | |

End-of-session trust (1–7): ____ · Transit dependence noted: ____ · Wants weighting: ____ ·
Fairness re-check (§11): MATCH / MISMATCH

### Household 4

- Phone-first: Y / N · Couple: Y / N · Works in tech: Y / N
- Block order: ________ · Scenario order: ________ · Secondary-task set: ________
- Consent / recording: ________

| Task | Variant | Correct outcome? | Time to trusted region | Corrections | SEQ (1–7) | Notes |
|---|---|---|---|---|---|---|
| 1 — Cold start | | | | | | |
| 2 — Impossible search | | | | | | |
| 3 — Ambiguous place | | | | | | |
| 4 — Outside coverage | | | | | | |
| 5 — Seeded misparse | | caught unprompted / prompted / missed | | | | |
| 6 — Why-out / relax | | | | | | |

End-of-session trust (1–7): ____ · Transit dependence noted: ____ · Wants weighting: ____ ·
Fairness re-check (§11): MATCH / MISMATCH

### Household 5 (if recruited)

- Phone-first: Y / N · Couple: Y / N · Works in tech: Y / N
- Block order: ________ · Scenario order: ________ · Secondary-task set: ________
- Consent / recording: ________

| Task | Variant | Correct outcome? | Time to trusted region | Corrections | SEQ (1–7) | Notes |
|---|---|---|---|---|---|---|
| 1 — Cold start | | | | | | |
| 2 — Impossible search | | | | | | |
| 3 — Ambiguous place | | | | | | |
| 4 — Outside coverage | | | | | | |
| 5 — Seeded misparse | | caught unprompted / prompted / missed | | | | |
| 6 — Why-out / relax | | | | | | |

End-of-session trust (1–7): ____ · Transit dependence noted: ____ · Wants weighting: ____ ·
Fairness re-check (§11): MATCH / MISMATCH

## 15. Verdict

(Owner fills in after all sessions, against §12's success criteria and §13's decision table —
not before.)

---

## Appendix: implementation notes verified while building this protocol (2026-11-03)

- `node --check` passes on `fixtures.js`, `regions.js`, and `shared.js`.
- `regions.geojson` parses as a FeatureCollection of 20 features (`node -e
  "JSON.parse(require('fs').readFileSync('v2/spikes/g5a-protos/regions.geojson'))"`); `regions.js`
  exposes the same 20 features as `window.G5A_REGIONS` / `module.exports`.
- Every `<script src>` and `<link href>` in `index.html`, `address-first.html`, and
  `describe-it.html` resolves to a file present in `v2/spikes/g5a-protos/` or to the pinned CDN
  URL below; there is no reference to a missing local path.
- MapLibre GL JS is pinned to **v3.6.2** from `cdn.jsdelivr.net/npm/maplibre-gl@3.6.2` (both the
  JS and CSS); fetched 2026-11-03 and confirmed to return the real library (BSD-licensed MapLibre
  source, not a 404), so the version exists and the CDN path is correct as of this date.
- Scenario matching, the mute/delete-always-shows-a-larger-real-region behaviour, the impossible-
  search distances, and the fairness-check pairs above were each exercised with `node -e` against
  `shared.js` on 2026-11-03 and produced the numbers quoted in §7, §8, and §11 of this document —
  they are not estimates.
- Not implemented / known gaps: no actual browser was available to this build, so keyboard-
  tab-order and the 390×844 phone layout were verified by reading the CSS and markup, not by
  opening a browser — a moderator should do one quick manual pass on a real phone and with a
  keyboard before the first session. The "why is this out?" map-tap gesture has no keyboard
  equivalent other than the explicit "Why is a place out?" dropdown-and-button control next to
  it; that control is the keyboard path, not an afterthought, but it has not been tested with an
  actual screen reader.
