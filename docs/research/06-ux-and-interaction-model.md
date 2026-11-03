# 06 — UX, User Needs, and the Interaction Model

**Date:** 2026-11-03
**Status:** Complete (research only; no code modified). Recommends the interaction model for decision 3 in `../plans/2026-11-03-v2-rethink-decisions.md`.
**Scope and method:** Desk research on (1) how people express location needs when choosing where to live, (2) the reception of existing commute/isochrone and AI-search tools, (3) applicable HCI findings, and (4) the specific design questions in the brief. Primary sources were fetched directly: Hacker News threads (via the HN Algolia API and item pages), NAR and Zillow survey summaries, Nielsen Norman Group and Baymard articles, vendor announcements (Zillow, Redfin/Sierra, Airbnb, Google, OpenAI), and paper metadata/abstracts (OpenAlex). Every quotation below is verbatim from the cited page as fetched on 2026-11-03; nothing inside quotation marks is paraphrased.

**Access limitations (read before relying on this document):**
- Reddit could not be read. `reddit.com` and `old.reddit.com` are blocked by the fetch tool; three mirrors (redlib, safereddit, r.jina.ai) returned 429/503/401. The brief asked for r/RealEstate, r/FirstTimeHomeBuyer, r/gis, r/dataisbeautiful and r/UXDesign quotes; **none are included**. Hacker News threads carry the forum evidence instead, and the friends-and-family tests in §7 are designed to close the gap with real non-technical users.
- The session's web-search budget was exhausted part-way through; later evidence came from direct URL fetches only. Kayak AI Mode, Expedia Romie, Realtor.com and Homes.com AI features, and Perplexity/ChatGPT map search were **not verified** in this pass and are marked "(unverified)".
- Several pages returned HTTP 403 (Zillow Research 2026 buyers report, Zillow Front Porch commute-filter post, GeekWire, OpenAI, ACM DL, Springer, hankbailey.com, PhoneArena). Where a figure comes only from a search-engine summary of a blocked page it is marked "(from search summary; page returned 403)".

---

## 1. Executive summary

- **Commute is one of several roughly co-equal location constraints, not the dominant one.** NAR's 2025 Profile puts "quality of the neighborhood" at 59%, "convenient access to friends and family" at 47%, and "convenience to job" at 31% (down from 52% in 2014). Zillow's 2026 buyers report has commute at 49% "very or extremely important", walkability at 61%, proximity to shopping/services at 53%, sense of community at 51%. The product's premise — many constraints combined — matches how buyers actually weigh location; "near my sister's house" is the second most common factor, not an edge case.
- **People already want this tool and have been building it for themselves for 15 years.** HN threads from 2018 to 2026 repeat the same request ("to be able to search properties within say 30 minutes drive from work") and the same discovery ("many geographically closer properties were often much further in terms of time"; "Turned 40 minutes real estate searches into 40ms or so"). Every popular self-built tool is an isochrone over a map, not a chat.
- **The two most-requested features in those threads are multiple origins with overlap, and honest travel-time variance** (best/worst case; "to be on time 95% of the time"). The most common complaint is travel-time accuracy ("it tells me by car I can get somewhere in < 15 min, but it's always taken me 20").
- **Users describe constraints as a short list of hard limits with a budget trade-off**, e.g. "you could have inexpensive, short travel time, or nice/safe, choose two." The modal maximum acceptable commute in Zillow's survey is 30 minutes. Hard AND-intersection is the right default; soft/weighted scoring is a refinement, not the entry point.
- **Pure chat has failed, in public, at exactly our task.** In the Show HN "Map with an LLM" thread users report "absolutely invented data. Same prompt, three times gives 3-4 different results" and pins "where a train station is." Zillow's natural-language search was called "a broken promise" ("You cannot talk to Zillow's app and search like you talk to a family member and find the homes you want. Not even close.").
- **Pure forms have also failed — ours.** V1's criteria form + polygon was judged clunky; Baymard finds "the majority of ecommerce sites have filtering experiences that are 'mediocre' to 'poor'", and Redfin's pitch for conversational search is explicitly against "dropdown menus, setting exact square footage ranges, and drawing hard-and-fast boundaries on maps."
- **The HCI literature converged on the middle long ago:** Horvitz's "elegant coupling of automated services with direct manipulation" (1999); Shneiderman's "high levels of human control and high levels of computer automation" (2020); Nielsen's "Future AI systems will likely have a hybrid user interface that combines elements of both intent-based and command-based interfaces while still retaining many GUI elements" (2023).
- **The articulation barrier is real for our target users.** Nielsen: "half the population in rich countries is not articulate enough to get good results" from prose prompts. NN/G's remedy: "A GUI could lessen the users' memory load by favoring recognition over recall."
- **Users iterate on AI output in pieces, not wholesale.** NN/G observed "accordion editing" and "apple picking" and concluded users need "compartmentalization of AI responses" and "direct editing". A criteria card is exactly such a compartment.
- **Industry is landing on the same hybrid.** Airbnb's CEO: "just adopting a chatbot-like interface won't work for travel use cases"; Airbnb ships "AI filters that anticipate what the user is looking for" (typing "baby" surfaces 'cribs', 'playgrounds', 'toys'). Google Maps' Gemini "will answer your question and also show the reviews it based its answer on so you can verify the information." Zillow inside ChatGPT renders "an interactive map showing options."
- **Trust requires visible components.** Baymard: 28% of sites fail to show applied filters, causing missing confirmation, no quick removal, and lost context. Explanation research (Kulesza et al. 2013) finds more complete explanations improve mental models while oversimplified ones produce "cognitive strain and diminished trust." Users should see each constraint's own layer and be able to ask "why is this area out?"
- **Latency must be designed, not hoped for.** Nielsen's 10-second limit for keeping attention requires percent-done feedback; V1's OSM queries routinely exceeded it. Stream constraints onto the map one at a time so the user watches the region narrow.
- **RECOMMENDED MODEL: (2) the hybrid — natural language (typed or spoken) builds a visible, editable, structured query shown as criteria cards over the map; the map is the primary canvas; chat is one of three ways to edit the same state (text, card controls, map gestures).** Chat-first loses because LLMs are unreliable at geography and non-technical users cannot see or fix what was understood; form-first loses because it is what failed in V1 and it puts the articulation burden on the user before any result appears. The hybrid keeps the LLM where it is strong (parsing intent, disambiguating, suggesting), keeps a deterministic geo engine where correctness matters, and keeps the user in control of a state they can read.

---

## 2. What users want: synthesized needs with evidence

### 2.1 Vocabulary and constraint structure

