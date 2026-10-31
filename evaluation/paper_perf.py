"""
Standalone, sequential performance measurement for the paper.

Run AFTER the pipeline experiments finish (no other CPU load). For every
rule_basic case whose verification PASSED and whose code actually changed,
benchmark original vs optimized with PerfBenchmarker (min of N runs, -O0).
Timings below NOISE_MS are flagged: they are within timer/process noise.
"""

import csv
import glob
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src.verification.perf_benchmarker import PerfBenchmarker  # noqa: E402
from evaluation.paper_experiments import EXP, case_path  # noqa: E402

NOISE_MS = 1.0


def main(config: str = "rule_basic", runs: int = 10) -> None:
    bench = PerfBenchmarker(runs=runs)
    out_rows = []
    for raw in sorted(glob.glob(os.path.join(EXP, "raw", config, "*.json"))):
        row = json.load(open(raw, encoding="utf-8"))
        if row.get("error") or row.get("ver_status") != "PASS" or not row.get("code_changed"):
            continue
        orig_path = case_path(row["tc"])
        opt_path = os.path.join(EXP, "opt_out", config, "OPT_" + os.path.basename(orig_path))
        if not os.path.isfile(opt_path):
            continue
        res = bench.benchmark(open(orig_path, encoding="utf-8", errors="replace").read(),
                              open(opt_path, encoding="utf-8", errors="replace").read())
        out_rows.append({
            "tc": row["tc"], "transformations": ";".join(row.get("transformations", [])),
            "original_ms": round(res.original_ms, 4), "optimized_ms": round(res.optimized_ms, 4),
            "speedup_pct": round(res.speedup_pct, 2), "error": res.error or "",
            "below_noise_floor": max(res.original_ms, res.optimized_ms) < NOISE_MS,
        })
        # 0.0 ms means no timing line was produced (crash / UB / compile failure):
        # report n/a, never a 0% speedup.
        if res.error or res.original_ms <= 0 or res.optimized_ms <= 0:
            out_rows[-1]["speedup_pct"] = "n/a"
        print(out_rows[-1], flush=True)
    path = os.path.join(EXP, f"perf_{config}.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0]) if out_rows else ["tc"])
        w.writeheader()
        w.writerows(out_rows)
    print("wrote", path, len(out_rows), "rows")


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["rule_basic"]))
