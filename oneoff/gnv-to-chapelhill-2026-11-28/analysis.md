# Gainesville FL → Chapel Hill NC, overnight stop Sat 28 Nov 2026

One-off trip analysis. Self-contained; not part of the Distance Finder app.

**Party:** 2 adults + boys aged 6 and 9.
**Saturday 28 Nov 2026:** drive north, arrive mid/late afternoon, one short exploration, overnight.
**Sunday 29 Nov 2026:** finish the drive to Chapel Hill.

**Owner constraints (confirmed):** mid-morning departure; up to ~45 min total detour off
the fastest route; all activity types in play (hands-on museum, outdoor walk, historic
downtown + lights, zoo/animals); lodging type and budget open — pick the best stop first.

---

## Method

Drive times come from the public Valhalla routing server (`valhalla1.openstreetmap.de`),
the same engine the main app uses for isochrones. For each of 38 candidate stops I routed
`Gainesville → stop → Chapel Hill` as a single three-point request, which yields both legs
and the exact detour penalty against the unconstrained fastest route.

Two caveats that bound every number below:

- **Free-flow only.** Valhalla has no traffic model here. Thanksgiving weekend will be
  worse than these times, and unevenly so — see the I-95 section.
- **The matrix endpoint was unusable.** The public server caps `sources_to_targets` path
  distance at 150 km, so per-candidate `/route` calls were the only option. Noted because
  it is a real constraint on the main app's routing options too.

Sunset is computed with the NOAA solar-position algorithm at each candidate's coordinates
for 2026-11-28 (`scripts/daylight.py`), not looked up. Arrival assumes a 09:30 EST
departure plus 18% overhead for fuel, lunch and bathroom stops with young kids.

Reproduce with:

```bash
python scripts/route_scan.py   # -> data/corridors.json, data/candidates.json
python scripts/daylight.py     # -> data/daylight.json
```

---

## 1. The corridor question: there is effectively one route

The fastest route is **530.8 mi / 8.31 h**. I forced Valhalla through the via-points that
define each recognisably different way of making this drive. The result is lopsided:

| Corridor | Miles | Hours | Penalty |
|---|---:|---:|---:|
| Fastest (unconstrained) | 530.8 | 8.31 | — |
| I-95 via Jax / Savannah / Florence / Fayetteville | 548.1 | 8.95 | +0:38 |
| I-95 then US-301 inland via Orangeburg / Columbia | 605.2 | 9.65 | +1:20 |
| US-301 Florida bypass of Jacksonville | 578.0 | 10.14 | +1:50 |
| Coastal detour via Charleston | 613.8 | 10.22 | +1:55 |
| I-75 inland via Macon / Augusta / Columbia | 688.7 | 11.09 | +2:47 |
| I-75 to Macon, then I-16 to Savannah | 764.5 | 11.93 | +3:37 |

**Conclusion: the I-75/Macon/Atlanta-side inland routes are dead.** They cost 2.8–3.6
extra hours — six times the stated detour budget. Georgia's road geometry funnels this
trip east: there is no usable inland diagonal from Gainesville to the Carolinas. Anything
west of the I-95/US-301 corridor is off the table, which removes Macon, Augusta, Aiken,
Dublin and Vidalia regardless of how good a stop they might be.

Everything worth considering therefore sits on the I-95 spine or within a short hop of it.

## 2. Candidate stops: the halfway band

`frac` is the fraction of total drive time completed by Saturday night. The owner asked for
"close to but not precisely halfway" — so the target zone is roughly **0.50–0.60**, which
puts a little more of the drive on Saturday and leaves a shorter Sunday.

Stops inside a sane band (frac 0.40–0.68, detour ≤ 60 min), ordered by daylight remaining
on arrival:

| Stop | Sat drive | Arrive | Sunset | Daylight left | Usable light | Detour | frac | Sun drive |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hardeeville, SC | 3:24 | 13:31 | 17:20 | 3:49 | 4:16 | +0:03 | 0.41 | 4:58 |
| Ridgeland, SC | 3:38 | 13:47 | 17:19 | 3:32 | 3:58 | +0:04 | 0.43 | 4:45 |
| Hilton Head Island, SC | 3:50 | 14:01 | 17:18 | 3:17 | 3:44 | +0:52 | 0.42 | 5:20 |
| Beaufort, SC | 3:57 | 14:10 | 17:18 | 3:08 | 3:35 | +0:39 | 0.44 | 5:01 |
| **Walterboro, SC** | 4:09 | 14:24 | 17:16 | 2:53 | 3:19 | **+0:07** | **0.49** | 4:16 |
| **Santee, SC** | 4:52 | 15:14 | 17:14 | 2:01 | 2:28 | **+0:17** | **0.56** | 3:44 |
| Summerville, SC | 4:52 | 15:15 | 17:14 | 1:59 | 2:26 | +0:53 | 0.53 | 4:19 |
| Orangeburg, SC | 4:56 | 15:19 | 17:16 | 1:57 | 2:24 | +0:41 | 0.55 | 4:04 |
| Sumter, SC | 5:23 | 15:52 | 17:13 | 1:21 | 1:49 | +0:26 | 0.62 | 3:22 |
| **Columbia, SC** | 5:31 | 16:01 | 17:15 | 1:14 | 1:42 | +0:49 | 0.60 | **3:37** |
| Florence, SC | 5:47 | 16:19 | 17:10 | 0:51 | 1:18 | +0:11 | 0.68 | 2:43 |
| Camden, SC | 5:55 | 16:29 | 17:13 | 0:44 | 1:11 | +0:49 | 0.65 | 3:13 |

