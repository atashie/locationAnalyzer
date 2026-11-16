"""Reassemble a browser probe run from the loopback server's access log.

**Why this exists.** `probe_placement.js` returns about 10 KB of JSON. A session driving the page
has to get that into a file, and reading it back through the browser tool spends the whole
document on context for no benefit -- twice now. The page instead sends it as a sequence of GETs
whose query strings carry the payload, `python -m http.server` logs every request line verbatim,
and this reads the log and puts the document back together.

From the page:

    const enc = encodeURIComponent(JSON.stringify(run));
    const parts = [];                       // 1200 chars is comfortably inside every URL limit
    for (let i = 0; i < enc.length; i += 1200) parts.push(enc.slice(i, i + 1200));
    const stamp = Date.now();
    for (let i = 0; i < parts.length; i++) {
      await fetch(`/__run?s=${stamp}&i=${i}&n=${parts.length}` +
                  `&d=${encodeURIComponent(parts[i])}`).catch(() => {});
    }

**Encode twice, and this unquotes twice.** A slice of a percent-encoded string can cut a `%XX`
escape in half, so each piece is re-encoded as opaque text before it is sent.

Then:

    python scripts/collect_probe_run.py <log file> <stamp> [--into <artifact.json> --key <name>]

Every chunk index must be present exactly once and the whole must parse as JSON, or it writes
nothing: a partial run that looks complete is worse than a failure, because the thing being
collected is evidence.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import urllib.parse

PATTERN = re.compile(r'"GET /__run\?s=(\d+)&i=(\d+)&n=(\d+)&d=([^ ]*) HTTP')


def collect(log: pathlib.Path, stamp: str) -> dict:
    """The run the page sent under `stamp`, or an AssertionError saying what is missing."""
    chunks: dict[int, str] = {}
    total: int | None = None
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = PATTERN.search(line)
        if not m or m.group(1) != stamp:
            continue
        i, n = int(m.group(2)), int(m.group(3))
        total = n if total is None else total
        assert n == total, f"chunk {i} says {n} chunks, an earlier one said {total}"
        # **Reject an index outside the declared range** -- Codex pass 55, F9. Without this a
        # complete `n=1` payload plus a stray `i=99,n=1` was accepted, the extra chunk silently
        # ignored, and the result reported as a clean collection. A collector whose job is to
        # move evidence must refuse anything it cannot account for, not quietly drop it.
        assert 0 <= i < total, f"chunk index {i} is outside the declared range 0..{total - 1}"
        assert i not in chunks, f"chunk {i} arrived twice; the log holds two runs for this stamp"
        chunks[i] = m.group(4)

    assert total is not None, f"no chunks for stamp {stamp} in {log.name}"
    missing = [i for i in range(total) if i not in chunks]
    assert not missing, f"missing chunks: {missing} of {total}"
    assert len(chunks) == total, f"{len(chunks)} chunks for a payload declaring {total}"
    encoded = "".join(urllib.parse.unquote(chunks[i]) for i in range(total))
    return json.loads(urllib.parse.unquote(encoded))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("log", type=pathlib.Path, help="the http.server output file")
    ap.add_argument("stamp", help="the `s=` value the page used")
    ap.add_argument("--into", type=pathlib.Path,
                    help="an existing JSON artifact to write the run into")
    ap.add_argument("--key", default="run", help="the key to write it under (with --into)")
    args = ap.parse_args()

    run = collect(args.log, args.stamp)
    probes = run.get("probes") or []
    disagreements = sum(len(p.get("disagreements") or []) for p in probes)
    print(f"{len(probes)} probes, {disagreements} disagreements, ran={run.get('ran')}")

    if args.into is None:
        print(json.dumps(run)[:200] + " ...")
        return
    doc = json.loads(args.into.read_text(encoding="utf-8"))
    doc[args.key] = run
    args.into.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\r\n")
    print(f"written into {args.into.name} under {args.key!r}")


if __name__ == "__main__":
    main()
