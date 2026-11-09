# Skills

Personal Claude Code skills, version-controlled here. Everything is on `master`.

| Skill | What it is for |
|---|---|
| `planning-route-stops` | Choosing where to stop along a journey. Holds provenance, recomputation and verification status in place; does not teach travel knowledge. Ships two measuring tools, a self-test, a doc checker and a complete worked trip. |

## Setting up on a new machine

Claude Code only sees a skill at `~/.claude/skills/<name>`. Link that path into this checkout,
so the files Claude loads and the files git tracks are the same bytes — then editing either
path edits both, and `git status` tells the truth about what Claude is actually running.

**Windows** (no admin needed; `mklink /J` makes a directory junction):

```
cmd /c mklink /J "%USERPROFILE%\.claude\skills\planning-route-stops" ^
  "<repo>\skills\planning-route-stops"
```

**macOS / Linux:**

```bash
ln -s "<repo>/skills/planning-route-stops" ~/.claude/skills/planning-route-stops
```

Replace `<repo>` with wherever you cloned. Then confirm the link resolved and the skill is
intact. Both checks are self-contained and need no network:

```bash
python ~/.claude/skills/planning-route-stops/selftest.py     # expect 42/42 pass
python ~/.claude/skills/planning-route-stops/doccheck.py \
       ~/.claude/skills/planning-route-stops/examples/chapel-hill-thomasville
                                                             # expect "prose and code agree"
```

`selftest.py` checks the measuring tools' invariants — every case in it is a defect that once
reached a published page. `doccheck.py` checks the skill's prose against its own code and
against the worked example's real figures, so the documentation cannot drift silently.

## Worked example

`planning-route-stops/examples/chapel-hill-thomasville/` is a complete trip — seven itineraries
across three corridors, 23 researched facility schedules, a baked basemap — and it **rebuilds
offline from what is committed**:

```bash
cd skills/planning-route-stops/examples/chapel-hill-thomasville
python build_page.py            # -> route-options.html
```

Its own README covers re-measuring against live routing, editing the trip, and **updating the
already-published artifact rather than creating a second one**. Read it before building a new
trip: the spec format is much easier to copy than to infer.

## Working on this repo

A git worktree keeps the junction stable while the main checkout's branch changes underneath:

```bash
git worktree add ../distancefinder-skills master
```

That is how this was developed — the junction points into the worktree, so switching the main
tree to a feature branch never makes the skill vanish from under Claude.

After changing a tool run `selftest.py`; after changing prose run `doccheck.py`. Add a case to
the self-test whenever you fix something: a fix without a failing test beside it is a fix that
comes back.
