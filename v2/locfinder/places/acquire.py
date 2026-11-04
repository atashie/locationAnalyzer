"""Acquiring an Overture theme safely. Phase 1, shared by `scripts/fetch_places.py` and
`scripts/fetch_buildings.py`.

Two hazards live here, both named in the plan's S4.1 and one of them demonstrated by Codex pass-10
H5. Keeping them in one tested function means neither script can reintroduce them.

**A raw file must not be reused for a request it does not answer.** `fetch_places.py` originally
returned any existing `overture_places_raw.parquet` regardless of the release *or the bounding box*
asked for, after which `partition_by_licence` labelled it with the **requested** release. That is
how an evaluation-extent download came to back a resolver that claims a routing-extent bound. A
state file records exactly what was fetched, and a mismatch forces a re-download.

**An interrupted download must not inherit the previous label.** Writing straight over the raw file
while its state file stayed valid meant a failed or cancelled download left the *new* bytes on disk
still described by the *old* state — and the next request for that old release reused them. So the
download goes to a temporary file, the state is removed, the bytes are moved into place, and only
then is the new state written. A failure at any point leaves the previous pair intact or no state at
all, never a lie.

**And two writers must not interleave.** Removing the state before replacing the bytes makes a
single writer's interruption safe but says nothing about concurrency, and the first version claimed
more than it delivered (Codex pass-11 H1): with a shared `raw.partial` filename and no lock, the
schedule "A replaces raw → B downloads and commits B → A writes state A" leaves B's bytes labelled
A, and both calls return success. Reproduced deterministically rather than by timing luck. So each
acquisition uses a **process-unique** temporary location, and the whole check-download-commit
sequence is serialised.

**The first lock still did not deliver that** (Codex pass-12 H1). A lock whose only owner is the
*content* of a file cannot be released safely. Staleness was 3600 s while the wait was 1800 s, so a
waiter would break a lock still held by a live 45-minute download; the original holder's `finally`
then unlinked the *replacement* lock and let a third process in. Codex reproduced all three
ownership failures by ageing a held lock. Writing a PID into the file does not fix it — PIDs are
reused, and mean nothing across machines on a shared filesystem.

So the lock is now owned by the **operating system** for the lifetime of the holding process:
`msvcrt.locking` on Windows, `fcntl.flock` elsewhere, on a handle held open for the duration. The
kernel releases it when the process dies, however it dies, so there is no abandoned lock to time
out of and no automatic reclaiming to get wrong. Waiting is a retry loop on the non-blocking call,
and the only remaining failure is a genuine timeout — which now really does mean someone else is
still working.

**And the downloader writes files we did not ask for.** The `overturemaps` CLI drops a sidecar
beside its output named `<output>.state` — exactly the convention this module uses for its own state
file. With the download going straight to `raw` that sidecar lands *on* our state file, and it
parses as valid JSON with different keys, so `describes()` returns False and the pair re-downloads
on every run forever: a silent permanent cache miss, found on disk in `data/slice/`. With a
process-unique temp file it merely orphans one sidecar per download. Patching the one filename would
leave the collision class open, so the download now goes into a **temporary directory** that is
removed wholesale: whatever the downloader writes beside its output is contained and cannot collide
with anything this module owns.

The lock is advisory and local: it serialises acquisitions on one machine, which is what the build
does. It does **not** make the *consumer* safe — a caller that acquires and then reads is still
racing anything that replaces the file in between — and the durable answer to that is S4.1's
immutable release bundles with an atomic manifest switch, not a longer-held lock.
"""
from __future__ import annotations

import errno
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

STATE_SUFFIX = ".state"
LOCK_SUFFIX = ".lock"
#: Seconds to wait for another acquisition to finish before giving up. Generous, because the thing
#: being waited for is a multi-minute download.
LOCK_TIMEOUT_S = 1800.0
#: Seconds between attempts while waiting.
LOCK_POLL_S = 0.2


#: `errno` values that mean "someone else holds it", as opposed to "locking does not work here".
#: Treating every `OSError` as contention made an unsupported filesystem look like a 30-minute
#: queue and then reported a holder that never existed (Codex pass-13 L1). A failed lock *operation*
#: is not evidence of a lock *holder*.
_CONTENTION_ERRNOS = frozenset({
    errno.EACCES,       # Windows: the range is locked by another process
    errno.EAGAIN,       # POSIX: EWOULDBLOCK, the usual flock contention code
    errno.EDEADLK,      # Windows msvcrt after its internal retries
})


