"""Phase 1: the two acquisition hazards, tested without a network.

Both are in the plan's S4.1 and one was demonstrated by Codex pass-10 H5. Neither is reachable by a
happy-path test, which is exactly why they survived: the first needs a *changed request* and the
second needs an *interrupted download*. The downloader is injected so both can be provoked.
"""
import errno
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from locfinder.places.acquire import Acquisition, acquire, read_state, state_path

#: The competing-writer tests need a *separate process*, because an OS lock is held per process.
V2 = Path(__file__).resolve().parents[1]

A = Acquisition(overture_type="place", release="2026-10-21.0", bbox="-79.2,35.7,-78.5,36.15")
A2 = Acquisition(overture_type="place", release="2026-11-21.0", bbox="-79.2,35.7,-78.5,36.15")
B = Acquisition(overture_type="place", release="2026-10-21.0", bbox="-79.35,35.55,-78.35,36.30")


def leftovers(d):
    """Everything in the directory except the lock file, which is created once and deliberately
    never removed: unlinking it is what let one process release another's lock (pass-12 H1)."""
    return sorted(q.name for q in d.iterdir() if not q.name.endswith(".lock"))


def writer(payload: str):
    def _dl(tmp, want):
        tmp.write_text(payload, encoding="utf-8")
    return _dl


def test_a_fresh_acquisition_downloads_and_records_what_it_fetched(tmp_path):
    raw = tmp_path / "raw.parquet"
    path, downloaded = acquire(raw, A, downloader=writer("A-bytes"), log=lambda *a: None)
    assert downloaded and path.read_text(encoding="utf-8") == "A-bytes"
    assert read_state(raw) == A.as_dict()


def test_the_same_request_reuses_the_file(tmp_path):
    raw = tmp_path / "raw.parquet"
    acquire(raw, A, downloader=writer("A-bytes"), log=lambda *a: None)
    _, downloaded = acquire(raw, A, downloader=writer("SHOULD-NOT-RUN"), log=lambda *a: None)
    assert not downloaded and raw.read_text(encoding="utf-8") == "A-bytes"


def test_a_changed_bbox_forces_a_re_download():
    """The hazard that let an evaluation-extent download back a routing-extent claim: the original
    `fetch_places.fetch_overture` returned any existing raw file regardless of what was asked for."""
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        raw = Path(d) / "raw.parquet"
        acquire(raw, A, downloader=writer("eval-extent"), log=lambda *a: None)
        _, downloaded = acquire(raw, B, downloader=writer("routing-extent"),
                                log=lambda *a: None)
        assert downloaded and raw.read_text(encoding="utf-8") == "routing-extent"
        assert read_state(raw)["bbox"] == B.bbox


def test_a_changed_release_forces_a_re_download(tmp_path):
    raw = tmp_path / "raw.parquet"
    acquire(raw, A, downloader=writer("old"), log=lambda *a: None)
    newer = Acquisition(overture_type="place", release="2026-11-21.0", bbox=A.bbox)
    _, downloaded = acquire(raw, newer, downloader=writer("new"), log=lambda *a: None)
    assert downloaded and read_state(raw)["release"] == "2026-11-21.0"


def test_a_raw_file_with_no_state_is_never_trusted(tmp_path):
    raw = tmp_path / "raw.parquet"
    raw.write_text("mystery", encoding="utf-8")
    _, downloaded = acquire(raw, A, downloader=writer("known"), log=lambda *a: None)
    assert downloaded and raw.read_text(encoding="utf-8") == "known"


