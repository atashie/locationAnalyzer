# The walk: `band15min_pass-03`

> **UPDATE 2026-11-17 — the main question has been answered, so this walk is now worth much less.**
> The owner confirmed the dirt tracks are walkable: *"Yes those dirt-tracks exist and they are
> walkable; your estimates are correct."* That settles the dispute this walk existed to settle, and
> it settles it in the model's favour.
>
> **What is left is the stopwatch.** The record still holds no timed observation, so the 14-minute
> figure itself remains unverified even though the route is now known to be legitimate. That is
> worth having eventually and is no longer urgent. **Do not make a special trip for it.**

Everything else we have built compares the product to itself. This is the one check that consults
the world, and the record held **no admissible observation** — the journey was walked once, on
2026-11-10, but nothing about it was recorded that could confirm or refute our number.

Carrboro / Chapel Hill. About 15 minutes each way if we are right, about 25 if the earlier report
was.

---

## Where to start

**35.902334, -79.062476**

<https://www.openstreetmap.org/#map=18/35.90233/-79.06248>

That is the centre of published cell `row 286, col 129`. The cell is roughly 100 m square and holds
**2 buildings**, so **any door within about 70 m of that pin is inside the cell** and counts. Pick
whichever door you would actually leave from, and **write down which one** — that is the single
most important thing missing from the record.

## Where to walk to

**Hill's Family Asian Markets — 35.910405, -79.065417**

<https://www.openstreetmap.org/?mlat=35.910405&mlon=-79.065417#map=18/35.910405/-79.065417>

This is **our** prediction, not your choice. The point of the exercise is to check *our* answer, so
please walk to this shop even if you would normally go somewhere else. If it turns out to be closed
or not to exist, that is itself a finding worth more than the timing.

## What the product claims

| | |
|---|---|
| Travel time | **810.8 s** |
| Shown on the page as | **14 min** |
| At a 15-minute limit | **PASS** |
| At a 10-minute limit | FAIL |
| Route flag | **restricted** — our route uses private ground |

## The route, in words

Head **north**. Our route leaves the start, joins a **dirt track about 100 m south-east of the
start pin**, and follows it north for **305 m** before rejoining ordinary streets and continuing to
the shop.

**You do not have to walk our route.** Walk the way you actually would. The whole question is
whether our route is one a person would take, so following it on purpose would answer the wrong
question. Just note afterwards whether you ended up on the track.

## The specific thing in dispute

**OSM way `1254722641`** — <https://www.openstreetmap.org/way/1254722641>

It runs roughly south-to-north between these two points:

| | |
|---|---|
| south end | **35.901422, -79.063358** — <https://www.openstreetmap.org/#map=18/35.90142/-79.06336> |
| north end | **35.904659, -79.062387** — <https://www.openstreetmap.org/#map=18/35.90466/-79.06239> |

Its south end is about **100 m from the start pin**, which is why our route finds it immediately.

**What OSM says it is:**

```
highway       = track
access        = private
motor_vehicle = no
surface       = dirt
tracktype     = grade4      (soft; soil, sand or grass, no hard surface)
```

That way is why we say 14 minutes. A route to the same shop avoiding it is **2,139.9 m
(1.33 miles) and 25.55 minutes** — which matches your earlier report of "1.3 miles, closer to 25
minutes" almost exactly.

So the walk settles a narrow, answerable question: **is that dirt track something a household
would actually walk?**

- If it is an ordinary-looking path with nothing stopping you, our 14 minutes is defensible and we
  are over-reading the `access=private` tag.
- If it is gated, fenced, signed, somebody's land, or simply not there on the ground, our
  14 minutes is wrong and the 25-minute route is the real one.

**A second thing worth noticing while you are on it.** `surface=dirt` and `tracktype=grade4` mean a
soft, unsurfaced track. **Our model walks every way at the same speed**, so even if you are
perfectly entitled to use it, we may be too fast on it — and in wet weather it may not be walkable
at all. That is a separate defect from the access question and nothing has ever measured it. If the
going is noticeably slower than pavement, say so.

---

## What to record

Five things. The first four are what make the record admissible; the fifth is the one that settles
the dispute above.

1. **The door you left from** — a dropped pin, or a house number.
2. **A stopwatch time**, start to shop door. Not an estimate. If you stop for a crossing or a
   phone call, note it.
3. **Which shop you actually reached** — confirm it was Hill's Family Asian Markets, and whether
   it was open.
4. **The route you took** — a GPS trace if your phone will give one, otherwise a rough description
   of the streets.
5. **Did you use the private stretch?** Yes / no / did not notice. If yes: was there a gate, a
   sign, a fence, or anything suggesting you should not be there?

Anything you noticed that the map would not show is worth a line — a missing pavement, an
unsignalled crossing of a busy road, a dog.

## Where it goes

Row `band15min_pass-03` of
[`triangle-grocery-walk-chapelhill-with-destinations.csv`](triangle-grocery-walk-chapelhill-with-destinations.csv).
The columns are already there and currently hold the 2026-11-10 report:

```
walked = yes
walked_seconds = 1500          <- "about 25 min" taken at face value
duration_timed = no            <- this is the problem
witness_within_10min = no
witness_within_15min = no
unresolved = which shop was reached; whether the private approach was used; the start door
```

Fill in `start_lon`, `start_lat`, `door_offset_m`, `destination_used`, `destination_open`,
`route_usable`, `route_followed`, `walked_seconds`, and set `duration_timed = yes`. Or just send me
the five things above in a message and I will fill the sheet in.

---

## One caveat, so the result is not over-read

A slow walk **confirms** a FAIL but cannot by itself **refute** a PASS. Our claim is that *some*
15-minute journey exists from that cell, not that every journey is 15 minutes. If you walk it in 25
minutes by the public route, that tells us our route used ground you would not use — which is
exactly the finding we want — but it does not prove no 15-minute route exists.

That is why item 5 on the list matters most. The timing is evidence; the private stretch is the
answer.
