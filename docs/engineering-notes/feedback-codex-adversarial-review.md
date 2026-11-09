---
name: feedback-codex-adversarial-review
description: Use Codex CLI as an adversarial reviewer after every major plan and every analyzed set of results
metadata:
  type: feedback
---

Call Codex (installed: codex-cli, use the codex:rescue / codex:codex-rescue plugin)
as an adversarial reviewer after every major plan is drafted and after every set
of results lands and has been analyzed. Do this regularly, not just at the end.

**Why:** The user believes a different model family catches different errors and
explicitly asked for Codex as a "great partner ... in an adversarial review context."

**How to apply:** Frame Codex prompts adversarially (find holes, challenge
assumptions, verify claims). Record Codex findings alongside the reviewed artifact
and address or explicitly dismiss each one. See [[feedback-autonomous-work-style]].
