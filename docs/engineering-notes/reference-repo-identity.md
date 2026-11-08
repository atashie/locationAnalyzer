---
name: reference-repo-identity
description: This work lives in atashie/locationAnalyzer on master; three other things answer to the name "distance finder" and none of them is it
metadata:
  type: reference
---

Recorded 2026-11-08, after a session on a second machine reported committed work as missing.

**The repo is `atashie/locationAnalyzer`. Default branch `master`.**

```bash
git clone https://github.com/atashie/locationAnalyzer.git
```

Four names overlap, and only the first is this repo:

| Name | What it is |
|---|---|
| `atashie/locationAnalyzer` | **This repo.** V1 app, V2 rethink, `docs/engineering-notes/`, `skills/`. |
| `atashie/distanceFinder` | A *separate* GitHub repo: a small Streamlit location PoC. Six files. No skills, no trips. |
| `distanceFinder/` in this tree | That same PoC, kept for history. Also not the skill. |
| `atashie/cc-skills` | A real Claude Code plugin repo — but it holds `html-review-comments` only, and none of this project's skills. |

The local checkout is customarily `~/documents/github/distancefinder`, and the app calls itself
Distance Finder, so the collision is easy to walk into rather than a hypothetical.

**What it cost.** Asked to adjust a route on an already-published page, a session on a second
machine pulled `distanceFinder`, found a Streamlit app, searched the disk for build scripts and
stop data, found none, and concluded the work "was probably done in a session or on a machine I
can't reach… The page itself is the only source." It then declined to change any routes. The
spec, generator, measurements and basemap were on `origin/master` of `locationAnalyzer` the
whole time, pushed two days earlier in `3c0360c`.

**How to apply.** If something this repo's documentation describes appears to be absent, check
`git remote -v` and `git ls-tree origin/master --name-only` *before* concluding it was lost.
Committed work going missing is far rarer than a wrong clone. The repo name is now stated in
`CLAUDE.md`, in `skills/README.md`, and in the footer of every page the route skill generates —
see [[feedback-a-published-page-must-name-its-source]].

Related: [[reference-sibling-repos]] for local sibling directories, a different question.
