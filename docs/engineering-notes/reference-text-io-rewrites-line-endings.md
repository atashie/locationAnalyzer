# `read_text` + `write_text` silently rewrites line endings on Windows

**2026-11-10.** Found because a mutation harness's own "restored byte-identically" check failed, and
then because the older harness's equivalent check could never fail.

## The fact

`pathlib.Path.read_text()` reads with **universal newlines**: every `\r\n` becomes `\n` in the
string. `pathlib.Path.write_text()` writes with `newline=None`, which translates every `\n` to
`os.linesep` — `\r\n` on Windows. So the pair is **not** a round trip:

```python
f.write_bytes(b"a = 1\nb = 2\n")        # LF
f.write_text(f.read_text())             # read then write back, "unchanged"
f.read_bytes()                          # b'a = 1\r\nb = 2\r\n'   <- every line changed
```

A CRLF file survives; an LF file is converted. Measured both ways, not assumed.

## Why it mattered here

Two committed mutation harnesses save a source file, mutate it, and restore it. Both used
`read_text`/`write_text`, so restoring an LF file rewrote every line ending in it.

`mutate_conditional_rate_guards.py` was the worse case: it hashed the **decoded text** on both
sides —

```python
digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
back = hashlib.sha256(TARGET.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
```

— which compares translated to translated. It printed `restored byte-identical: True` however much
the bytes on disk had changed. **A verification that cannot fail in the dimension it claims to check
is not a verification**, and this one was guarding against a tool leaving a mutation in the
repository.

This repo sets `core.autocrlf=true`, which normalises on commit and hid the consequence entirely:
`git diff` showed nothing. On a repository that does not normalise, the same code produces a
whole-file diff authored by a verification tool.

## The rules

- **A tool that saves and restores a file reads and writes bytes.** `path.read_bytes().decode("utf-8")`
  and `path.write_bytes(text.encode("utf-8"))`.
- **Hash the bytes on disk**, never a decoded copy of them, when the claim is about bytes on disk.
- **Once reads are faithful, multi-line anchors stop matching on a CRLF checkout.** Both harnesses
  now localise their anchors to the file's own line ending. This matters more than it sounds: an
  anchor that cannot be applied reports as a **surviving mutation**, which looks exactly like a test
  that cannot see one. Two different failures with one appearance.
- Not a reason to change the repo's `autocrlf`. It is a reason not to let a tool's correctness
  depend on it.

Related: [[feedback-verify-the-shape-of-the-risk]],
[[project-phase1-s3-audit-destination-recovery]], [[reference-codex-runtime-quirks]].
