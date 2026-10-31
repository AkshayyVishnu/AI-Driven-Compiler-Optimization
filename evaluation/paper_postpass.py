"""
Post-pass: split 'output matches SOL' into four outcomes by also comparing the
ORIGINAL program to the reference solution.

  mismatch -> match   : corrected (output-verified)
  match    -> match   : bug not visible in output (match proves nothing)
  mismatch -> mismatch: not fixed
  match    -> mismatch: regression
"""

import json
import os
import platform
import subprocess
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from evaluation.paper_experiments import EXP, case_path, load_meta, output_matches_sol, sol_path  # noqa: E402


def _read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def outcome(before, after):
    if before is False and after is True:
        return "corrected"
    if before is True and after is True:
        return "bug_not_visible_in_output"
    if before is False and after is False:
        return "not_fixed"
    if before is True and after is False:
        return "regression"
    return "unchecked"


def main(config="rule_basic"):
    meta = load_meta()
    rows, counts = [], Counter()
    for tc, m in meta.items():
        raw_path = os.path.join(EXP, "raw", config, f"{tc}.json")
        if not os.path.isfile(raw_path):
            continue
        row = json.load(open(raw_path, encoding="utf-8"))
        sp = sol_path(tc, m.get("sol_file"))
        if row.get("error") or not sp or not m.get("compiles_here") or m.get("nondeterministic") is not False:
            continue
        orig = _read(case_path(tc))
        rolled = row["ver_status"] in ("ROLLBACK", "FAIL") or row["sec_status"] == "ROLLBACK"
        opt_file = os.path.join(EXP, "opt_out", config, "OPT_" + os.path.basename(case_path(tc)))
        final = orig if rolled or not os.path.isfile(opt_file) else _read(opt_file)
        before = output_matches_sol(orig, _read(sp))
        after = output_matches_sol(final, _read(sp))
        o = outcome(before, after)
        counts[o] += 1
        rows.append({"tc": tc, "original_matches_sol": before, "final_matches_sol": after, "outcome": o})
    with open(os.path.join(EXP, f"postpass_{config}.json"), "w", encoding="utf-8") as fh:
        json.dump({"counts": dict(counts), "rows": rows}, fh, indent=2)
    print(dict(counts))
    for r in rows:
        print(r)


def write_environment():
    def run(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout.strip().splitlines()[0]
        except Exception as exc:
            return f"unavailable ({exc})"

    env = {
        "date": "2026-10-31",
        "os": platform.platform(),
        "cpu": platform.processor(),
        "python": sys.version.split()[0],
        "g++": run(["g++", "--version"]),
        "gemini_model_default": "gemini-2.5-flash",
        "ollama": "not evaluated (user decision); supported via src/llm/llm_client.py",
        "cppcheck": "not installed",
        "z3": "not installed (verification layer reports SKIPPED/UNKNOWN)",
        "clang": "not installed (no independent static-analysis oracle beyond g++ -Wall -Wextra)",
        "perf_harness_changes": [
            "added #undef main before the timing wrapper (previously never linked)",
            "overloaded shim supports int main(), int main(void), int main(int,char**)",
            "timer moved to a second translation unit using QueryPerformanceCounter on Windows "
            "(MinGW GCC 6 std::chrono ticks ~15 ms: 1936/2000 zero readings in a probe)",
        ],
        "case_timeout_s": 300,
        "timeout_explanation": "TC37 is an infinite loop: verification runs diff-test (10 s) plus the "
                               "perf benchmark (10 runs x 15 s timeout), exceeding the 300 s case limit.",
        "stdin": "empty for every executed program",
    }
    with open(os.path.join(EXP, "environment.json"), "w", encoding="utf-8") as fh:
        json.dump(env, fh, indent=2)


if __name__ == "__main__":
    write_environment()
    main(*(sys.argv[1:2] or ["rule_basic"]))
