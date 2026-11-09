---
name: reference-where-secrets-hide
description: "Where credentials have actually turned up in this repo - .claude/settings.local.json records approved Bash commands verbatim, and four diagnostic scripts printed a live key to stdout - plus the handling pattern that found them"
metadata:
  node_type: memory
  type: reference
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-09T00:00:00.000Z
---

Found 2026-11-09 while making the untracked `backend/test_*.py` diagnostic scripts committable
(`02a0b24`, `48e776e`). Nothing was ever published — `git log -S<key> --all` found no match and no
committed version of any file contained it — but two of the three hiding places were not where I
would have looked.

**1. `.claude/settings.local.json` records approved Bash commands verbatim.** It is a remembered
allow-list, so **anything typed into a command that was then approved is stored in it** — here, a
live TripAdvisor key in three entries, because the key had been pasted into `set "VAR=..."` and two
inline `python -c` commands. The file was **tracked**, so any future `git add -A` would have
published it. It is now gitignored and the three entries are removed; 56 remain and were swept for
other credential-shaped values (none). `.claude/settings.json`, the shared config, stays tracked.

> This is the generalisable one. A credential does not have to be *written to a config file* to end
> up in a tracked file — it is enough to have typed it into a command once.

**2. Printing is disclosure too.** Four of the five key-bearing scripts did
`print(f'Params: {params}')` where `params['key']` was the live key. Terminal scrollback, captured
logs and pasted output are the same exposure as a commit, just slower and harder to audit. They now
print `masked(params)` from `backend/tripadvisor_test_env.py`.

**3. The ordinary one:** five scripts assigned the key inline. They now call
`tripadvisor_test_env.load_api_key()`, which reads `TRIPADVISOR_API_KEY` from `backend/.env`
(gitignored, explicit path so it works from the repo root too) or the environment, and **exits with
instructions when absent** rather than failing later as an opaque 401. `.env.example` documents
`TRIPADVISOR_API_KEY` and `TRIPADVISOR_REFERER_DOMAIN`, which it had omitted despite `CLAUDE.md`
listing both.

**The handling pattern, which is the reusable part.**

- **Never put the secret in the tool that removes it.** Both patch scripts discovered the key by
  regex — from the file being cleaned, then from the gitignored `.env` — so neither script, and
  neither scratchpad artifact, ever contained it.
- **Mask in the diagnostic, not just in the fix.** Every search printed `<REDACTED-32>` or a length,
  never the value, so the investigation did not create new copies in the transcript.
- **Sweep the staged diff before every commit:** `git diff --cached | grep -q -- "$KEY"`. Checking
  the working tree is not enough — what matters is what is about to be published.
- **Check history before claiming it is clean:** `git log -S"$KEY" --all` plus
  `git show HEAD:<path> | grep`. "It is untracked" and "it was never committed" are different facts.
- **Scan what you leave behind,** not only what you change: after filtering the allow-list, the
  remaining 56 entries were checked for any 20+ character value following a
  `key`/`token`/`secret`/`password` assignment.

**Still open, deliberately.** The TripAdvisor key is **not rotated** — the owner's call on
2026-11-09 ("don't worry about the tripadvisor api key for now"). It has existed in plaintext in
several places on this machine and is now reaching a second one, so rotation remains the standing
recommendation; `.env` means a new value needs no code change. A **live Google Maps API key** was
also pasted into the terminal in an earlier session; restricting or rotating that one was
recommended at the time and has not been confirmed done.

Related: [[project-v2-rethink-decisions]] for the data-licensing constraints, which are a separate
concern from credential handling — contractually restricted sources (Google place IDs, RentCast,
MLS/IDX, portals) must never enter an ODbL-published artifact.
