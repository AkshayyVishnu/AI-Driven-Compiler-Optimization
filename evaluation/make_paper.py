"""
Render Report/DeepCompile_Paper.md from Report/paper_template.md.

Every number in the paper's Results section is a {{placeholder}} resolved from
files under Report/experiments/. Unresolved placeholders abort the build, which
is the audit: no number can appear in the paper without a source file.
"""

import csv
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXP = os.path.join(ROOT, "Report", "experiments")
sys.path.insert(0, ROOT)


def jl(p):
    return json.load(open(os.path.join(EXP, p), encoding="utf-8"))


def raw_rows(cfg):
    out = {}
    for p in glob.glob(os.path.join(EXP, "raw", cfg, "*.json")):
        r = json.load(open(p, encoding="utf-8"))
        out[r["tc"]] = r
    return out


def pct(n, d):
    return f"{100.0 * n / d:.1f}" if d else "n/a"


def md_table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def hit(row):
    return bool(row.get("detected")) and all(row["detected"].values())


def main():
    meta = jl("expected_categories.json")
    g = jl("aggregate_gpp_wall.json")
    b = jl("aggregate_rule_basic.json")
    o = jl("aggregate_rule_orch.json")
    post = jl("postpass_rule_basic.json")
    env = jl("environment.json")
    rb, ro, rg = raw_rows("rule_basic"), raw_rows("rule_orch"), raw_rows("gpp_wall")
    V = {}

    headline = [t for t, m in meta.items() if m["headline"]]
    V["n_cases_total"] = len(meta)
    V["n_headline"] = b["headline_cases"]
    V["n_supported"] = b["supported_cases"]
    V["n_unsupported"] = b["headline_cases"] - b["supported_cases"]
    V["dc_det"] = b["detected_overall"]
    V["dc_det_pct"] = pct(b["detected_overall"], b["headline_cases"])
    V["dc_cov_hits"] = round(b["detection_rate_within_coverage"] * b["supported_cases"])
    V["dc_cov_pct"] = pct(V["dc_cov_hits"], b["supported_cases"])
    V["gcc_det"] = g["detected_overall"]
    V["gcc_det_pct"] = pct(g["detected_overall"], g["headline_cases"])
    V["gcc_cov_hits"] = round(g["detection_rate_within_coverage"] * g["supported_cases"])
    V["gcc_cov_pct"] = pct(V["gcc_cov_hits"], g["supported_cases"])
    V["orch_det"] = o["detected_overall"]

    ver = b["ver_status_counts"]
    V["n_pass"], V["n_rollback"], V["n_timeout"] = ver.get("PASS", 0), ver.get("ROLLBACK", 0), ver.get("TIMEOUT", 0)
    V["o_pass"], V["o_rollback"], V["o_timeout"] = (o["ver_status_counts"].get(k, 0) for k in ("PASS", "ROLLBACK", "TIMEOUT"))
    V["n_rows"] = b["rows_total"]

    ok = [r for r in rb.values() if "error" not in r]
    V["n_with_transform"] = sum(1 for r in ok if r.get("transformations"))
    V["n_code_changed"] = sum(1 for r in ok if r.get("code_changed"))
    V["n_ok_rows"] = len(ok)
    tcount = Counter(x for r in ok for x in r.get("transformations", []))
    V["n_transform_total"] = sum(tcount.values())
    V["n_transform_types"] = len(tcount)
    V["rollback_cases"] = ", ".join(sorted(t for t, r in rb.items() if r.get("ver_status") == "ROLLBACK"))
    V["timeout_cases"] = ", ".join(sorted(t for t, r in rb.items() if r.get("error") == "timeout"))
    V["det_corrected"] = b["corrected_detector_judged"]
    V["det_corrected_den"] = b["corrected_denominator"]
    V["det_corrected_cases"] = ", ".join(sorted(t for t, r in rb.items() if r.get("corrected_detector")))
    V["fp_sol"], V["fp_sol_den"] = b["fp_on_sol"], b["fp_denominator"]
    V["fp_sol_cases"] = ", ".join(sorted(t for t, r in rb.items() if r.get("fp_on_sol")))

    pc = post["counts"]
    V["sol_checked"] = sum(pc.values()) - pc.get("unchecked", 0)
    V["sol_corrected"] = pc.get("corrected", 0)
    V["sol_invisible"] = pc.get("bug_not_visible_in_output", 0)
    V["sol_not_fixed"] = pc.get("not_fixed", 0)
    V["sol_regression"] = pc.get("regression", 0)

    rbk = [t for t, r in rb.items() if r.get("ver_status") == "ROLLBACK"]
    V["rollback_no_transform"] = sum(1 for t in rbk if not rb[t].get("transformations"))
    V["rollback_no_transform_cases"] = ", ".join(sorted(t for t in rbk if not rb[t].get("transformations")))
    V["rollback_with_transform_cases"] = ", ".join(sorted(t for t in rbk if rb[t].get("transformations"))) or "none"
    V["rollback_with_transform"] = len(rbk) - V["rollback_no_transform"]
    nf = [r["tc"] for r in post["rows"] if r["outcome"] == "not_fixed"]
    V["not_fixed_unchanged"] = sum(1 for t in nf if not rb[t].get("code_changed"))
    V["slowest_case"] = max((r for r in ok), key=lambda r: r["pipeline_s"])["tc"]

    # orchestration: the cases where orchestrated outcome differs from basic
    diffs = [(t, rb[t]["ver_status"], ro[t]["ver_status"], ro[t].get("workflow_status"), ro[t].get("iterations"))
             for t in ro if t in rb and "error" not in ro[t] and "error" not in rb[t]
             and (rb[t]["ver_status"] != ro[t]["ver_status"] or ro[t].get("iterations"))]
    V["orch_escalated"] = sum(1 for r in ro.values() if r.get("workflow_status") == "ESCALATE")
    V["orch_escalated_cases"] = ", ".join(t for t, *_ in diffs if ro[t].get("workflow_status") == "ESCALATE")
    flips = [t for t, bs, os_, *_ in diffs if bs == "ROLLBACK" and os_ == "PASS"]
    V["orch_flip_cases"] = ", ".join(flips) or "none"

    # multi-rule cases, per case
    mr = []
    for t in ("TC56", "TC57", "TestCase1"):
        r, gr = rb.get(t, {}), rg.get(t, {})
        d = r.get("detected", {})
        gd = gr.get("detected", {})
        mr.append([t, len(d), sum(d.values()), sum(gd.values())])
    V["tc56_hit"], V["tc56_n"] = mr[0][2], mr[0][1]
    V["tc57_hit"], V["tc57_n"] = mr[1][2], mr[1][1]
    V["tc1_hit"], V["tc1_n"] = mr[2][2], mr[2][1]

    # per-category detection table
    cat = defaultdict(lambda: [0, 0, 0, False])
    for t in headline:
        m = meta[t]
        c = m["expected"][0]
        cat[c][0] += 1
        cat[c][1] += int(hit(rb[t])) if t in rb and "error" not in rb[t] else 0
        cat[c][2] += int(hit(rg[t])) if t in rg else 0
        cat[c][3] = m["supported"]
    cat_rows = [[c, n, d, gcc, "yes" if s else "no"] for c, (n, d, gcc, s) in sorted(cat.items())]

    # perf
    perf = list(csv.DictReader(open(os.path.join(EXP, "perf_rule_basic.csv"), encoding="utf-8")))
    valid = [p for p in perf if p["speedup_pct"] not in ("n/a", "")]
    V["perf_rows"] = len(perf)
    V["perf_valid"] = len(valid)
    V["perf_noise"] = sum(1 for p in valid if p["below_noise_floor"] == "True")
    sp = [float(p["speedup_pct"]) for p in valid]
    V["perf_min"], V["perf_max"] = f"{min(sp):.1f}", f"{max(sp):.1f}"
    V["perf_max_ms"] = f"{max(max(float(p['original_ms']), float(p['optimized_ms'])) for p in valid):.3f}"

    # timing
    ts = sorted(r["pipeline_s"] for r in ok)
    V["pipe_median_s"] = f"{ts[len(ts) // 2]:.2f}"
    V["pipe_max_s"] = f"{ts[-1]:.2f}"
    V["compiler"] = env["g++"]
    V["python"] = env["python"]
    V["os"] = env["os"]

    tables = {
        "T_DETECTION": md_table(
            ["System", f"Detected (all {V['n_headline']} headline cases)", "Rate",
             f"Within detector coverage ({V['n_supported']} cases)", "Rate"],
            [["DeepCompile (rule-only)", f"{V['dc_det']}/{V['n_headline']}", V["dc_det_pct"] + " %",
              f"{V['dc_cov_hits']}/{V['n_supported']}", V["dc_cov_pct"] + " %"],
             ["g++ -O2 -Wall -Wextra (baseline)", f"{V['gcc_det']}/{V['n_headline']}", V["gcc_det_pct"] + " %",
              f"{V['gcc_cov_hits']}/{V['n_supported']}", V["gcc_cov_pct"] + " %"]]),
        "T_CATEGORY": md_table(["Bug category", "Cases", "DeepCompile hits", "g++ hits", "Category reachable by a detector"], cat_rows),
        "T_MULTI": md_table(["Case", "Expected categories", "DeepCompile found", "g++ found"], mr),
        "T_PIPELINE": md_table(
            ["Configuration", "Verification PASS", "ROLLBACK", "TIMEOUT"],
            [["Basic pipeline", V["n_pass"], V["n_rollback"], V["n_timeout"]],
             ["Orchestrated (with refinement)", V["o_pass"], V["o_rollback"], V["o_timeout"]]]),
        "T_CORRECTION": md_table(
            ["Outcome (original vs. reference solution output)", "Cases"],
            [["mismatch -> match (output-verified correction)", V["sol_corrected"]],
             ["match -> match (bug not visible in output)", V["sol_invisible"]],
             ["mismatch -> mismatch (not fixed)", V["sol_not_fixed"]],
             ["match -> mismatch (regression)", V["sol_regression"]]]),
        "T_TRANSFORMS": md_table(["Transformation", "Applications"], sorted(([k, v] for k, v in tcount.items()), key=lambda x: -x[1])),
        "T_PERF": md_table(
            ["Case", "Original (ms)", "Optimized (ms)", "Speedup (%)", "Below 1 ms noise floor"],
            [[p["tc"], p["original_ms"], p["optimized_ms"], p["speedup_pct"], p["below_noise_floor"]] for p in perf]),
    }

    tpl = open(os.path.join(ROOT, "Report", "paper_template.md"), encoding="utf-8").read()
    for k, v in tables.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    for k, v in V.items():
        tpl = tpl.replace("{{" + k + "}}", str(v))
    left = sorted(set(re.findall(r"\{\{(\w+)\}\}", tpl)))
    if left:
        raise SystemExit(f"Unresolved placeholders (audit failed): {left}")
    out = os.path.join(ROOT, "Report", "DeepCompile_Paper.md")
    open(out, "w", encoding="utf-8").write(tpl)
    json.dump(V, open(os.path.join(EXP, "paper_values.json"), "w", encoding="utf-8"), indent=2)
    print("wrote", out, f"({len(tpl.split())} words)")


if __name__ == "__main__":
    main()
