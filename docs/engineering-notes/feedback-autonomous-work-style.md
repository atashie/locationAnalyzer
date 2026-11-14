---
name: feedback-autonomous-work-style
description: Work iteratively and autonomously, launch subagents freely, pause for user feedback only when absolutely necessary; commit and push to origin freely on the working branch
metadata:
  type: feedback
---

Work iteratively, creatively, and autonomously. Launch subagents for research,
test cases, and tooling trials without asking. Pause for the user only when a
decision is genuinely theirs.

**Git policy, current:** create branches, commit **and push to `origin`** freely
on the working branch. The 2026-11-03 policy was "never push; the user merges";
that was **overridden** during S3 and pushing is authorized. Merges to `master`
are still the owner's. Keep using `git commit --file=` rather than `-m` for
anything multi-line -- see [[reference-codex-runtime-quirks]], where a
double-quoted `-m` silently command-substituted backticks and still exited 0.

**Codex cadence, standing:** run an adversarial Codex pass **very regularly** --
after every major plan, and after every set of results lands *and has been
analysed*. Commit the prompt before launching, as passes 42-49 did. Trust order,
the owner's: **experimental results > research > priors.**

**Why:** The user is not watching in real time and wants long autonomous runs
with a few high-leverage check-ins rather than many small ones.

**How to apply:** Batch clarifying questions up front; afterwards make routine
calls yourself and document assumptions. Commit research docs and plans as they
land on the working branch. Related: [[feedback-codex-adversarial-review]].
