# Per-region research brief

Template for delegating research on a shortlisted stop. Fill the brackets.

The point of the shape below is that it forces the **three-state status** back out of the
agent. A brief that just asks "what's good in X" returns uniform confidence, and then you
cannot tell a confirmed opening time from a guess.

---

Research **[REGION]** as a **[overnight stop / layover base / charging-and-meal stop]** on
**[WEEKDAY DATE]**. Today is **[TODAY]**.

**Context.** [Party: who, ages.] They arrive about **[TIME]** with **[N]** hours before
**[sunset / last entry / departure]**, and leave **[WHEN]**. [One line on why this region made
the shortlist, and the one thing that would disqualify it.]

**Find, in priority order:**

1. **[The single highest-value unknown — the thing that decides this region.]**
2. What is actually open and worth doing in the arrival window. For each: what it is, why it
   suits this party, cost for the whole party, and **closing time**.
3. [Lodging / logistics], with the binding amenity named explicitly.
4. Food that works at the hour they will want it.
5. Anything date-specific that weekend — events, closures, seasonal programmes, local traffic.

**Rules — these are the output contract, not advice:**

- **Label every claim** as one of: **confirmed for [DATE]** / **standing hours, date not
  checked** / **could not determine**. Never let the third render as the first.
- Cite a URL for every substantive claim; prefer the operator's own page.
- **Do not invent prices, hours or events. "Not published" is a valuable finding** — report it
  as a finding, not a gap to fill.
- Report pages that 403, time out or render client-side, and say which claims that leaves
  unverified.
- Flag contradictions between sources rather than silently picking one. Aggregators disagree
  constantly on binary amenities; a rebrand makes the widely-repeated answer stale.
- If something in the context looks wrong (a date already past, a venue closed), say so rather
  than answering around it.

**Return** a tight markdown report: what is open with times and costs, what is closed and why,
lodging, food, and a closing **"could not determine"** list with the calls worth making.

---

## When the brief comes back

Do not paste it through. Three checks first:

1. **Re-measure any number it gives you.** A research agent returned 5h44 for a leg measured at
   4h42, and called a +1h22 detour "not really a detour". Both went into a draft.
2. **Check its figures came from your instrument**, not a travel-time website it happened to
   find. A second engine in your table is a bug.
3. **Carry the status labels forward.** The commonest way this work degrades is a caveat
   recorded here and dropped in the summary.
4. **Spot-check that the citations exist and say what is claimed.** Open two or three. A
   research pass in testing **fabricated an entire region's lodging, food and events from
   memory and attached invented citations**. It read as the most confident section in the
   batch. Re-measuring numbers cannot catch this — a fabricated source survives every check
   except opening it.

   If you find one, do not patch the bad claims: **discard that whole pass** and re-run or
   mark the region unresearched. A source that invented one section invented at whatever rate,
   and you cannot tell which half is real. Say so in the output.

5. **Verify the claimed *failures* too, not only the claimed findings.** The same testing run
   produced the nastier version: an agent dispatched three subagents, never read their output,
   and wrote their sections from memory — **inventing the evidence of having checked**, including
   a fabricated HTTP 403 `Retry-After` header and invented 429 counts. All three subagent output
   files were 0 bytes.

   This is a hazard these very rules create. A brief that rewards "report what 403'd" gives an
   agent a template for sounding rigorous without doing the work, because **a plausible failure
   is cheaper to invent than a plausible fact and is almost never checked.** If a pass reports
   blocked sources, confirm the blocks are real — an empty output file, a tool-call count of
   zero, or a suspiciously tidy error are the tells.
