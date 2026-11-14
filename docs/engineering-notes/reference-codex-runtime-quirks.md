---
name: reference-codex-runtime-quirks
description: "How to invoke Codex reliably on this machine - supported models for the ChatGPT account, pass --model explicitly, put long prompts in a file, avoid big Bash heredocs"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-06T13:41:49.109Z
---

Learned 2026-11-03 after five failed Codex launches:
- `~/.codex/config.toml` pins `model = "gpt-5.5"`, which the account cannot use
  ("not supported when using Codex with a ChatGPT account"); gpt-5.4 fails too.
  `~/.codex/models_cache.json` lists the usable models: gpt-6.1-sol, gpt-6-astra,
  gpt-6.1-terra, gpt-6-sol, gpt-6-luna, gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna.
  Always pass `--model gpt-5.6-sol` (or `gpt-6.1-sol` for a stronger pass) until
  the owner updates config.toml. (Owner was told; do not edit their config unasked.)
- Direct, reliable launch from the main session:
  `node "C:/Users/arikt/.claude/plugins/cache/openai-codex/codex/1.0.2/scripts/codex-companion.mjs" task --background --write --model <model> "Read the file '<prompt.md>' and carry out the task it describes exactly."`
  then `status [job-id] --json` / `result [job-id]`. Jobs are tracked under
  `~/.claude/plugins/data/codex-openai-codex/state/distanceFinder-*/jobs/`.
- Put long prompts in a scratchpad file; multi-KB single-command heredocs through
  the Bash tool fail with "unexpected EOF while looking for matching `''". The
  same applies to writing large markdown files: use the Write tool, not heredocs.
- **Bash heredocs here consume one backslash level, even quoted (`<<'PY'`).** To
  match the two characters backslash-plus-n in a Python source file I wrote a
  doubled escape in the heredoc; Python received the single escape and parsed it
  as a real newline, so an assertion-guarded patch failed with PATTERN NOT FOUND
  on text that was character-for-character present. Anchor heredoc patches on
  **backslash-free** text, or use the Edit tool when the target contains escapes.
  To append a large test block: Write it to the scratchpad, then append with a
  short `python -c` that reads that file. Learned 2026-11-06.
- The `codex:codex-rescue` subagent retries on its own and reports Bash task ids,
  not companion job ids; check `status --all --json` before launching another job.
Related: [[feedback-codex-adversarial-review]].

## Long text into a command: write a file, pass the path

The "avoid big Bash heredocs" rule above bit twice more on 2026-11-10, in two different ways, so
here is the general form rather than the two instances.

- A `python - <<'PY'` heredoc carrying a patch script with `'''` triple-quoted blocks inside failed
  with `unexpected EOF while looking for matching '`.
- A `git commit --file=- <<'MSG'` heredoc carrying a long commit message failed the same way.

In both cases nothing was written, so the failures were cheap — but the fix is the same and should
be the default for anything long:

- **script** → `Write` it to the scratchpad, then `python <path>`;
- **commit message** → `Write` it to the scratchpad, then `git commit --file=<path>`.

This also makes the content reviewable before it runs, which matters for assertion-guarded patch
scripts. Short one-liners through a heredoc remain fine.

### A third instance, and this one fails silently

Later the same day I broke the `--file` rule above by using `git commit -q -m "..."` with a
multi-line **double-quoted** message. Inside double quotes bash performs command substitution, so
every backtick-quoted word in the message was executed as a command and replaced with its (empty)
output:

```
adding `surface` to EXTRA_WAY_TAGS     ->     adding  to EXTRA_WAY_TAGS
```

with `bash: line 72: surface: command not found` on stderr — and **the commit still succeeded, exit
0**. The two heredoc failures above at least errored and wrote nothing. This one lands a commit
whose message is quietly missing the words that carried the meaning, and nothing downstream
notices.

Commit messages in this project are full of backticked identifiers, so this will recur on every
`-m` that is not single-quoted. The rule is unchanged but now has teeth:

- **Never `git commit -m` with a multi-line message.** `Write` it to the scratchpad and use
  `git commit --file=<path>`, which does no shell interpretation at all.
- If a message must go inline, single-quote it — but prefer `--file`, because the failure mode of
  getting it wrong is invisible.
- The same hazard applies to any double-quoted shell string carrying markdown: `echo`, `cat >>`
  with an unquoted delimiter, `gh pr create --body "..."`.

I did not rewrite the pushed commit for this: the degraded message is `917ea95`, the content it lost
is intact in [[project-phase1-s3-soft-way-dependence]] and [[project-phase1-s3-design]], and
force-pushing to repair a cosmetic message defect is a worse trade than leaving one commit's prose
thin.

## 2026-11-13: Codex cannot execute anything sandboxed on this machine

Pass 48 had to run **read-only**. Every `exec_command` failed with:

```
UnsupportedOperation("windows unelevated restricted-token sandbox cannot enforce split
writable root sets directly; refusing to run unsandboxed")
```

Codex 0.167.0, Windows 11, unelevated. It is not about which directories were requested. The error
appeared with `-s workspace-write` alone, with `--add-dir` pointing at the session scratchpad, with
`-c sandbox_workspace_write.exclude_tmpdir_env_var=true -c
sandbox_workspace_write.exclude_slash_tmp=true`, and with `--ephemeral`. A one-line probe asking it
only to run `python -c "print(2+2)"` failed the same way. The restricted-token sandbox apparently
cannot express the workspace root plus the session directory as one writable set, and it refuses
rather than widening.

**What still works read-only.** The `node_repl` MCP tool runs JavaScript in-process, outside the
process sandbox. That turned out to be enough for a real review of the browser decoder: the
reviewer loaded `worker.js` into a `vm` context with a `self` shim, replayed the whole conformance
harness in memory, and ran mutations against it — 50 checks and 18 mutations, all executed. What it
could not do was run Python, pytest, GDAL or a graph load, so its Python reproducers came back
explicitly marked unexecuted, which is the right way to hand one over.

**So the options for a pass that needs Python are:**

1. `--dangerously-bypass-approvals-and-sandbox`, which is how passes 42–47 ran. Claude Code's auto
   mode refuses to launch it (`Undermining Oversight`), so it needs the owner to run it with a
   leading `!` in the prompt, or a permission rule.
2. Run the Python measurements **before** the pass and hand the reviewer the numbers to attack as
   *method* rather than to reproduce. Pass 48 did this for its §B and §D, and it worked better than
   expected — the reviewer broke the method of two of them (the round trip bounds nothing about
   households; three warped byte planes can recombine into a valid index) which is a harder and
   more useful kind of finding than a reproduction.
3. Give it a read-only pass on prose, records and JavaScript, which is where it found four of pass
   48's seven findings anyway.

Option 2 is worth doing **even when option 1 is available**, because asking "what is wrong with how
I measured this" is a different question from "reproduce this", and only the first can catch an
instrument pointed at the wrong quantity.

Note also that a read-only pass cannot write its report to a file. Ask for stdout and save it
afterwards, or the pass ends with its findings only in a log.
