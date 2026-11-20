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
- **2026-11-16: Codex DID execute processes this session**, against the note above. A `task`
  run on gpt-6.1-sol ran PowerShell, the venv Python, pytest and node, rebuilt the UTM grid and
  reproduced counterexamples. Do not assume read-only any more -- check, because handing over a
  measurement "to attack as method" is a weaker review than letting it run the code. Two other
  things from that run: a background job can **die leaving its state saying `running`** with the
  pid gone, so check the pid and the log mtime rather than the status; and the full assistant
  messages of a dead run are recoverable from `~/.codex/sessions/<date>/rollout-*-<threadId>.jsonl`,
  which is how pass 55's first four findings survived.
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

## 2026-11-14: the working copy is CRLF, so an LF anchor matches nothing

Two mutations in `spikes/g3-render/mutate_worker.mjs` were reported **INERT** — the edit matched
nothing, so the guard they were meant to exercise was not being exercised at all. The anchors were
multi-line string literals with `\n` in them, and `worker.js` in the working copy has **CRLF**
line endings, because `core.autocrlf` converts on checkout. An `\n` literal therefore matches
nothing while every single-line anchor matches fine, which is why this only ever shows up on
multi-line edits.

```js
s.includes("state.lastEnabled = null;\n  state.lastInCount = 0;")    // false
s.includes("state.lastEnabled = null;\r\n  state.lastInCount = 0;")  // true
```

So: **any multi-line anchor in a `.mjs` or `.py` patch must be a regex with `\r?\n`**, never a
string literal with `\n`. The same trap caught a Python patch script earlier (a two-line import
anchor failed under CRLF while single-line anchors matched), so this is the second time. The
mutation runner reporting INERT separately from a catch is what made it visible both times —
without that it reads as a pass.

## 2026-11-14: I used a shell heredoc for a patch script again, twice, and it mangled the escapes again

The note above says to write patch scripts with the file-writing tool. I used
`python -I - <<'PY'` twice in one session anyway, and both times the backslashes were eaten:
`\*` arrived as `\*` and `\n` as `\n`, producing `SyntaxWarning: invalid escape sequence` and an
anchor that matched zero times. The first attempt also aborted part-way, leaving an in-memory edit
unwritten, which is a worse failure than a clean error.

A quoted heredoc protects `$` and backticks. **It does not protect backslashes from the shell's
own processing on this setup.** So the rule is narrower and easier to follow than "prefer the
tool":

* A heredoc is fine for a script with **no backslashes at all**.
* Anything with a regex, an escape sequence, or a Windows path goes through the file-writing tool
  and then `python -I <path>`.

## The heredoc rule is now absolute, after failing five times in one session

The rule was: a quoted shell heredoc is fine for a patch script **with no backslashes**, because a
quoted heredoc protects `$` and backticks but still eats one level of backslash.

That rule is correct and it does not work, because I cannot tell in advance whether a patch script
will need a backslash. On 2026-11-14 it was broken five times in one session: `\\*` became `\*`;
`\\n` became `\n`; a `\n` inside a replacement string became a real newline and produced
`SyntaxError: unterminated f-string literal`; and twice a quoted heredoc failed to parse at all
because the content contained an apostrophe the shell objected to.

**So: never use a shell heredoc to write a script. Write it with the file-writing tool and run it
with `python <path>`.** No exceptions, no judgement call about whether this one has backslashes in
it. The judgement call is the thing that keeps failing.

One further detail that cost a run: **`python -I` breaks on this machine** for anything importing
`geopandas` or `pandas`, because `-I` drops the user site directory and `dateutil` lives there.
Use `-I` only for scripts that read downloaded or untrusted data, which is what it is for; project
code runs as plain `python`.

## Backticks in a `git commit -m` string are command substitution

A commit message passed with `-m "...`identifier`..."` had every backticked identifier **eaten by
the shell**: `` `elif not candidates:` `` became an attempted command and the surrounding sentence
lost its subject. The commit landed with the gap, and because it was already pushed, repairing it
would have meant rewriting pushed history, which is not worth a sentence.

**So: every commit message goes through a file with `-F`, not `-m`.** This project's messages are
long and full of backticked identifiers, which is exactly the shape that breaks. The rationale
that was lost went into a code comment instead, where it is more useful than in a message.

## 2026-11-16: `codex exec` in a background shell blocks forever on stdin

A pass-57 review was launched in a background Bash shell and sat there for **1 hour 48 minutes**
having used **0.3 seconds of CPU**. Its whole output file was one line:

```
Reading additional input from stdin...
```

`codex exec` takes the prompt as a positional argument *and* appends anything on stdin. When stdin
is not a TTY it announces that read and blocks. An interactive shell gives it a TTY, so this never
appears when testing by hand; a backgrounded shell hands it a pipe that nobody ever closes, so the
run never starts. Nothing times out and nothing errors.

**So: every background `codex exec` gets `< /dev/null`.**

```bash
codex.exe exec -s read-only --model gpt-6.1-sol -C <dir> "<prompt>" < /dev/null > "$OUT" 2>&1
```

