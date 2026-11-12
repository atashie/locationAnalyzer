Pass 37 runnable counterexamples
===============================

Run in PowerShell from the repository root. Use the repository's existing Python;
no downloads or extra packages are needed. All writes are confined to this review
directory during preparation; running these scripts with -B writes no bytecode.
Each script exits nonzero on a failed assertion. PASS means the finding/check
reproduced, not that the reviewed plan is correct.

Example:
  & .\v2\.venv\Scripts\python.exe -B .\docs\research\38-codex-review-pass37-counterexamples\f01_rounded_argmin.py

Run all nine scripts:
  Get-ChildItem -LiteralPath .\docs\research\38-codex-review-pass37-counterexamples -Filter *.py | ForEach-Object {
      & .\v2\.venv\Scripts\python.exe -B $_.FullName
      if ($LASTEXITCODE -ne 0) { throw "Reproducer failed: $($_.Name)" }
  }

f01_rounded_argmin.py       F1: certified in-domain real/rounded argmin flips;
                           prefix and fraction composition rounding failures.
f02_witnesses.py            F2: W1's required answer contradicts fsum; also
                           independently recomputes W2 and W3's numbers.
f03_scalar_search.py        F3: existing CSR/SciPy scalar search returns 1001 s
                           where whole-journey fsum ranking/oracle selects 2 s.
f04_csr_views.py            F4: cost-selected collapse loses objective 1; ties
                           depend on insertion order; zero weights rejected.
f05_interval_formulas.py    F5: two unchosen same-edge operation sequences give
                           different seconds and published-threshold verdicts.
f06_transformation_impact.py F6: original convention pairs agree, but a lawful
                           midpoint subdivision flips A's encoded verdict.
f07_t0_exact_scope.py       F7: T0's exact squared-distance diagnostic coexists
                           with a float endpoint label for an interior minimum.
f08_w2_factoring.py         F8: factored fsum reaches W2; already-rounded
                           products do not. No general projection claim follows.
arithmetic_checks.py       Sound side claims: rational sqrt midpoint algorithm,
                           an in-domain CPython hypot rounding miss, exact
                           factor-three calculation, qualified fsum behavior.

REPORT.md states claims, severities, evidence, required plan corrections,
sound checks, dependencies and the limitations of these experiments.

The W1 script temporarily replaces a Python property in memory and restores it
in finally. It does not modify toy.py. Other imports are read-only; the T0 pilot
is imported without invoking main(), which would otherwise write its artifact.
The central irrational witnesses use integer/Fraction comparisons as their
certificates. Decimal is used only for displaying the central irrational value.
