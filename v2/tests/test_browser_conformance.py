"""The browser decoder, checked against Python's — S3.5.

`spikes/g3-render/worker.js` is the only implementation a household's answer actually passes
through, and a Python round trip cannot protect it. `worker_conformance.mjs` replays
`scripts/make_wire_vectors.py`'s vectors through the real worker, driven by its real message
protocol with `self` shimmed. This runs that under pytest, so the browser check happens on every
suite run rather than when someone remembers to type `node`.

It **skips** when node is absent and when the vectors have not been generated, and says which —
a silent pass would be worse than no test.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

import pytest

SPIKE = pathlib.Path(__file__).resolve().parents[1] / "spikes" / "g3-render"
HARNESS = SPIKE / "worker_conformance.mjs"
VECTORS = SPIKE / "fixtures" / "conformance" / "vectors.json"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH")
@pytest.mark.skipif(not VECTORS.exists(),
                    reason="run scripts/make_wire_vectors.py to generate the vectors")
def test_the_browser_decoder_agrees_with_the_python_one():
    out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, f"{out.stdout}\n{out.stderr}"
    assert "all browser conformance checks passed" in out.stdout
    # A harness that silently ran nothing would also exit 0.
    assert out.stdout.count("PASS  ") >= 25, out.stdout


@pytest.mark.skipif(not VECTORS.exists(), reason="vectors not generated")
def test_the_vectors_cover_every_status_code_the_published_layer_produces():
    """The real-window group is only evidence if the window actually contains every code. The
    generator refuses to write one that does not; this asserts the artifact on disk kept that
    property, so a stale regeneration cannot quietly weaken the check."""
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    assert data["encoding"] == "published-v2"
    real = [g for g in data["groups"] if "published layer window" in g["name"]]
    assert real, "no real-layer group in the vectors"
    present = set(real[0]["status_codes_present"])
    assert {0, 1, 2} <= present, f"the window is missing a status code: {sorted(present)}"