def test_an_interrupted_download_leaves_the_previous_pair_intact(tmp_path):
    """Codex pass-10 H5. Writing over the raw file while its state stayed valid meant a failed
    download left the NEW bytes labelled with the OLD release, and the next request for that
    release reused them."""
    raw = tmp_path / "raw.parquet"
    acquire(raw, A, downloader=writer("A-bytes"), log=lambda *a: None)

    def fails(tmp, want):
        tmp.write_text("B-partial", encoding="utf-8")
        raise RuntimeError("connection dropped")

    with pytest.raises(RuntimeError, match="connection dropped"):
        acquire(raw, B, downloader=fails, log=lambda *a: None)

    # the previous file and its label are untouched, and no partial file survives
    assert raw.read_text(encoding="utf-8") == "A-bytes"
    assert read_state(raw) == A.as_dict()
    assert leftovers(tmp_path) == ["raw.parquet", "raw.parquet.state"]

    # and asking for A again legitimately reuses A, not B's bytes
    _, downloaded = acquire(raw, A, downloader=writer("SHOULD-NOT-RUN"), log=lambda *a: None)
    assert not downloaded and raw.read_text(encoding="utf-8") == "A-bytes"


def test_an_interrupt_cannot_promote_a_partial_file_either(tmp_path):
    """`BaseException`, not `Exception`: Ctrl-C during a download must behave like a failure."""
    raw = tmp_path / "raw.parquet"

    def interrupted(tmp, want):
        tmp.write_text("partial", encoding="utf-8")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        acquire(raw, A, downloader=interrupted, log=lambda *a: None)
    assert not raw.exists() and read_state(raw) is None


def test_a_downloader_that_writes_nothing_is_an_error_not_an_empty_success(tmp_path):
    raw = tmp_path / "raw.parquet"
    with pytest.raises(RuntimeError, match="produced no file"):
        acquire(raw, A, downloader=lambda tmp, want: None, log=lambda *a: None)
    assert read_state(raw) is None


def test_a_corrupt_state_file_is_treated_as_unknown(tmp_path):
    raw = tmp_path / "raw.parquet"
    raw.write_text("bytes", encoding="utf-8")
    state_path(raw).write_text("{not json", encoding="utf-8")
    assert read_state(raw) is None
    _, downloaded = acquire(raw, A, downloader=writer("fresh"), log=lambda *a: None)
    assert downloaded


def test_the_state_file_is_readable_json_next_to_the_raw_file(tmp_path):
    raw = tmp_path / "raw.parquet"
    acquire(raw, A, downloader=writer("x"), log=lambda *a: None)
    assert state_path(raw) == tmp_path / "raw.parquet.state"
    assert json.loads(state_path(raw).read_text(encoding="utf-8"))["type"] == "place"


def test_two_acquisitions_cannot_interleave_into_a_wrong_label(tmp_path):
    """Codex pass-11 H1, reproduced deterministically rather than by timing luck. With a shared
    temporary filename and no lock, the schedule "A replaces raw -> B commits B -> A writes state A"
    left B's bytes labelled A and both calls returned success. The lock makes the whole
    check-download-commit sequence exclusive, so a competing acquisition waits instead.

    The competitor has to be a *separate process*: the lock is now an OS lock on a file handle, and
    those are owned per process, so a re-entrant call from inside the same process would be granted
    the lock it already holds. That is correct behaviour for the thing we are defending against —
    two builds racing — and it is why this test spawns a child.
    """
    raw = tmp_path / "raw.parquet"
    acquire(raw, A, downloader=writer("A-bytes"), log=lambda *a: None)

    program = textwrap.dedent(f"""
        import pathlib, sys
        sys.path.insert(0, {str(V2)!r})
        import locfinder.places.acquire as acq
        acq.LOCK_TIMEOUT_S = 0.4
        want = acq.Acquisition(overture_type="place", release="2026-10-21.0",
                               bbox="-79.35,35.55,-78.35,36.30")
        try:
            acq.acquire(pathlib.Path({str(raw)!r}), want,
                        downloader=lambda tmp, w: tmp.write_text("B-bytes"),
                        log=lambda *a: None)
        except TimeoutError:
            print("TIMEOUT", flush=True)
            sys.exit(7)
        print("COMMITTED", flush=True)
    """)

    def downloader_that_races(tmp, want):
        tmp.write_text("A-bytes-v2", encoding="utf-8")
        done = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True)
        assert done.returncode == 7, f"child should have timed out, got {done.returncode}: {done.stdout}{done.stderr}"
        assert "TIMEOUT" in done.stdout

    acquire(raw, A2, downloader=downloader_that_races, log=lambda *a: None)
    # the competitor never committed, so the file and its label are the ones this call wrote
    assert raw.read_text(encoding="utf-8") == "A-bytes-v2"
    assert read_state(raw) == A2.as_dict()


