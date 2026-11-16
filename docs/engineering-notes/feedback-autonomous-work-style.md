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

## How to write the summary back, 2026-11-16

The owner's words: *"I don't like how we are communicating with each other. In
the future please write summaries in plain english, with bullet points where
possible, and always delineate planned or possible next steps by plans that I
intend to implement and why vs steps that I'd need to implement or approve."*

Three rules, in force for every reply:

- **Plain English.** Short, ordinary words. No rhetorical build-ups, no
  drum-roll sentences, no clever framing. Say the thing.
- **Bullet points wherever they fit.** Prose paragraphs only when a point
  genuinely needs connected reasoning.
- **Split next steps into two labelled lists, always:**
  - what I plan to do next, each with a one-line reason;
  - what needs the owner -- a decision, an approval, or something only they
    can do, like a walk or a device.

**Why:** the owner is not watching in real time. They read a summary to decide
what to do. A summary that mixes my work with theirs, or that buries the
decision in prose, makes them do sorting work before they can act. This
supersedes nothing above; it is how the result of a long autonomous run gets
reported.

This extends the existing prose rule in [[project-phase1-s3-progress]]
("short, plain, concrete sentences; the owner rejected decorated writing in
those words"). That rule was about the *documents*. This one is about the
*replies*, which had drifted further than the documents had.
