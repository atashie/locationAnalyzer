# Skills

Personal Claude Code skills, version-controlled here.

`~/.claude/skills/<name>` is a **directory junction** pointing into this worktree, so the
files Claude loads and the files git tracks are the same bytes. Edit either path; commit and
push from here.

This worktree is pinned to the `skills` branch and lives beside the main repo at
`../distancefinder-skills`, deliberately outside it so the main tree's branch can change
without the skill disappearing from under the junction.

| Skill | What it is for |
|---|---|
| `planning-route-stops` | Choosing where to stop along a journey. Holds provenance, recomputation and verification status in place; does not teach travel knowledge. |

To re-create the junction on a new machine (Windows, no admin needed):

```
cmd /c mklink /J "%USERPROFILE%\.claude\skills\planning-route-stops" ^
  "%USERPROFILE%\documents\github\distancefinder-skills\skills\planning-route-stops"
```