def test_the_lock_is_released_when_the_holder_dies(tmp_path):
    """Codex pass-12 H1. The old lock was a file whose *content* claimed ownership, so a crashed
    download left it behind and a staleness threshold had to guess when to break it — which let a
    waiter break a lock a live download still held, and let the original holder then unlink the
    replacement. An OS lock is released by the kernel on process death, so there is nothing to
    guess and nothing to reclaim."""
    raw = tmp_path / "raw.parquet"
    marker = tmp_path / "child-acquired"
    killer = textwrap.dedent(f"""
        import os, sys, pathlib
        sys.path.insert(0, {str(V2)!r})
        import locfinder.places.acquire as acq
        with acq._exclusive(pathlib.Path({str(raw)!r})):
            pathlib.Path({str(marker)!r}).write_text("held")
            os._exit(1)      # die holding the lock, with no cleanup of any kind
    """)
    died = subprocess.run([sys.executable, "-c", killer], capture_output=True, text=True)
    # Prove the child reached the inside of the lock. Without this the test passes just as well
    # when the child dies on import, which would make it evidence of nothing (Codex pass-13).
    assert marker.exists(), f"child never held the lock: {died.stdout}{died.stderr}"
    assert died.returncode == 1
    lock = raw.with_suffix(raw.suffix + ".lock")
    assert lock.exists(), "the lock file is deliberately never unlinked"

    # ...and it does not block the next acquisition for a moment, let alone an hour.
    import locfinder.places.acquire as acq
    original = acq.LOCK_TIMEOUT_S
    acq.LOCK_TIMEOUT_S = 1.0
    try:
        _, downloaded = acquire(raw, A, downloader=writer("fresh"), log=lambda *a: None)
    finally:
        acq.LOCK_TIMEOUT_S = original
    assert downloaded and raw.read_text(encoding="utf-8") == "fresh"


def test_the_temporary_location_is_process_unique(tmp_path):
    """A shared `raw.partial` let one acquisition's cleanup delete another's download."""
    import os
    raw = tmp_path / "raw.parquet"
    seen = []
    acquire(raw, A, downloader=lambda tmp, want: (seen.append(tmp), tmp.write_text("x")),
            log=lambda *a: None)
    assert str(os.getpid()) in seen[0].parent.name


def test_a_sidecar_the_downloader_writes_cannot_collide_with_our_state_file(tmp_path):
    """The real defect, found on disk. The `overturemaps` CLI writes `<output>.state` beside its
    output — the same name this module gives its own state file. Downloading straight to `raw` put
    the CLI's JSON *on* our state file, where it parses but does not describe the request, so
    `describes()` returned False and the pair re-downloaded on every run forever. Found as
    `data/slice/overture_places_raw.parquet.state` holding the CLI's schema.

    The download now happens inside a temporary directory that is removed wholesale, so nothing the
    downloader writes beside its output can reach a path this module owns."""
    raw = tmp_path / "raw.parquet"

    def writes_a_sidecar(tmp, want):
        tmp.write_text("real-bytes", encoding="utf-8")
        # exactly what the CLI does, and exactly our own naming convention
        tmp.with_suffix(tmp.suffix + ".state").write_text('{"theme": "places"}', encoding="utf-8")

    acquire(raw, A, downloader=writes_a_sidecar, log=lambda *a: None)

    # our state survived and still describes the request, so the next call reuses the file
    assert read_state(raw) == A.as_dict()
    _, downloaded = acquire(raw, A, downloader=writer("SHOULD-NOT-RUN"), log=lambda *a: None)
    assert not downloaded and raw.read_text(encoding="utf-8") == "real-bytes"
    # and the sidecar left no litter behind at all
    assert leftovers(tmp_path) == ["raw.parquet", "raw.parquet.state"]


