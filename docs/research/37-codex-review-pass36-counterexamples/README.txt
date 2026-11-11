Pass 36 adversarial review of 3aa4a44..38ae076 on v2-rethink.
No tracked files changed.

Run from the repository root using v2/.venv/Scripts/python.exe:

v2/.review36/check_review.py
  Small counterexamples, a 100-query full-scan enumeration comparison, renderer
  --check against a copied document, frame verification. Results: check_output.txt.

v2/.review36/real_records.py
  Rebuilds the pilot graph in memory from the existing GraphML, reads frozen frames,
  measures the effect of retaining coincident parallel alternatives. No graph writes.
  Results: real_records_results.json. About 95 seconds on this machine.
  The parallel-only comparison preserves normal forward/reverse pairing and leaves
  self-loop groups unchanged; it is a lower-bound demonstration of lost multiplicity.

v2/.review36/real_ties.py
  Rebuilds the graph in memory and checks all 512,633 structures. Both reported
  discarded genuine-tie candidates are UNIQUE exact minima, with no equal occurrence.
  Results: real_ties_results.json. About three minutes including graph preparation.

v2/.review36/find_false_tie.py
  Small synthetic demonstration of the same mislabeled genuine-tie diagnostic.

v2/.review36/find_rounding.py
  Fixed-seed counterexample: subdivide perturbs exact geometry through midpoint
  rounding, removes a genuine rational tie and moves a retained D position.
  This does not refute D's invariance under transformations that preserve exact geometry.

v2/.review36/find_window.py
  The transformation window (unlike measure_point's window) omits numerical slack.
  A record at the computed band boundary disappears even with unchanged geometries.

Existing v2/tests/test_frames.py: all 34 tests passed. Windows sandbox directory
creation with mode 0700 caused permission errors in the ordinary pytest tmp fixture;
the successful in-process run changed only Path.mkdir's mode to inherited 0777 for
test temporary directories, and used --basetemp under .review36 with cache disabled.
