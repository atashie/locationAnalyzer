---
name: feedback-a-published-page-must-name-its-source
description: A published artifact is the only copy that reaches other machines; if it does not name the repo, branch and path that built it, a later session can reproduce everything and still refuse to edit it
metadata:
  type: feedback
---

Learned 2026-11-08, from a handoff that failed with everything already committed and pushed.

A session on a second machine was given the published route page and asked to change a route. It
did the hard parts unprompted and well: identified the routing engine from the page, reproduced
the direct trip to within a minute (540 mi / 8h41 against the page's 8h42), and recovered the map
projection from the city dots to about a pixel. Then it stopped. Its own account: the build
script and data "aren't on this machine… The page itself is the only source", so it "haven't
changed any routes yet."

**Why:** it could not tell whether editing meant updating the source of truth or forking away
from it. That is the right call with the information it had, and it had that little information
only because the page never said where it came from. The repo was one `git clone` away.

Provenance on that page was otherwise exemplary — measured, derived, computed, calculated, and
standing-hours all labelled per figure. Every label described *the numbers*. None described *the
page*. The habit of labelling values does not produce the one label a reader on another machine
actually needs.

**How to apply:**

- Every generated page carries a **Source** line in its provenance block naming the repo as
  `git clone` accepts it, the branch, the path, the offline rebuild command, and the instruction
  to republish to the same URL. Not the project's name, not the app's name, not the local folder
  — see [[reference-repo-identity]] for why those are three different words here.
- The rule is in `skills/planning-route-stops/comparison-page.md`, and enforced: `doccheck.py`
  fails a worked example whose generator emits no Source block, or whose Source block names no
  `github.com/<owner>/<repo>`. Both failure modes were verified to fire before the check was
  committed.
- Generalise past pages: anything published outward that someone may later need to edit should
  state where its inputs live. The artifact is the wide-reaching copy; the repo is the editable
  one; only the artifact can carry the pointer between them.

Related: [[feedback-provenance-is-not-correctness]] — the same discipline failing in the other
direction, where labels were right and values wrong.