def test_a_failed_download_leaves_no_temporary_directory(tmp_path):
    raw = tmp_path / "raw.parquet"

    def fails(tmp, want):
        tmp.write_text("partial", encoding="utf-8")
        tmp.with_suffix(tmp.suffix + ".state").write_text("{}", encoding="utf-8")
        raise RuntimeError("dropped")

    with pytest.raises(RuntimeError, match="dropped"):
        acquire(raw, A, downloader=fails, log=lambda *a: None)
    assert leftovers(tmp_path) == []


def test_a_leftover_lock_file_does_not_block_anything(tmp_path):
    """A lock file that nobody holds is just a file. Under the old content-ownership scheme its
    mere existence blocked acquisition until a staleness threshold expired."""
    import locfinder.places.acquire as acq
    raw = tmp_path / "raw.parquet"
    lock = raw.with_suffix(raw.suffix + acq.LOCK_SUFFIX)
    lock.write_text("99999 0", encoding="utf-8")
    original = acq.LOCK_TIMEOUT_S
    acq.LOCK_TIMEOUT_S = 1.0
    try:
        _, downloaded = acquire(raw, A, downloader=writer("fresh"), log=lambda *a: None)
    finally:
        acq.LOCK_TIMEOUT_S = original
    assert downloaded and raw.read_text(encoding="utf-8") == "fresh"


def _patch_os_lock(monkeypatch, raising):
    """Replace the platform lock primitive, not `_try_lock` itself.

    Patching `_try_lock` would replace the code under test — it is where the errno is classified —
    so the fake has to sit one level down, at the call the real function makes.
    """
    import os as _os
    if _os.name == "nt":
        import msvcrt
        monkeypatch.setattr(msvcrt, "locking", lambda fd, mode, nbytes: raising())
    else:
        import fcntl
        monkeypatch.setattr(fcntl, "flock", lambda fd, op: raising())


def test_a_filesystem_that_cannot_lock_fails_immediately_rather_than_waiting(tmp_path, monkeypatch):
    """Codex pass-13 L1. `_try_lock` returned False for *any* `OSError`, so an unsupported lock
    operation was retried for up to 1,800 seconds and then reported as another process holding the
    lock. A failed lock operation is not evidence of a lock holder."""
    import locfinder.places.acquire as acq
    raw = tmp_path / "raw.parquet"

    def unsupported():
        raise OSError(errno.ENOLCK, "no locks available")

    _patch_os_lock(monkeypatch, unsupported)
    monkeypatch.setattr(acq, "LOCK_TIMEOUT_S", 0.2)   # so a regression hangs briefly, not for 30 min
    with pytest.raises(RuntimeError, match="does not support locking"):
        acquire(raw, A, downloader=writer("x"), log=lambda *a: None)


def test_a_genuine_contention_errno_is_waited_on_not_raised(tmp_path, monkeypatch):
    """The other side of the same rule, through the real `_try_lock`: a contention errno must be
    retried and then time out, not reported as a broken filesystem."""
    import locfinder.places.acquire as acq
    raw = tmp_path / "raw.parquet"

    def busy():
        raise OSError(errno.EACCES, "locked by another process")

    _patch_os_lock(monkeypatch, busy)
    monkeypatch.setattr(acq, "LOCK_TIMEOUT_S", 0.2)
    with pytest.raises(TimeoutError, match="still holds"):
        acquire(raw, A, downloader=writer("x"), log=lambda *a: None)