def _try_lock(fd: int) -> bool:
    """Take an OS-owned exclusive lock on `fd` without blocking. True if it was taken.

    The kernel owns it, so it is released when this process exits by any route. There is no
    staleness threshold to tune and nothing for another process to reclaim, which is the whole
    point: a lock whose *content* claims ownership cannot be released safely by anyone but its
    creator, and the previous version released other processes' locks (Codex pass-12 H1).

    Raises on anything that is not contention, so a filesystem that cannot lock fails immediately
    and visibly instead of being retried for half an hour and then blamed on a phantom holder.
    """
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as exc:
        if exc.errno in _CONTENTION_ERRNOS:
            return False
        raise RuntimeError(
            f"cannot take an exclusive lock here ({exc.__class__.__name__}: {exc}). This is not "
            "contention — the lock operation itself failed, which usually means the filesystem "
            "does not support locking (some network shares). Acquisition cannot be serialised on "
            "this filesystem.") from exc


def _unlock(fd: int) -> None:
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass          # the handle is about to close, which releases it regardless


@contextmanager
def _exclusive(raw: Path, *, timeout_s: float | None = None):
    """Serialise the whole check-download-commit sequence for one raw file.

    The lock file is created once and **never deleted**: unlinking it is exactly what let one
    process release another's lock. An empty sidecar costs nothing, and its existence means
    nothing — only the OS lock held on it does.

    The timeout is read from the module global at call time, not bound as a default argument:
    binding it made the value un-overridable and a test that lowered `LOCK_TIMEOUT_S` waited the
    full 1800 s instead.
    """
    lock = raw.with_suffix(raw.suffix + LOCK_SUFFIX)
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + (LOCK_TIMEOUT_S if timeout_s is None else timeout_s)
    fd = os.open(lock, os.O_CREAT | os.O_RDWR)
    try:
        while not _try_lock(fd):
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"another acquisition still holds {lock.name}; it is an OS lock, so if that "
                    "process were gone the lock would already be released \u2014 this is a real wait")
            time.sleep(LOCK_POLL_S)
        try:
            yield
        finally:
            _unlock(fd)
    finally:
        os.close(fd)


def state_path(raw: Path) -> Path:
    return raw.with_suffix(raw.suffix + STATE_SUFFIX)


@dataclass(frozen=True)
class Acquisition:
    """What a raw file is, so a later run can tell whether it answers the question being asked."""

    overture_type: str
    release: str
    bbox: str

    def as_dict(self) -> dict:
        return {"type": self.overture_type, "release": self.release, "bbox": self.bbox}


def describes(state: dict | None, want: Acquisition) -> bool:
    if not state:
        return False
    return {k: state.get(k) for k in want.as_dict()} == want.as_dict()


def read_state(raw: Path) -> dict | None:
    sp = state_path(raw)
    if not sp.exists():
        return None
    try:
        return json.loads(sp.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def default_downloader(tmp: Path, want: Acquisition) -> None:
    cmd = [sys.executable, "-m", "overturemaps.cli", "download", f"--bbox={want.bbox}",
           "-f", "geoparquet", f"--type={want.overture_type}", "-o", str(tmp),
           "--release", want.release]
    print("running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def acquire(raw: Path, want: Acquisition, *, downloader=default_downloader,
            log=print) -> tuple[Path, bool]:
    """Ensure `raw` holds exactly `want`. Returns `(path, downloaded)`.

    `downloader` is injectable so the reuse and failure-safety rules can be tested without a
    network — which is the point, because the failure they prevent only happens on interruption.
    """
    with _exclusive(raw):
        have = read_state(raw)
        if raw.exists() and describes(have, want):
            log(f"reusing {raw.name}: release {want.release}, bbox {want.bbox}")
            return raw, False
        if raw.exists():
            if have:
                log(f"re-downloading {raw.name}: it holds release {have.get('release')} / bbox "
                    f"{have.get('bbox')}, not {want.release} / {want.bbox}")
            else:
                log(f"re-downloading {raw.name}: no state file, so what it holds is unknown")

        # A directory, process-unique: one acquisition's cleanup cannot delete another's download,
        # and any sidecar the downloader writes beside its output is contained rather than left in
        # a namespace this module also uses.
        tmp_dir = raw.with_name(f".{raw.name}.{os.getpid()}.partial")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir(parents=True)
        tmp = tmp_dir / raw.name
        try:
            downloader(tmp, want)
            if not tmp.exists():
                raise RuntimeError(f"downloader produced no file at {tmp}")
            # Commit. State goes first, so there is no instant at which new bytes carry an old
            # label. `os.replace` is atomic within a volume, and the temp directory is a sibling of
            # the target, so the two are always on one volume.
            state_path(raw).unlink(missing_ok=True)
            tmp.replace(raw)
            state_path(raw).write_text(json.dumps(want.as_dict(), indent=1), encoding="utf-8")
        finally:
            # `finally`, so a KeyboardInterrupt cannot leave a partial directory behind either.
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return raw, True
