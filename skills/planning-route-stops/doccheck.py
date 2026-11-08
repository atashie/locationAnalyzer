#!/usr/bin/env python3
"""Check the skill's prose against the skill's code. No network.

    python doccheck.py [path/to/worked-example-dir]

Documentation drifts silently, and the drift is invisible in exactly the way a stale
published figure is: it reads as derived. This caught the docs still claiming a basemap
reduced to "636 points" one commit after a fix changed it to 673 — the sentence describing
the fix had not been updated by the fix.

Checks:
  * every file the prose names in backticks exists
  * every `--flag` the prose names is a real argparse argument
  * every spec field the prose promises is actually read by the tool
  * the rule count in the heading matches the numbered headings
  * figures quoted about the worked example match its JSON, where one is given
  * a worked example's page generator names the repo that built it
  * selftest.py passes
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = ("SKILL.md", "comparison-page.md", "endpoint-notes.md", "research-brief.md")
CODE = ("itinerary_compare.py", "basemap.py", "corridor_scan.py", "selftest.py")
# names that legitimately appear in prose but live in the caller's workspace, not here
EXTERNAL = {"build_page.py", "trip.json", "spec.json", "measured.json", "basemap.json",
            "experiments.json", "motorways_raw.json", "states_raw.json"}
# argparse provides these; they are not ours to define
BUILTIN_FLAGS = {"--help"}
SPEC_FIELDS = ("depart_h", "utc_offset", "last_entry", "facilities", "always",
               "dwell_min", "cost_usd", "corridor", "days", "status")

RULE_WORDS = {"three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
              "nine": 9, "ten": 10}


def main(example_dir=None):
    docs = {n: io.open(os.path.join(HERE, n), encoding="utf-8").read()
            for n in DOCS if os.path.exists(os.path.join(HERE, n))}
    code = {n: io.open(os.path.join(HERE, n), encoding="utf-8").read()
            for n in CODE if os.path.exists(os.path.join(HERE, n))}
    blob = "".join(docs.values())
    allcode = "".join(code.values())
    problems = []

    for name in sorted(set(re.findall(r"`([A-Za-z0-9_]+\.(?:py|md|json))`", blob))):
        if name in EXTERNAL:
            continue
        if not os.path.exists(os.path.join(HERE, name)):
            problems.append(f"prose names `{name}`, which is not in the skill directory")

    declared = set(re.findall(r'add_argument\("(--[a-z-]+)"', allcode))
    # CSS custom properties look exactly like CLI flags in backticks; they are not.
    css_tokens = set(re.findall(r"var\((--[a-z-]+)\)", blob))
    css_tokens |= set(re.findall(r"(--[a-z-]+)\s*:", blob))
    mentioned = set(re.findall(r"`(--[a-z-]+)`", blob))
    for flag in sorted(mentioned - declared - BUILTIN_FLAGS - css_tokens):
        problems.append(f"prose names flag `{flag}`, which no tool defines")

    for field in SPEC_FIELDS:
        if f"`{field}`" in blob and field not in allcode:
            problems.append(f"prose promises spec field `{field}`, no tool reads it")

    skill = docs.get("SKILL.md", "")
    m = re.search(r"## The (\w+) rules", skill)
    if m:
        want = RULE_WORDS.get(m.group(1).lower())
        got = len(re.findall(r"^### \d+\. ", skill, re.M))
        if want != got:
            problems.append(f"SKILL.md heading says '{m.group(1)} rules' but there are {got}")
    else:
        problems.append("SKILL.md has no '## The N rules' heading")

    if example_dir:
        bm_path = os.path.join(example_dir, "basemap.json")
        if os.path.exists(bm_path):
            counts = json.load(open(bm_path, encoding="utf-8")).get("counts", {})
            for key, label in (("road_fragments", "fragment count"),
                               ("road_chains", "chain count"),
                               ("roads_kept", "kept road points")):
                val = counts.get(key)
                if val is None:
                    continue
                # any other 3-5 digit number adjacent to the same words is suspicious
                if str(val) not in blob:
                    problems.append(
                        f"worked example reports {label} = {val}; that figure appears "
                        f"nowhere in the prose (stale number likely)")

        # A published page is the only copy that travels. One session was handed the live URL,
        # rebuilt the routing and the projection from the page alone, then declined to change
        # anything because nothing on the page said where its spec and generator lived.
        gen_path = os.path.join(example_dir, "build_page.py")
        if os.path.exists(gen_path):
            gen = io.open(gen_path, encoding="utf-8").read()
            if "<strong>Source</strong>" not in gen:
                problems.append("build_page.py emits no Source provenance block; a page that "
                                "does not name its own repo cannot be picked up elsewhere")
            else:
                if not re.search(r"github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", gen):
                    problems.append("build_page.py has a Source block that names no "
                                    "github.com/<owner>/<repo>")
                if "republish" not in gen.lower():
                    problems.append("build_page.py Source block never says to republish to the "
                                    "same URL; publishing without it forks the artifact")

    rc = subprocess.run([sys.executable, os.path.join(HERE, "selftest.py")],
                        capture_output=True, text=True)
    summary = [l for l in rc.stdout.strip().splitlines() if re.match(r"^\d+/\d+ pass", l)]
    print(f"selftest: {summary[-1] if summary else 'no result'}")
    if rc.returncode != 0:
        problems.append("selftest.py is failing")

    print(f"docs checked: {', '.join(sorted(docs))}")
    print(f"tools checked: {', '.join(sorted(code))}")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nprose and code agree")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