Two things made this cost nearly two hours instead of two minutes:

* The standing rule not to poll a background task was followed literally. It is the right default
  for a task that reports when it exits, but a task that blocks on input never exits. **One check
  that the CPU time is non-zero, shortly after launch, separates "thinking" from "hung"** and costs
  nothing. `Get-Process` CPU and the output file's mtime are the two cheap signals, and neither
  counts as waiting on the result.
* The launch was never smoke-tested. The `--print` prompt-attachment bug in the Antigravity CLI was
  caught the same day *because* a one-line smoke test ran first. The Codex launch skipped it.
  **A smoke test before a long reviewer run is worth its cost every time**, since the failure it
  catches is otherwise invisible until the report is due.

This is the same shape as that `agy --print` bug: both CLIs accept a prompt in a way that looks
right, fail silently rather than erroring, and are caught in seconds by a probe that asks only for
the word READY and a `git log -1`.
## 2026-11-19: Antigravity headless cannot be given scoped permissions, and `--mode plan` reviews nothing

**Owner decision the same day: do not use Antigravity as a reviewer.** *"If it requires multiple
dangerously-skip-permissions calls then I do not think it is worth the effort."* Recorded here so
nobody spends the three attempts again.

What was tried, in order:

* `--dangerously-skip-permissions` — **refused by the Claude Code auto-mode classifier** as
  undermining oversight, which is correct: it auto-approves every tool, writes included. An agent
  cannot launch Antigravity headless this way.
* `--mode plan` alone — runs, exits **0**, and produces **no review**. Plan mode makes the agent
  write an implementation plan and stop to ask for confirmation. It wrote the plan to
  `~/.gemini/antigravity-cli/brain/<id>/implementation_plan.md` and asked a question. **Exit 0 with
  a plan is the failure mode**, and it looks like success in a task notification.
* `--settings <file>` with `permissions.allow` entries of the form `command(git)`, `command(python)`
  and so on — **same auto-denial**. The error names the permission as `command` and suggests
  `command(<target>)`, but no spelling tried was accepted, and **there is no `agy` settings.json
  anywhere on this machine** to copy a working schema from. The pass-56 note records that the
  reviewer "was given no write access" without recording how, so that configuration is lost.

**Both of those conclusions were too strong, and two probes on the evening of 2026-11-19
corrected them.** The owner asked for an Antigravity review again the same day, so the launch was
retried with no `--dangerously-skip-permissions` anywhere:

* **A READ-ONLY review needs no blanket flag at all.** `agy --print "<task>" --sandbox` read a file
  out of the repository and answered correctly on the first try. What was auto-denied in the three
  earlier attempts was *terminal commands*, not file reads, and the note above did not separate
  them. So Antigravity is usable as a reviewer for prose, records, tables and code — which is where
  it found most of pass 56's findings anyway — and only a pass that must *execute* something needs
  the owner.
* **`--mode auto` is not available for this account.** It prints
  `warning: --mode auto is not available for this account; continuing in the default mode` and
  continues. The recommendation above to use `--mode auto` instead of `--mode plan` was therefore
  advice to pass a flag that does nothing; the *default* mode is what works. The real lesson of the
  `--mode plan` failure was narrower than it looked: **do not pass `--mode` at all.**
* `--sandbox` ("run in a sandbox with terminal restrictions enabled") exists and is the right flag
  for a review, because it states the restriction rather than discovering it.
* `agy models` lists what the account can use. `gemini-4-hydrogen-xhigh` is available, which is the
  model pass 56 used.

**What this cost to learn: two commands and about a minute.** The earlier conclusion that
Antigravity was unusable held for a day and removed the second reviewer, which the section above
correctly called a real loss — and it was wrong because three failures with one *kind* of
permission were generalised to the tool. The probe that settled it is the same one-line smoke test
that has now earned its cost four times.

**Codex executed commands again on 2026-11-19.** The smoke test ran
`powershell -Command 'git log -1 --oneline'` and returned exit 0, so the 2026-11-13 section above —
"Codex cannot execute anything sandboxed on this machine" — is not currently true either. Check
with the smoke test rather than assuming; both of these sections have been wrong in both
directions.

**The smoke test earned its cost for the third time.** One probe asking for the word READY and a
`git log -1` caught the `--mode plan` behaviour in seconds; the alternative was waiting for a
review that was never going to arrive. Codex passed the same probe first try and its review ran
fine.

**The consequence I drew here was wrong, and it is left standing because the mistake is the
lesson.** I wrote: *"Reviews are now single-reviewer. Pass 56's most useful output was the
disagreement between Codex and Antigravity on how to rank product risk, and that is no longer
available."* The first sentence was a prediction dressed as a consequence, and the paragraph above
this one disproves it the same evening. The second sentence is still true and is the reason the
first one mattered: a cross-reviewer disagreement is the most valuable thing these passes produce,
which is exactly why "the tool does not work" deserved one more probe before it became policy.