Notable exclusions and why:

- **Savannah, GA** — only a 15-min detour and a genuinely great family city, but it sits at
  **frac 0.38**: a 3:17 Saturday and a **5:16 Sunday**. It is too early in the trip. It
  front-loads the easy day and leaves the hard one for the holiday-traffic Sunday.
- **Charleston, SC** — frac 0.52 is ideal, but the detour is **+1:22**, nearly double the
  budget. Summerville (+0:53) is the cheapest way to sleep within reach of Charleston.
- **Congaree National Park** — the obvious geospatial temptation, and it scores a **+2:03
  detour** because the visitor centre is at the end of a dead-end road you pay for twice.
  Also closes at dusk, so a 16:00 arrival gets almost nothing. Rejected on measurement.
- **Jekyll Island / St. Simons, GA** — lovely, but frac 0.27–0.28. Far too early.
- **Myrtle Beach, SC** — +2:09 detour. No.

## 3. The finding that should drive the decision: I-95 on Sunday 29 Nov

Sunday 29 Nov 2026 is the Sunday of Thanksgiving weekend — among the heaviest northbound
travel days of the year. I extracted the road refs for each candidate's Sunday leg:

| Stop | Sunday hours | Uses I-95? | Route |
|---|---:|:--:|---|
| **Columbia, SC** | 3:37 | **No** | I-77 → I-85 Charlotte–Greensboro → I-40 → NC-86 |
| Sumter, SC | 3:22 | Yes | US-76 → I-95 → I-295 → US-1/US-15-501 |
| Santee, SC | 3:44 | Yes | SC-6 → I-95 → I-295 → US-1/US-15-501 |
| Orangeburg, SC | 4:04 | Yes | US-601/US-301 → I-95 → I-295 |
| Florence, SC | 2:43 | Yes | I-95 → I-295 → US-1/US-15-501 |
| Walterboro, SC | 4:16 | Yes | US-15 → I-95 → I-295 |
| Summerville, SC | 4:19 | Yes | I-26 → I-95 → I-295 |
| Beaufort, SC | 5:01 | Yes | US-21/US-17 → I-95 → I-295 |
| Savannah, GA | 5:16 | Yes | US-17 → I-95 → I-295 |

**Columbia is the only shortlisted stop that avoids I-95 altogether.** Every other option
routes through the I-95 → I-295 Fayetteville corridor, which is exactly where holiday
northbound traffic concentrates. The free-flow numbers in section 2 therefore understate
the real Sunday cost of the coastal stops more than they understate Columbia's.

This inverts the naive reading of the table. Walterboro looks like the perfect
near-free halfway stop at +0:07 — and on an ordinary weekend it would be. On *this*
weekend its 4:16 Sunday leg runs the full length of the worst stretch, while Columbia's
3:37 does not.

### The real trade-off

The table reduces to one axis: **Saturday daylight versus Sunday traffic exposure.**

- Stop early (Walterboro, Hardeeville, Beaufort) → 3 hours of daylight for an outdoor
  exploration, but a long Sunday on I-95.
- Stop late (Columbia, Sumter) → little or no daylight on arrival, but a short Sunday and,
  for Columbia, no I-95 at all.

Stopping late is only the right call if the late-day activity is one that *works after
dark* — which, in the last week of November, is exactly when the region's Christmas light
displays open. That is the hinge, and it is what the destination research was commissioned
to settle.

---

## 4. Destination assessments

Per-area research, with every date and price traced to a source and the unverified items
called out as unverified:

| File | Covers |
|---|---|
| `data/research-savannah.md` | Savannah, Pooler, Tybee, Hardeeville |
| `data/research-lowcountry.md` | Hilton Head, Beaufort, Walterboro, Summerville |
| `data/research-charleston.md` | Charleston, Mount Pleasant, North Charleston |
| `data/research-columbia.md` | Columbia, Congaree, Orangeburg, Santee, Camden |
| `data/research-sandhills-florence.md` | Florence, Fayetteville, Southern Pines, Myrtle Beach |

## 5. Recommendation

See **`recommendation.md`**. In short: the holiday calendar, not the geography, decides this
trip. Nov 28 2026 falls in a gap — a week before almost every town's parade and tree
lighting, a day after the few kickoffs — so the shortlist collapses to the handful of places
with a Christmas light display already running that night. Combined with a 17:15 sunset that
makes every daytime attraction unreachable, the stop to pick is one where darkness is the
attraction.

**Recommended: Columbia, SC** — the only in-band stop that avoids I-95 on Thanksgiving
Sunday, with three confirmed light events that evening (cheapest $30/car, all-inclusive),
no home football game, and verified indoor-pool suites around $110.
**Runner-up: Orangeburg, SC** — a free, kid-specific light walk and 42 more minutes of
daylight, at the price of the longest Sunday on I-95.
