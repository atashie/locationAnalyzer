---
name: feedback-a-dropped-stop-is-a-new-measurement
description: Taking a stop off an itinerary changes the legs either side, the detour, the arrival, the daylight and the cost at once, so measure the variant as its own option; and merging one fresh measurement beside committed ones is only honest if the shared legs and the direct baseline come back identical
metadata:
  type: feedback
---

Learned 2026-11-15, adding a "chosen day" tab to the Chapel Hill → Thomasville page.

The traveller picked the coastal option built around Fort McAllister and then dropped the fort
itself: it sits 14 minutes past the lunch places, where the boys are out of the car anyway. The
tempting edit is to subtract the fort's 105 minutes from that option's row and move on.

**Why that is wrong:** six figures move, not one. The two legs either side of the gap collapse
into a single different leg (869 s + 3977 s became 3299 s — the drive back out of the spur
disappears), so the total, the detour against the direct route, the arrival clock, whether
arrival is before sunset, the door-to-door elapsed and the admissions total all change together.
Here that turned 18:12 after dark into 16:01 with 1h34 of daylight, and +50 min of added driving
into +24. A hand-adjusted row would have kept the old arrival and reported a day that does not
exist. This is the skill's rule 2, and dropping a stop is its sharpest case.

**How to apply:** define the variant as its own option in the spec and route it. Then, if you
cannot re-measure the whole spec (no route cache on this machine, and re-running would rewrite
nine committed options for no reason), measure the one option on its own through the same tool
and merge it — but only after two checks pass:

- the **direct baseline** matches the committed one (39 ms apart on 8h42 here, 1.2 ppm);
- the **legs the variant shares** with the option it came from match to the millisecond.

Those two together say the instrument has not moved, which is what makes one table out of two
runs legitimate. Recompute the merged option's detour against the *committed* baseline, so every
"added" figure on the page is measured from one origin. If either check fails, the merge is not
available: re-measure everything and say so. See [[feedback-provenance-is-not-correctness]] and
[[feedback-a-published-page-must-name-its-source]].

A second, smaller lesson from the same change: when you add a tab to a generated page, the old
view's script starts matching the new view's markup. The option switcher queried `.route`,
`.markers` and `.tl` document-wide, and the chosen-day tab draws all three — selecting any option
hid them. Scope such queries to the panel they belong to.