Buyers talk in **minutes, named places, and modes**, not miles or coordinates. The example prompts Zillow chose for its launch are the vocabulary: "Homes 30 min drive from Millennium Park", "Apartments near Denver Union Station", "3-bedroom houses near Roosevelt High School" (Zillow press release, 2024-09-04, https://zillow.mediaroom.com/2024-09-04-Zillows-AI-powered-home-search-gets-smarter-with-new-natural-language-features). HN house-hunters say "within say 30 minutes drive from work" (angarg12, https://news.ycombinator.com/item?id=17679148) and "decently transit-accessible to my office while still cheap" (ng-henry, https://news.ycombinator.com/item?id=36847960).

Constraints are **few and mostly hard, with a budget trade-off running through them**. The clearest statement is from a London search: "The ultimate conclusion was that you could have inexpensive, short travel time, or nice/safe, choose two" (throwaway22032, HN 36847960). closemove.com, the only multi-person tool found, models exactly this: "1-6 people's workplaces, budgets, and maximum commute times", filtering to "only properties satisfying everyone's constraints" (https://news.ycombinator.com/item?id=44965079). Its first commenter immediately asked for "more granular filtering, like number of bathrooms" — structural constraints (location) come first, attribute filters (bathrooms) second.

**Thresholds:** In Zillow's 2019 Consumer Housing Trends survey (13,000 households) respondents reported "actual commute time of 20 minutes and maximum acceptable commute of 30 minutes", with about one-third willing to go 30–44 minutes and 12% to 45–60 (https://zillow.mediaroom.com/2020-02-13-The-Major-Role-Work-Life-Balance-Plays-in-Decisions-About-Home). This gives a defensible default ("25–30 minutes") and a sensible slider range (10–60).

### 2.2 How many constraints, and which

- NAR 2025: quality of neighborhood 59%; convenient access to friends and family 47%; convenience to job 31% (https://crosscountrymortgage.com/mortgage/resources/nar-profile-home-buyers-sellers-2025/); overall affordability 35% (from search summary of the report PDF, https://www.rirealtors.org/clientuploads/documents/NAR/Homebuyers_and_sellers_trend_2025.pdf; not re-verified). NAR's own 2024 highlights article confirms the trend: "convenience to one's job dropped to 34%, from 52% in 2014. The top factors are the quality of the neighborhood and convenience to friends/family" (https://www.nar.realtor/news/economists-outlook/the-top-10-highlights-from-nars-2024-profile-of-home-buyers-and-sellers).
- NAR 2026 cohort data (via Local Logic, 2026-05-05, https://locallogic.co/blog/neighborhood-intelligence-brokerages-2026-nar-report/): for younger millennials (27–35) "commuting costs ranked as the most important environmental factor" (57%); for older millennials "34% cited school district quality and 38% cited school convenience"; for boomers "28–35% named proximity to health facilities". Also: "56% of buyers said finding the right property was the most difficult step, not inventory volume, but neighborhood fit"; "46% of buyers started their home search by looking online for properties".
- Zillow 2026 buyers report (from search summary; page returned 403, https://www.zillow.com/research/buyers-housing-trends-report-2026/): walkable neighborhood 61% very/extremely important; proximity to shopping/services/leisure 53%; sense of community 51%; commute 49% (53% in 2023).
- Zillow 2019: "Almost two-thirds (62%) of employed buyers said their commute to work or school ... was very or extremely important."

Implication: the constraint palette must include **people** (work, a relative), **amenity categories** (grocery, park, transit stop, school, healthcare), **walkability** as a quality-of-place layer, and **budget**, and it must let each household member carry their own commute. Commute has been declining as remote work rises ("About half of buyers said they do at least one day a week" remote, Zillow 2019), which argues for commute being *one card among several* rather than the organising principle of the UI.

### 2.3 The partner's commute

Direct quantitative evidence on two-earner commute trade-offs was not found in the accessible sources (NAR's "61% of buyers are married couples" is the closest; crosscountrymortgage.com summary). The qualitative evidence is strong and consistent:
- "It can also map out multiple locations and see the overlap. It gave me more options than I thought I had." (bkor, HN 36847960)
- "I want to be able to see where's the best place for me and my friend in another city to meet up for lunch" (xbryanx, HN 17679148)
- closemove.com's whole premise is 1–6 people (HN 44965079); hugpoint.io ("Find the fairest meeting spot for a group", https://news.ycombinator.com/item?id=47263280, 2026) is the same need in another domain.
- Walk Score shipped commute-based apartment search in 2011 (https://en.wikipedia.org/wiki/Walk_Score), single-destination; Zillow's 2024 natural-language examples are single-destination ("Homes 30 min drive from Millennium Park"); the Zillow commute-time filter's multi-destination support is **unverified** (page returned 403).

Nobody mainstream does the overlap well. This is a differentiator and must be a first-class object ("Person" with places and modes), not a repeated single-destination filter.

### 2.4 How they use maps today

- They **draw**: Redfin/Sierra's marketing attacks "drawing hard-and-fast boundaries on maps" as friction (https://sierra.ai/customers/redfin), which confirms drawing is the status quo on portals.
- They **measure**: isochrone builders describe replacing manual checks — "Turned 40 minutes real estate searches into 40ms or so" (cridenour, HN 36847960).
- They **discover that distance lies**: "I previously used Mapnificent to choose a house location, and found that many geographically closer properties were often much further in terms of time." (richardw, HN comment 42976908)
- They **distrust point estimates**: "I am more interested in the amount of time I need to budget to travel between two places to be on time 95% of the time" (lotsofpulp, https://news.ycombinator.com/item?id=43392521); "it tells me by car I can get somewhere in < 15 min, but it's always taken me 20..." (jovas, same thread); "is the shading...mean travel time...or...max travel time" (balderdash, same thread); "should have two 'blobs' one for best case and another for worst case traffic wise" (cascom, HN 17679148).
- They want **the tool inside the listing portal**: "I'd love to have such a feature in RightMove or Zillow" (angarg12, HN 17679148); "I've been meaning to make a much more searchable realty system... could compute travel time between points roughly then filter out results more accurately" (matthewfcarlson, HN 43392521).
- They notice **price follows access**: "there seemed to be pockets of higher transit accessibility in certain areas that sometimes corresponded to higher rent prices" (ahmedoo, https://news.ycombinator.com/item?id=46885226).

### 2.5 Why they stop using these tools

From the same threads: accuracy ("The spikes jutting out from my location don't follow the roads or terrain" — codingdave; "It doesn't seem to account for ferry routes" — allannienhuis; places within 45 minutes not inside the 50-minute zone — yawz; all HN 17679148), coverage ("Bicycle mode is only supported in France for the moment"), and the gap to listings (the tool shows a region; the listings live elsewhere). The remark that isochrone maps are "anything but new, but are (IMHO criminally) unpopular. They're extremely helpful when house hunting" (baq, HN 36847960) is the core product insight: the capability exists; the packaging has never been right.

---

## 3. What existing tools got right and wrong

| Tool / feature | Interaction model | Got right | Got wrong / reported failure | Source |
|---|---|---|---|---|
| Isochrone Show HNs (2018 "how far can you go"; 2023 Toronto transit map; 2025 OpenTimes; 2026 howfar.nyc) | Direct manipulation: drop pin, pick time, see blob | Immediate, legible region; users self-report using them to pick where to live | Single origin; no listings; point estimates ("<15 min, but it's always taken me 20"); geometry artefacts; no variance | HN 17679148, 36847960, 43392521, 46885226 |
| Mapnificent / TravelTime walkshed | Multiple markers, time slider | "map out multiple locations and see the overlap"; "geographically closer properties were often much further in terms of time" | Transit-only (Mapnificent); no amenities, no listings | HN 36847960; HN comment 42976908 |
| closemove.com (2025, UK) | Structured form: N people × workplace/budget/max commute → list/map of rentals | Multi-person constraints as the primary input; filters after results | Filters hidden until after results ("I will try to make this more obvious within the UI and allow filters earlier on"); 5 comments, low traction | HN 44965079 |
| Show HN "Map with an LLM" (Dec 2024) | Chat-first; LLM emits places | "Natural language is a much better 'interface' for most of what i want to do with maps" (koopuluri); "wooded hiking trails near [my address]" → "got exactly what I was looking for" (themanmaran) | "absolutely invented data. Same prompt, three times gives 3-4 different results" (onebitwise); "all 5 were misplaced. One field was shown where a train station is" (a10c); "Pins dropping in the ocean" (devbrianwhite); "LLMs are notoriously terrible at spatial thinking" (dr_dshiv) | https://news.ycombinator.com/item?id=42519562 |
| Zillow natural-language search (Sep 2024) | Text box → listings; "ditch search filters" | Mobile-first; typo-tolerant; commute/price/school/POI vocabulary | Reviewer: 1 of 5 "two stories" results was a vacant lot; none of 3 "white kitchen" results had one; "a broken promise"; root cause "The data needed is not in the MLS". Launch coverage never says whether the parsed interpretation is shown back to the user | zillow.mediaroom.com; wavgroup.com; inman.com; nowbam.com |
| Zillow commute time filter | Structured filter | Exists as a dedicated filter (title confirmed) | Multiple destinations? rush hour? **(unverified — page returned 403)** | https://www.zillow.com/news/zillows-commute-time-filter/ |
| Ask Redfin (May 2024) | Chat about one listing | Narrow scope, fair-housing guardrails ("appropriately says that it can't answer the question"), agent handoff; 93% return within a week; 59% of questions about property details | Reviewer (per search summary of a 403 page): everything it said was already in the listing text | https://redfin.com/news/ask-redfin-launches-nationwide; hankbailey.com |
| Redfin conversational search via Sierra (2025–26) | "conversational home search, where the conversation _is_ the interface. There are no filters to configure, no parameters to refine." | Vendor reports "conversational search users view nearly twice as many listings" and are "47% more likely to request a tour" | Vendor metrics on self-selected users; by design removes the visible state a household needs to inspect, negotiate and correct | https://sierra.ai/customers/redfin |
| Airbnb AI search (test Aug 2026, launch Sep 2026) | NL text/voice box **plus** "AI filters that anticipate what the user is looking for"; AI comparisons "appear automatically on any search rather than only inside a chatbot"; opt-in toggle | Chesky: "just adopting a chatbot-like interface won't work for travel use cases"; results "conversational as if you're reading a chatbot, but more visual" | Too new for reception data; rivals (Priceline Penny 2023, Kayak AI Mode, Expedia/Vrbo) shipped chatbots first — their reception **(unverified)** | skift.com; techcrunch.com; pymnts.com |
| Google Maps + Gemini (Oct 2024 →) | Ask in context of a place/area; curated results above "regular results"; shows "the reviews it based its answer on so you can verify the information" | Grounded in the places DB: "there should be no hallucinations on places to stop at or things like that" (Amanda Leicht Moore); sources shown | "Reviews of Mighty Oak" → "cheerfully summarized a Rotten Tomatoes meta review"; in sparse areas it "padded the list with a pizza place and a shawarma spot"; "In places with less map data, I'd double-check its answers before going anywhere" | allthings.how; techlicious.com; androidpolice.com |
| Zillow app inside ChatGPT (Oct 2025) | Chat that can "render a fully interactive UI in the chatbot's responses" | "an interactive map showing options, and users could talk with ChatGPT to learn more about each one" | Refinement is still by talking; no evidence of editable filters inside the widget | techcrunch.com 2025-10-06 |
| Kayak AI Mode, Expedia Romie, Realtor.com / Homes.com AI, Perplexity/ChatGPT maps | — | — | **(unverified in this pass)** | — |

**Pattern across the table.** Every tool that users say they actually used to choose where to live is a map with direct manipulation. Every chat-only tool that touches geography has a documented hallucination or mis-placement story. The two largest consumer companies that shipped recently (Airbnb, Google) both chose a hybrid: natural language in, *structured and visual artefacts out* (filters, pins, sourced reviews), with the regular results still visible underneath.

---

## 4. HCI and design principles that apply

| Principle | Source | One-line implication for us |
|---|---|---|
| Direct manipulation gives "rapid learning, low error rates, and exploratory usage"; agents must remain "transparent and understandable" | Shneiderman & Maes 1997, *Interactions* (https://dl.acm.org/doi/10.1145/267505.267514; wording from search summary) | The region, the constraints, and their effects must be visible objects the user can poke. |
| Mixed initiative: "an elegant coupling of automated services with direct manipulation"; weigh uncertainty about the user's goals; use dialog to resolve key uncertainties; allow efficient direct invocation and termination; minimise the cost of poor guesses | Horvitz 1999, CHI (abstract via https://api.openalex.org/works/doi:10.1145/302979.303030) | The AI proposes constraints and asks only when ambiguity is real ("which Whole Foods?"); every guess is a card the user can delete in one tap. |
| "high levels of human control and high levels of computer automation" are compatible | Shneiderman 2020, https://arxiv.org/abs/2002.04087 | Automate parsing and computing; keep the user in control of the query and the view. |
| Intent-based outcome specification "completely reverses the locus of control", but "half the population in rich countries is not articulate enough to get good results"; the future is "a hybrid user interface" | Nielsen 2023, https://www.nngroup.com/articles/ai-paradigm/ | Accept intent in prose but never depend on it; offer suggestions and controls alongside. |
| Articulation barrier; "A GUI could lessen the users' memory load by favoring recognition over recall"; users "will learn the names and aesthetics they were previously unaware of" by selecting | Mugunthan 2023, https://www.nngroup.com/articles/ai-articulation-barrier/ | Show a palette of constraint types (people, places, amenities, budget) so users recognise what they can ask for. |
| Novices cannot name what they don't know: "You know a problem, but you don't know the best way to describe that problem when you're a novice"; AI interfaces "fail to guide users toward more effective interactions" | Moran 2025, https://www.nngroup.com/articles/ai-information-seeking-keyword-foraging/ | The system proposes the next constraint ("Add your partner's work?") rather than wait for a perfect prompt. |
| Accordion editing / apple picking → users need "compartmentalization of AI responses" and "direct editing" | Gibbons, Mugunthan & Nielsen 2023 (8 participants), https://www.nngroup.com/articles/accordion-editing-apple-picking/ | Each constraint is a separately editable card; never force a re-prompt to change one number. |
| Generative UI caution: "constantly changing UIs will cause usability problems" | Moran & Gibbons 2024, https://www.nngroup.com/articles/generative-ui/ | Generate *content* (cards, layers), not *layout*; the chrome stays fixed. |
| 28% of sites show no applied-filter overview, causing no confirmation, no quick removal, lost context | Baymard, updated 2026-05-13, https://baymard.com/blog/how-to-design-applied-filters | The card rail *is* the applied-filter overview: always on screen, removable, "clear all". |
| Result counts beside filter options are "one of the single highest-impact improvements"; desktop updates instantly, mobile uses a "Show X Results" button | Baymard 2026-04-17, https://baymard.com/blog/ecommerce-filter-ui | Each card shows its effect ("removes 62% of area"; "212 homes inside"); mobile batches edits. |
| Response-time limits 0.1 s / 1 s / 10 s; beyond ~10 s "users should be given feedback indicating when the computer expects to be done" | Nielsen 1993, https://www.nngroup.com/articles/response-times-3-important-limits/ | Precompute what we can; stream per-constraint progress; never a blank spinner. |
| Progressive disclosure: "get the right split between initial and secondary features"; make the path to level two obvious | Nielsen 2006, https://www.nngroup.com/articles/progressive-disclosure/ | Minutes and mode on the card face; rush hour, variance, hard/soft behind "More". |
| Explanations serve transparency, scrutability, trust, effectiveness, persuasiveness, efficiency, satisfaction | Tintarev & Masthoff 2007, https://doi.org/10.1109/icdew.2007.4401070 | "Why is this area out?" must name the constraint *and* let the user change it (scrutability), not merely inform. |
| Users demand intelligibility (why / why-not) selectively, "under specific circumstances" | Lim & Dey 2009, https://dl.acm.org/doi/10.1145/1620545.1620576 | Offer why-excluded on tap of the map, not as always-on clutter. |
| More complete explanations improved mental models; oversimplified ones caused "cognitive strain and diminished trust" | Kulesza et al. 2013, https://doi.org/10.1109/vlhcc.2013.6645235 | Say "Driving from here to Duke at 8 am is 34 min (limit 25)", not "doesn't match". |
| Critiquing-based recommenders: users refine by reacting to results instead of specifying up front | Chen & Pu 2012, https://doi.org/10.1007/s11257-011-9108-6 (abstract not retrievable; 333 citations) | Support "a bit farther is fine" / "tighter" critiques both on cards and in chat. |
| "Good tools make it clear how they should be used. And more importantly, how they should _not_ be used"; avoid the "No man's land where the human is still required to make decisions, but they're not in control of the outcome" | Wattenberger 2023, https://wattenberger.com/thoughts/boo-chatbots | A blank chat box is that no-man's-land; the card rail and palette make capabilities legible. |
| The chatbot "is also the lazy solution" | Appleton, https://maggieappleton.com/lm-sketchbook | Chat is an input, not the product. |
| Generative UI: "move beyond plaintext and markdown chatbots to give LLMs rich, component-based interfaces" | Vercel AI SDK 3.0, 2024-03-01, https://vercel.com/blog/ai-sdk-3-generative-ui | Having the LLM emit typed criteria that render as cards is a solved engineering pattern. |

---

## 5. Recommended interaction model: language builds an editable structured query over a map

### 5.1 One sentence

The user says or types what they want; the system turns it into **criteria cards** (people with places and modes, amenities, budget, quality-of-place) shown in a rail beside the map; every card is a deterministic geospatial operation the user can edit, toggle, or delete; the map shows the resulting region, each card's own layer on demand, and the listings and places inside; the chat box stays available for the next sentence.

### 5.2 The shared state

Everything — chat, cards, map gestures — reads and writes one object:

```
Query {
  people[]:    { name, places[]: { label, resolved_place, mode, max_minutes,
                                   time_of_day, hard|soft } }
  amenities[]: { category | named_place, mode, max_minutes | max_distance, hard|soft }
  budget?:     { max_price | max_rent }
  quality[]:   { walkability >= x, ... }
  region_hint: { metro | bbox }
}
```

The LLM's only job is **NL → Query delta**, plus disambiguation questions and suggestions. Geography is never produced by the model; it comes from the routing/precompute engine applied to places resolved by a gazetteer. This is the direct lesson of the "Map with an LLM" thread — the commenter's advice "JSON structured output lat/long pretty much. Then just plot the coordinates" is the *wrong* lesson, because coordinates from the model are what put pins in the ocean — and it matches the in-house pattern already proven in localUpdates (NL → forced tool use → frozen Pydantic filter → deterministic retrieval; see `00-existing-assets-audit.md`).

### 5.3 First-run flow (the first 30 seconds)

1. **The map is already on screen**, centred on the detected or default metro (Research Triangle). No empty state, no sign-up (closemove: "No sign-up required").
2. **One large input** with a rotating *real* example as placeholder: "Both of us drive to work in under 25 minutes, a 10-minute walk to a park, bikeable to a grocery store". Beneath it, **four tappable starter cards**: "Add a person's work", "Walk to…", "Bike to…", "Budget". This is the recognition-over-recall palette.
3. User types one sentence or taps a starter. **Cards stream in as they are parsed** (one per clause), each immediately computing and drawing its layer; the intersection darkens as cards land. The first visible change should occur within ~1 s (geocode + precomputed grid lookup); the whole sentence within ~10 s with a per-card progress state ("Finding parks… 3 of 4").
4. **Ambiguity is resolved inline, not by failing**: a card for "Whole Foods" renders with a chooser ("3 in this area — which one? [pins]") rather than guessing. "Work" with no address renders a card with the address field focused.
5. **The system proposes the next card** when the query is lopsided: one person with a commute → "Does anyone else commute? [Add person]". This is Horvitz's dialog-to-resolve-uncertainty and Moran's "guide users toward more effective interactions".
6. Result after the first sentence: a shaded region, a one-line summary ("About 14 sq mi across 6 neighborhoods: Old West Durham, …"), and the count of homes inside.

### 5.4 The query-building loop

- **Three equivalent edit paths**: type another sentence ("make the park 15 minutes"); edit the card (minutes stepper, mode toggle, hard/soft switch); or gesture on the map (drag a person's pin; tap a greyed area and choose "allow this"). All three mutate `Query`; map and rail re-render from it. There is no mode switch between "chat mode" and "filter mode".
- **Cards show their effect** (Baymard's result counts): "Removes 62% of remaining area", and on hover the card's own isochrone is highlighted. This answers "which constraint is killing my options?" without the user having to ask.
- **Hard by default, soft on request.** Each card is AND-ed. A card can be flipped to *soft*, which changes its rendering from a hard edge to a graded band (25-minute edge solid; 25–35 minutes as a lighter fringe) and the region to a two-tone fill: "meets all" and "meets all but one soft". Numeric weights are deliberately not exposed in v1 (see §6 and the §7 test that would overturn this).
- **Travel-time honesty on the card**, not in a settings page: "Drive · 8 am weekday · typical" with a "worst case" toggle that redraws using a slower profile. This is the HN "two blobs" request and the OpenTimes 95th-percentile request made concrete; the data behind it is a stream-05 question.
- **Chat doubles as a log of what the system understood.** Each parsed clause is echoed as "Added: Sam drives to Fidelity RTP ≤ 25 min" with the card highlighted. Misparses are therefore visible — the V1 router bug that read minutes as miles would have been obvious to a user in this design.

### 5.5 Result presentation

- **Region first, then named neighborhoods, then listings.** Buyers reason in neighborhoods (NAR: "quality of the neighborhood" 59%; "56% of buyers said finding the right property was the most difficult step… neighborhood fit"), so the polygon is annotated with the named areas it covers and each is a row in a side list with a fit percentage.
- **Polygon with graded fringe, not a heat map, as the default.** A heat map hides the hard constraints and invites "why is this orange?"; a polygon with a soft band keeps the AND semantics legible. Heat rendering is reserved for a single *soft* criterion when the user asks "where is it best for X".
- **Layer toggles** per card (eye icon) and a "show each person's area" view (two translucent colours plus their overlap) — the Mapnificent interaction people already praise.
- **Listings and places inside the region** as pins and a list, with counts on the cards. Pins are real records from a POI store (Overture/OSM) or a listing deep link, never model output.

### 5.6 Correction and refinement

- Any card: edit, mute (eye), delete; undo for the last five changes.
- Any greyed area: tap → "Why is this out?" → the failing constraints listed with actual values ("Sam → RTP at 8 am: 31 min (limit 25)"), each with a one-tap "relax to 31" (Kulesza: complete *and* sound; Tintarev & Masthoff: scrutability).
- Any pin: "Not this one" to swap an ambiguous resolved place.
- In chat: critiques work ("a bit farther is fine", "swap the park for a playground") and are echoed as card changes.

### 5.7 Path to listings without leaving the flow

Given decision 7 (deep links bounded to the region; official/free APIs; no scraping):
- A persistent **"See homes here"** button opens the portal with the region's bounding box (and price filter where the URL scheme accepts it) in a new tab; our map keeps the region so the user can come back and tighten.
- Where a portal accepts a drawn-polygon URL (to be confirmed in stream 04), pass the simplified polygon; otherwise bbox plus a copyable "paste this boundary" hint.
- Listings the user is considering are pinned back onto our map (paste a URL or address) so region and shortlist live together. This answers the "I'd love to have such a feature in RightMove or Zillow" request from the other side.

### 5.8 Explainability summary

Three levels, progressively disclosed: (a) the card rail itself — what is applied; (b) per-card effect and layer highlight — what each does; (c) tap-anywhere "why out" with actual values and one-tap relax — why this specific place fails. No free-text "AI explanation" of the region: explanation text is templated from the engine's numbers, which keeps it sound.

### 5.9 Wireframes

**A. First run (desktop)**

```
+--------------------------------------------------------------------------+
| LocationFinder                                   Research Triangle, NC ▾ |
+----------------------------+---------------------------------------------+
| Describe where you want    |                                             |
| to live                    |                                             |
| +------------------------+ |                                             |
| | Both of us drive to    | |              [ map, metro view ]            |
| | work in under 25 min,  | |                                             |
| | 10-min walk to a park… | |                                             |
| +------------------------+ |                                             |
|  [Add a person's work]     |                                             |
|  [Walk to…]  [Bike to…]    |                                             |
|  [Budget]                  |                                             |
|                            |                                             |
| Try: "near my sister in    |                                             |
| Carrboro, 30 min to RDU"   |                                             |
+----------------------------+---------------------------------------------+
```

**B. Query-building loop (desktop, after one sentence)**

```
+--------------------------------------------------------------------------+
| ▸ Understood: 2 people, 1 park, 1 grocery.  Add anything?  [__________] |
+----------------------------+---------------------------------------------+
| CRITERIA            clear  |   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   |
| ┌────────────────────────┐ |   ░░░░░░░▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░   |
| │👤 You → UNC Hospitals  │ |   ░░░░▓▓▓▓███████████▓▓▓░░░░░░░░░░░░░░░░   |
| │ 🚗 ≤ 25 min  8am  HARD │ |   ░░░▓▓▓███████████████▓▓░  ● Durham      |
| │ removes 48%  👁  ✎  ✕  │ |   ░░░░▓▓▓███████████▓▓▓░░░░░░░░░░░░░░░░   |
| ├────────────────────────┤ |   ░░░░░░░▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░   |
| │👤 Sam → Fidelity RTP   │ |   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   |
| │ 🚗 ≤ 25 min  8am  HARD │ |   █ meets all   ▓ misses one SOFT          |
| │ removes 31%  👁  ✎  ✕  │ |   [show each person] [worst-case traffic]   |
| ├────────────────────────┤ |                                             |
| │🌳 Park  🚶 ≤ 10 min    │ |  tap any grey area → "Why is this out?"     |
| │ SOFT removes 22% 👁 ✎ ✕│ |  ┌───────────────────────────────────────┐ |
| ├────────────────────────┤ |  │ Hope Valley: Sam → RTP 8am = 31 min   │ |
| │🛒 Grocery 🚲 ≤ 12 min  │ |  │ (limit 25)      [relax to 31] [close] │ |
| │ HARD removes 9%  👁 ✎ ✕│ |  └───────────────────────────────────────┘ |
| └────────────────────────┘ |                                             |
| + Add person  + Add place  |  14 sq mi · 6 neighborhoods · 212 homes     |
| Suggest: airport? budget?  |  [See homes here ↗]  [Places inside ▾]      |
+----------------------------+---------------------------------------------+
```

**C. Mobile result → listings**

```
+------------------------------+
| ◂  Where to live        ⋯    |
|  [map: region, 2 pins]       |
|  ████████▓▓                  |
|  ██████████▓▓   ● Durham     |
|  ████████▓▓                  |
|------------------------------|
| 14 sq mi · 6 neighborhoods   |
| [See 212 homes ↗]            |
|------------------------------|
| ⟵ You→UNC 25m | Sam→RTP 25m  |
|   Park 🚶10m | Grocery 🚲12m ⟶ |
|  (chips scroll; tap to edit) |
|------------------------------|
| Old West Durham   91% fits ▸ |
| Watts-Hillandale  78% fits ▸ |
| Lakewood          64% fits ▸ |
|------------------------------|
| [ Add or change…        🎤 ] |
+------------------------------+
```

On mobile, card edits batch behind a "Show results" button (Baymard's mobile pattern) and the chip rail is the always-visible applied-filter overview; voice input is offered because Airbnb and Zillow both lead with mobile and Airbnb ships "text or voice".

### 5.10 Answers to the brief's specific design questions

| Question | Answer | Basis |
|---|---|---|
| Hard (AND) or weighted scores, or both? | Hard AND by default; per-card *soft* flag renders a graded fringe; no numeric weights in v1 | Users state limits ("choose two", 30-minute max); critiquing beats up-front weighting (Chen & Pu); heat maps are hard to explain |
| Region vs ranked neighborhoods vs listings? | All three, layered: region (primary), named neighborhoods with fit %, listings/places inside | NAR "neighborhood fit" is the hard step; isochrone users want the region; everyone wants listings next |
| How to make the user trust the result? | Visible card rail; per-card layer toggle and effect; tap-to-explain with real numbers and one-tap relax; sourced pins only | Baymard applied-filters; Kulesza completeness; Google Maps "show the reviews it based its answer on" |
| Two-person household input? | "Person" is a first-class object with its own places/modes; "show each person" view colours the two areas and their overlap | bkor/Mapnificent overlap; closemove 1–6 people; hugpoint |
| Region → listings without leaving? | Persistent "See homes here" deep link bounded to the region; shortlist pinned back onto our map | Decision 7; angarg12 "feature in RightMove or Zillow" |
| First 30 seconds? | Map already visible; one sentence or one starter tap; cards stream in with progress; first region in ≤10 s; system suggests the second person | Nielsen 10-s limit; articulation barrier; Horvitz dialog |

---

## 6. Alternatives considered and why they lost

**(1) Chat-first; conversation is the whole UI (Redfin/Sierra, early Priceline/Kayak).**
Lost because: (a) non-technical users hit the articulation barrier and the blank-box problem (Nielsen; Wattenberger); (b) geography is where LLMs demonstrably fail in public — invented places, non-deterministic results, misplaced pins (HN 42519562) — and a transcript gives the user no way to see which constraint was misunderstood; (c) correction means re-prompting whole outputs, which NN/G found users dislike (accordion editing); (d) Sierra's own description — "There are no filters to configure, no parameters to refine" — removes exactly the state a two-person household needs to negotiate over; (e) Airbnb, the most-watched travel UX team, said "just adopting a chatbot-like interface won't work for travel use cases." Chat survives in our design as the fastest *input* and as the explanation log.

**(3) Structured form/map with AI only assisting (V1, closemove, Zillow's commute filter).**
Lost because: (a) it is what we had and it was judged clunky; (b) Baymard's finding that most filtering UIs are mediocre-to-poor shows the form-first bar is hard to clear; (c) it puts the full articulation burden on the user before any result appears — closemove's author had to promise to "allow filters earlier on" after users could not find them; (d) multi-person × multi-mode × multi-amenity queries make the form combinatorially long, which *is* the clunkiness. Its strengths — visible state, direct manipulation, deterministic computation — are kept wholesale in the hybrid.

**Heat-map scoring as the primary output.** Lost as default because users state constraints as hard limits and "why is this orange?" has no crisp answer; kept as an optional view for a single soft criterion.

**Ranked neighborhood list as the primary output.** Lost as default because the region is the differentiator and a list hides overlap and shape; kept as the second layer (named areas inside the region with fit %), since buyers reason in named neighborhoods.

**Numeric weight sliders / pairwise preference elicitation.** Deferred: no evidence in the accessible sources that non-technical home-seekers want to weight criteria numerically; hard/soft toggles plus "relax to N" critiques cover the observed behaviour. The §7 test can overturn this.

**Generated layout ("generative UI" proper).** Rejected: NN/G's warning that "constantly changing UIs will cause usability problems". We generate card *content*; the chrome is fixed.

---

## 7. Design risks and how to test them cheaply with friends and family

**Risks**
1. The LLM misparses (units, mode, which person) and users don't notice despite the cards. Mitigation: echo line + card highlight. Test task 5.
2. Users don't understand the soft band / two-tone fill. Test task 2.
3. Latency over 10 s with no visible progress makes it feel broken, as V1 did. Instrument per-card timing. Test task 1.
4. Place disambiguation interrupts flow, or is skipped and silently wrong. Test task 3.
5. The handoff to a listing portal feels like leaving; users don't come back to tighten. Test task 6.
6. Two-person input is modelled in users' heads as two separate commute filters, not as people. Test task 1; listen to vocabulary.
7. The mobile card rail is ignored; users only talk. Test task 7.

**Usability test script** (6 participants, 30–40 min each, think-aloud, screen-recorded; recruit couples where possible; at least 3 participants who do not work in tech)

Warm-up (2 min): "Tell me about the last time you looked for a place to live. How did you decide which areas to look in?" Note the words they use (minutes, miles, neighborhood names, "near").

- **Task 1 — Cold start, two commutes.** "Imagine you just took a job at [local hospital] and your partner works at [local employer]. Find where you could live so you both drive under 25 minutes." Measure: time to first region; typed, tapped a starter, or hesitated; created two *people* or two commutes; looked at the cards while waiting.
- **Task 2 — Soft constraint.** "You'd like to be able to walk to a park in about 10 minutes, but it's not essential." Measure: found the hard/soft switch; can explain in their own words what the lighter band means; trusts it.
- **Task 3 — Ambiguity.** "You want to be within a 10-minute bike ride of Whole Foods." Measure: noticed there are several; resolved or assumed; reaction to the chooser.
- **Task 4 — Why excluded.** "Your friend lives in [neighborhood just outside the region]. Find out why it isn't included, and change the search so it is." Measure: found tap-to-explain; used "relax to N", edited the card, or typed; explanation understood.
- **Task 5 — Catching a misparse (seeded).** The system deliberately parses "20 minutes to the airport" as 20 miles. Measure: noticed from the echo/card; how fixed (card vs chat); time to fix.
- **Task 6 — To listings and back.** "See actual homes for sale in this area, then come back and make the search stricter." Measure: found "See homes here"; bounds carried correctly into the portal; returned and continued.
- **Task 7 — Mobile repeat.** Repeat Task 1 on their own phone. Measure: chips vs voice vs typing; batch "Show results" understood.

After each task: Single Ease Question (1–7). At the end: "Would you use this the next time you move? What would you tell your partner it does?" and a trust rating 1–7 for "I believe the shaded area is right."

Success criteria to proceed: ≥5/6 complete Tasks 1, 4 and 6 unaided; median SEQ ≥ 5; every participant can state in their own words what one card means. Signals to change course: any participant who never touches a card in Tasks 2–5 (make cards more prominent, or shift toward chat); any participant asking "how much more important is X than Y" (prototype weights); any participant who trusts a visibly wrong region in Task 5 (strengthen the echo).

---

## 8. Open questions

1. **Reddit evidence is missing.** Can the owner, or a later pass with a different fetcher, read r/FirstTimeHomeBuyer and r/RealEstate threads on two-commute trade-offs and the Zillow draw tool to confirm the vocabulary and threshold findings?
2. **Does Zillow's commute filter support multiple destinations and rush hour?** (unverified; page returned 403.) If it does both, our differentiation shifts further toward amenities + people + explainability.
3. **Which portal URL schemes accept a bbox or polygon** (stream 04)? This decides whether §5.7 is a one-click handoff or copy-paste.
4. **Soft-criteria rendering**: two-tone fill vs graded fringe vs count-of-misses — needs the §7 test before committing.
5. **Voice as first input on mobile**: worth the complexity for friends and family, or a v2 item?
6. **Should the LLM propose criteria the user did not mention** (e.g., school convenience for a given cohort)? Horvitz says yes when the cost of a poor guess is low; fair-housing rules (Ask Redfin "appropriately says that it can't answer the question") bound what may be suggested about neighborhoods.
7. **Travel-time variance source**: the "worst case" toggle needs either a slower precomputed profile or traffic data (stream 05); the UI promise must not outrun the data.
8. **Reception of Kayak AI Mode, Expedia Romie, Realtor.com and Homes.com AI** (unverified): a short follow-up could confirm or refute the "hybrid is where everyone is landing" claim with travel-industry data.

---

## 9. Sources (all accessed 2026-11-03)

**Surveys and reports**
- Zillow Research, "Buyers: Results from the Consumer Housing Trends Report 2026" — https://www.zillow.com/research/buyers-housing-trends-report-2026/ (403; figures from search summary)
- Zillow press release, "The Major Role Work-Life Balance Plays in Decisions About Home", 2020-02-13 — https://zillow.mediaroom.com/2020-02-13-The-Major-Role-Work-Life-Balance-Plays-in-Decisions-About-Home
- Chicago Agent Magazine, "The commute factor: Why it's become the ultimate deal breaker for buyers", 2020-02-14 — https://chicagoagentmagazine.com/2020/02/14/the-commute-factor-why-its-become-the-ultimate-deal-breaker-for-buyers/
- NAR, "The Top 10 Highlights from NAR's 2024 Profile of Home Buyers and Sellers" — https://www.nar.realtor/news/economists-outlook/the-top-10-highlights-from-nars-2024-profile-of-home-buyers-and-sellers
- CrossCountry Mortgage, "NAR Profile of Home Buyers and Sellers 2025" (summary) — https://crosscountrymortgage.com/mortgage/resources/nar-profile-home-buyers-sellers-2025/
- Rhode Island Realtors mirror, "2025 Profile of Home Buyers and Sellers" (PDF) — https://www.rirealtors.org/clientuploads/documents/NAR/Homebuyers_and_sellers_trend_2025.pdf (affordability 35% from search summary)
- Local Logic, "Neighborhood intelligence for brokerages: what the 2026 NAR data reveals", 2026-05-05 — https://locallogic.co/blog/neighborhood-intelligence-brokerages-2026-nar-report/
- Wikipedia, "Walk Score" — https://en.wikipedia.org/wiki/Walk_Score

**Forum threads (Hacker News)**
- Show HN: A map that shows you how far you can go for a given time or distance (2018) — https://news.ycombinator.com/item?id=17679148
- Show HN: I built a transit travel time map (2023) — https://news.ycombinator.com/item?id=36847960
- Show HN: Map with an LLM (2024) — https://news.ycombinator.com/item?id=42519562
- Show HN: OpenTimes – Free travel times between U.S. Census geographies (2025) — https://news.ycombinator.com/item?id=43392521
- Show HN: AI agent finds homes (2025; 2 comments) — https://news.ycombinator.com/item?id=43465520
- Show HN: Tool shows UK properties matching group commute/time preferences (closemove.com, 2025) — https://news.ycombinator.com/item?id=44965079
- Show HN: howfar.nyc (2026) — https://news.ycombinator.com/item?id=46885226
- Show HN: hugpoint.io – Find the fairest meeting spot for a group (2026) — https://news.ycombinator.com/item?id=47263280
- HN comments mentioning Mapnificent (richardw 42976908; informalo 32278016; factorymoo 36855810) — https://hn.algolia.com/api/v1/search?query=Mapnificent
- Mapnificent — https://www.mapnificent.net/

**Vendor announcements and coverage**
- Zillow press release, "Zillow's AI-powered home search gets smarter with new natural language features", 2024-09-04 — https://zillow.mediaroom.com/2024-09-04-Zillows-AI-powered-home-search-gets-smarter-with-new-natural-language-features
- HousingWire, "Zillow enhances AI search abilities", 2024-09-04 — https://www.housingwire.com/articles/zillow-artificial-intelligence-search/
- Inman, "Zillow, Unfiltered", 2024-09-04 — https://www.inman.com/2024/09/04/zillow-unfiltered-portal-giant-adds-ai-fueled-natural-language-feature/
- BAM, "Goodbye to Filters? Zillow's AI-Powered Home Search Is Smarter than Ever", 2024-09-07 — https://nowbam.com/goodbye-to-filters-zillows-ai-powered-home-search-is-smarter-than-ever/
- WAV Group, "REAL AI: Zillow's AI stumble", 2024-09-06 — https://www.wavgroup.com/2024/09/06/real-ai-zillow-ai-stumbles/
- Zillow Front Porch, "Discover your perfect commute with Zillow's commute time filter" — https://www.zillow.com/news/zillows-commute-time-filter/ (403; title only)
- Redfin, "Ask Redfin Launches Nationwide", 2024-05-02 — https://redfin.com/news/ask-redfin-launches-nationwide
- Sendbird case study, "Redfin" — https://sendbird.com/resources/redfin
- Sierra, "Redfin" customer page — https://sierra.ai/customers/redfin
- Hank Bailey, "Ask Redfin, Ask Zillow — What AI Can (and Can't) Tell You About a Home", 2026-02-10 — https://www.hankbailey.com/blog/2026/02/10/ask-redfin-ask-zillow-what-ai-can-and-cant-tell-you-about-a-home/ (403; from search summary)
- Skift, "Airbnb Launches AI Tools, Catching Up to OTA Rivals", 2026-09-30 — https://skift.com/2026/09/30/airbnb-launches-ai-tools-catching-up-to-ota-rivals/
- TechCrunch, "Airbnb says AI is helping it ship features faster as it tests a new search function", 2026-08-07 — https://techcrunch.com/2026/08/07/airbnb-says-ai-is-helping-it-ship-features-faster-as-it-tests-a-new-search-function/
- PYMNTS, "Airbnb Tests AI Search After Automating 45% of Support", 2026-08-20 — https://www.pymnts.com/news/artificial-intelligence/2026/airbnb-is-weaving-ai-into-every-step-of-a-trip/
- TechCrunch, "Google Maps is getting new AI features powered by Gemini", 2024-10-31 — https://techcrunch.com/2024/10/31/google-maps-is-getting-new-ai-features-powered-by-gemini
- AllThings.how, "Ask Maps in Google Maps uses Gemini to give you spot and activity ideas", 2024-11-04 — https://allthings.how/ask-maps-in-google-maps-uses-gemini-to-give-you-spot-and-activity-ideas/
- Techlicious, "Google Maps Gets Chatty with Gemini AI Integration", 2025-11-05 — https://www.techlicious.com/blog/google-integrates-gemini-ai-into-google-maps/
- Android Police, "This Gemini Map feature solved my biggest search frustration in seconds", 2026-10-11 — https://www.androidpolice.com/gemini-map-feature-solved-biggest-search-frustration/
- TechCrunch, "OpenAI launches apps inside of ChatGPT", 2025-10-06 — https://techcrunch.com/2025/10/06/openai-launches-apps-inside-of-chatgpt/
- Vercel, "AI SDK 3.0 with Generative UI support", 2024-03-01 — https://vercel.com/blog/ai-sdk-3-generative-ui

**HCI and design research**
- Shneiderman & Maes, "Direct manipulation vs. interface agents", *Interactions* 4(6), 1997 — https://dl.acm.org/doi/10.1145/267505.267514 (metadata via https://api.openalex.org/works/doi:10.1145/267505.267514; PDF at https://www.cs.umd.edu/~ben/papers/Maes1997Intelligent.pdf could not be text-extracted)
- Horvitz, "Principles of Mixed-Initiative User Interfaces", CHI 1999 — https://dl.acm.org/doi/10.1145/302979.303030 (abstract via https://api.openalex.org/works/doi:10.1145/302979.303030)
- Shneiderman, "Human-Centered Artificial Intelligence: Reliable, Safe & Trustworthy", 2020 — https://arxiv.org/abs/2002.04087
- Nielsen, "AI: First New UI Paradigm in 60 Years", NN/G, 2023-06-18 — https://www.nngroup.com/articles/ai-paradigm/
- Mugunthan, "Overcoming the Articulation Barrier in Generative AI Using Hybrid Interfaces", NN/G, 2023-08-13 — https://www.nngroup.com/articles/ai-articulation-barrier/
- Gibbons, Mugunthan & Nielsen, "Accordion Editing and Apple Picking: Early Generative-AI User Behaviors", NN/G, 2023-09-24 — https://www.nngroup.com/articles/accordion-editing-apple-picking/
- Moran & Gibbons, "Generative UI and Outcome-Oriented Design", NN/G, 2024-03-22 — https://www.nngroup.com/articles/generative-ui/
- Moran, "How AI Succeeds (and Fails) to Help People Find Information", NN/G, 2025-08-22 — https://www.nngroup.com/articles/ai-information-seeking-keyword-foraging/
- Nielsen, "Response Times: The 3 Important Limits", 1993 — https://www.nngroup.com/articles/response-times-3-important-limits/
- Nielsen, "Progressive Disclosure", 2006-12-03 — https://www.nngroup.com/articles/progressive-disclosure/
- Baymard, "Filtering UX: Display 'Applied Filters' in an Overview", 2020-10-06, updated 2026-05-13 — https://baymard.com/blog/how-to-design-applied-filters
- Baymard, "What Is an Ecommerce Filter? UI Best Practices", 2026-04-17 — https://baymard.com/blog/ecommerce-filter-ui
- Wattenberger, "Why Chatbots Are Not the Future" (2023) — https://wattenberger.com/thoughts/boo-chatbots
- Appleton, "Language Model Sketchbook, or Why I Hate Chatbots" — https://maggieappleton.com/lm-sketchbook
- Tintarev & Masthoff, "A Survey of Explanations in Recommender Systems", ICDE Workshops 2007 — https://doi.org/10.1109/icdew.2007.4401070
- Lim & Dey, "Assessing demand for intelligibility in context-aware applications", UbiComp 2009 — https://dl.acm.org/doi/10.1145/1620545.1620576 (abstract via https://api.openalex.org/works/doi:10.1145/1620545.1620576)
- Kulesza, Stumpf, Burnett, Yang, Kwan & Wong, "Too much, too little, or just right? Ways explanations impact end users' mental models", VL/HCC 2013 — https://doi.org/10.1109/vlhcc.2013.6645235
- Chen & Pu, "Critiquing-based recommenders: survey and emerging trends", UMUAI 2012 — https://doi.org/10.1007/s11257-011-9108-6 (abstract not retrievable; cited for the critiquing paradigm)
