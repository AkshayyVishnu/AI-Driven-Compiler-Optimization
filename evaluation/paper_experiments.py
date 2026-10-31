"""
Experiment runner for the paper.

  python evaluation/paper_experiments.py run --config rule_basic
  python evaluation/paper_experiments.py run --config gemini_orch --subset
  python evaluation/paper_experiments.py summarize --config rule_basic

Configs: rule_basic, rule_orch, gemini_basic, gemini_orch, gpp_wall (baseline).
Each case runs in its own subprocess with a hard timeout, so module-level
caches never leak between cases or configs. Optimizer output goes to
Report/experiments/opt_out/ (never MicroBenchmarks/Generated_optimisation).
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from evaluation.paper_metrics import aggregate, classify_finding, classify_text, score_detection  # noqa: E402

EXP = os.path.join(ROOT, "Report", "experiments")
TC_DIR = os.path.join(ROOT, "MicroBenchmarks", "Testcases")
SOL_DIR = os.path.join(ROOT, "MicroBenchmarks", "Solutions_to_testcase")

# One case per bug category (+ the two multi-rule cases) for the LLM configs.
SUBSET = ["TC01", "TC07", "TC12", "TC14", "TC15", "TC16", "TC17", "TC22", "TC23", "TC27",
          "TC32", "TC34", "TC35", "TC36", "TC44", "TC48", "TC49", "TC51", "TC52", "TC53",
          "TC54", "TC55", "TC56", "TC57"]


def case_path(tc: str) -> str:
    if tc == "TestCase1":
        return os.path.join(TC_DIR, "TestCase1_Lr_errors.cpp")
    hits = [p for p in glob.glob(os.path.join(TC_DIR, f"{tc}_*.cpp")) if "Copy" not in p]
    return hits[0]


def sol_path(tc: str, sol_file: Optional[str]) -> Optional[str]:
    if not sol_file:
        return None
    p = os.path.join(SOL_DIR, sol_file)
    return p if os.path.isfile(p) else None


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


# ── compile/run helpers (used for the SOL-output check and the g++ baseline) ──

def _gpp(args: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["g++"] + args, capture_output=True, text=True, timeout=timeout)


def _compile_run(code: str, workdir: str, name: str) -> Dict[str, Any]:
    src = os.path.join(workdir, name + ".cpp")
    exe = os.path.join(workdir, name + ".exe")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(code)
    try:
        cp = _gpp([src, "-o", exe, "-O0", "-w"])
    except subprocess.TimeoutExpired:
        return {"status": "compile_timeout"}
    if cp.returncode != 0:
        return {"status": "compile_error"}
    try:
        rp = subprocess.run([exe], capture_output=True, text=True, timeout=10, input="")
        return {"status": "ok", "stdout": rp.stdout.strip(), "rc": rp.returncode}
    except subprocess.TimeoutExpired:
        return {"status": "run_timeout"}


def output_matches_sol(final_code: str, sol_code: str) -> Optional[bool]:
    with tempfile.TemporaryDirectory(dir=_tmp_root()) as wd:
        a = _compile_run(final_code, wd, "final")
        b = _compile_run(sol_code, wd, "sol")
    if a["status"] != "ok" or b["status"] != "ok":
        return None
    return a["stdout"] == b["stdout"] and a["rc"] == b["rc"]


def _tmp_root() -> str:
    from src.temp_paths import runtime_temp_dir
    return runtime_temp_dir()


def gpp_warnings(code: str) -> List[Dict[str, Any]]:
    """Baseline: g++ -O2 -Wall -Wextra warnings, one pseudo-finding per warning."""
    with tempfile.TemporaryDirectory(dir=_tmp_root()) as wd:
        src = os.path.join(wd, "t.cpp")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(code)
        try:
            cp = _gpp([src, "-c", "-o", os.path.join(wd, "t.o"), "-O2", "-Wall", "-Wextra"])
        except subprocess.TimeoutExpired:
            return []
    out = []
    for line in cp.stderr.splitlines():
        m = re.search(r"(warning|error): (.*)", line)
        if m:
            out.append({"type": m.group(2), "line_text": line, "severity": m.group(1)})
    return out


# ── LLM + detection ──────────────────────────────────────────────────────────

def make_llm(config: str):
    from src.llm.llm_client import LLMClient, make_llm_client

    if config.startswith("gemini"):
        client = make_llm_client("gemini")
        real_generate = client.generate
        client.stub_calls = 0
        client.total_calls = 0

        def paced_generate(*a, **kw):
            time.sleep(7)  # stay under the free-tier per-minute limit
            out = real_generate(*a, **kw)
            client.total_calls += 1
            if "offline stub" in out.lower():  # API error / quota -> stub: not an LLM result
                client.stub_calls += 1
            return out

        client.generate = paced_generate
        return client

    class _NoLLM(LLMClient):
        def __init__(self):
            self.model, self._requests, self._available = "none", None, False

    return _NoLLM()


def detect(src: str, path: str, llm) -> List[Dict[str, Any]]:
    """Findings on `src`: analysis agent + security agent + standalone scanner."""
    from agent_framework import ContextManager
    from src.agents.analysis_agent import AnalysisAgent
    from src.agents.security_agent import SecurityAgent
    from src.security.security_scanner import SecurityScanner

    ctx = ContextManager()
    a = AnalysisAgent("det_a", ctx, llm).process({"source_code": src, "file_path": path})
    s = SecurityAgent("det_s", ctx, llm).process(
        {"original_code": src, "optimized_code": src, "file_path": path})
    return list(a.get("all_findings", [])) + list(s.get("all_vulnerabilities", [])) + SecurityScanner().scan(src)


# ── one case ─────────────────────────────────────────────────────────────────

def run_case(tc: str, config: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    logging.disable(logging.WARNING)
    path = case_path(tc)
    original = _read(path)
    expected = meta["expected"]
    row: Dict[str, Any] = {
        "tc": tc, "config": config, "expected": expected,
        "headline": meta["headline"], "supported": meta["supported"],
        "nondeterministic": meta.get("nondeterministic"),
    }

    if config == "gpp_wall":
        findings = gpp_warnings(original)
        row["detected"] = score_detection(findings, expected)
        row["n_findings"] = len(findings)
        row["ver_status"] = "n/a"
        return row

    from src.agents.optimization_agent import OptimizationAgent
    out_dir = os.path.join(EXP, "opt_out", config)
    OptimizationAgent.__init__.__defaults__ = (None, out_dir)

    llm = make_llm(config)
    t0 = time.perf_counter()
    findings = detect(original, path, llm)
    row["detected"] = score_detection(findings, expected)
    row["n_findings"] = len(findings)
    row["detect_s"] = round(time.perf_counter() - t0, 3)

    from src.pipeline.pipeline import CompilerOptimizationPipeline

    pipe = CompilerOptimizationPipeline(llm_client=llm)
    t1 = time.perf_counter()
    if config.endswith("_orch"):
        orch = pipe.run_orchestrated(path, max_cycles=3, low_conf_threshold=0.8)
        rep = orch["pipeline_result"]
        row.update(workflow_status=orch.get("workflow_status"),
                   iterations=orch.get("iteration_count"),
                   stop_reason=orch.get("stop_reason"))
        analysis, opt = rep["analysis_report"], rep["optimization_report"]
        ver, sec = rep["verification_report"], rep["security_report"]
        row["pipeline_status"] = rep["status"]
    else:
        res = pipe.run(path)
        analysis, opt, ver, sec = (res.analysis_report, res.optimization_report,
                                   res.verification_report, res.security_report)
        row["pipeline_status"] = res.status
    row["pipeline_s"] = round(time.perf_counter() - t1, 3)

    row["ver_status"] = (ver or {}).get("status", "UNKNOWN")
    row["sec_status"] = (sec or {}).get("status", "UNKNOWN")
    row["diff_passed"] = (ver or {}).get("diff_passed")
    row["transformations"] = [t.get("type") for t in (opt or {}).get("transformations", [])]
    row["stage_timings"] = {k: (r or {}).get("stage_timings") for k, r in
                            (("analysis", analysis), ("optimization", opt),
                             ("verification", ver), ("security", sec))}
    steps = " ".join((analysis or {}).get("reasoning_steps", []))
    row["llm_fallback"] = bool(config.startswith("gemini") and (
        re.search(r"stub|unavailable|invalid", steps, re.I)
        or (opt or {}).get("conclusion") == "Applied rule-based fixes."))

    if config.startswith("gemini"):
        row["llm_calls"] = llm.total_calls
        row["llm_stub_calls"] = llm.stub_calls
        if llm.stub_calls:  # fail fast: this row is NOT a valid LLM result
            row["error"] = f"llm_stub: {llm.stub_calls}/{llm.total_calls} calls returned the offline stub"
            return row

    rolled_back = row["ver_status"] in ("ROLLBACK", "FAIL") or row["sec_status"] == "ROLLBACK"
    final_code = original if rolled_back else (opt or {}).get("optimized_code", original)
    row["code_changed"] = final_code != original

    # Detector-judged correction: bug class detected before, absent after.
    if row["detected"] and all(row["detected"].values()):
        after = detect(final_code, path, make_llm("rule_basic"))
        still = score_detection(after, expected)
        row["corrected_detector"] = not any(still.values())
    else:
        row["corrected_detector"] = None

    sp = sol_path(tc, meta.get("sol_file"))
    if sp and meta.get("compiles_here") and meta.get("nondeterministic") is False:
        row["output_matches_sol"] = output_matches_sol(final_code, _read(sp))
    else:
        row["output_matches_sol"] = None

    # False positive: the TC's own bug class still reported on the fixed program.
    if config.startswith("rule") and sp:
        sol_findings = detect(_read(sp), sp, make_llm("rule_basic"))
        row["fp_on_sol"] = any(score_detection(sol_findings, expected).values())
    return row


# ── CLI ──────────────────────────────────────────────────────────────────────

def load_meta() -> Dict[str, Dict[str, Any]]:
    with open(os.path.join(EXP, "expected_categories.json"), encoding="utf-8") as fh:
        return json.load(fh)


def cmd_single(args) -> None:
    meta = load_meta()[args.tc]
    try:
        row = run_case(args.tc, args.config, meta)
    except Exception as exc:  # recorded, not fatal
        import traceback
        row = {"tc": args.tc, "config": args.config, "error": f"{type(exc).__name__}: {exc}",
               "traceback": traceback.format_exc()[-1500:]}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(row, fh, indent=2, default=str)


def cmd_run(args) -> None:
    meta = load_meta()
    cases = [c for c in args.cases.split(",")] if args.cases else (
        SUBSET if args.subset else list(meta))
    raw = os.path.join(EXP, "raw", args.config)
    os.makedirs(raw, exist_ok=True)
    for tc in cases:
        out = os.path.join(raw, f"{tc}.json")
        if os.path.isfile(out) and not args.force:
            continue
        t0 = time.time()
        try:
            subprocess.run([sys.executable, __file__, "single", "--tc", tc,
                            "--config", args.config, "--out", out],
                           timeout=args.timeout, capture_output=True, text=True)
        except subprocess.TimeoutExpired:
            with open(out, "w", encoding="utf-8") as fh:
                json.dump({"tc": tc, "config": args.config, "error": "timeout",
                           "timeout_s": args.timeout}, fh)
        print(f"{tc} {args.config} {time.time() - t0:.1f}s", flush=True)


def cmd_summarize(args) -> None:
    raw = os.path.join(EXP, "raw", args.config)
    rows = [json.load(open(p, encoding="utf-8")) for p in sorted(glob.glob(os.path.join(raw, "*.json")))]
    ok = [r for r in rows if "error" not in r]
    errors = [{"tc": r["tc"], "error": r["error"]} for r in rows if "error" in r]
    # A timed-out case is a pipeline failure, not a missing data point: keep it in
    # the denominator as an undetected, TIMEOUT-status row.
    meta = load_meta()
    for r in rows:
        if r.get("error") == "timeout":
            m = meta[r["tc"]]
            ok.append({"tc": r["tc"], "headline": m["headline"], "expected": m["expected"],
                       "supported": m["supported"], "detected": {c: False for c in m["expected"]},
                       "ver_status": "TIMEOUT", "corrected_detector": None})
    agg = aggregate(ok)
    agg["errors"] = errors
    agg["rows_total"] = len(rows)
    agg["output_matches_sol"] = sum(1 for r in ok if r.get("output_matches_sol") is True)
    agg["output_sol_checked"] = sum(1 for r in ok if r.get("output_matches_sol") is not None)
    agg["fp_on_sol"] = sum(1 for r in ok if r.get("fp_on_sol"))
    agg["fp_denominator"] = sum(1 for r in ok if "fp_on_sol" in r)
    agg["llm_fallback"] = sum(1 for r in ok if r.get("llm_fallback"))
    with open(os.path.join(EXP, f"aggregate_{args.config}.json"), "w", encoding="utf-8") as fh:
        json.dump(agg, fh, indent=2)
    cols = ["tc", "headline", "expected", "detected", "n_findings", "ver_status", "sec_status",
            "code_changed", "corrected_detector", "output_matches_sol", "fp_on_sol",
            "llm_fallback", "pipeline_s", "workflow_status", "iterations"]
    with open(os.path.join(EXP, f"summary_{args.config}.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([json.dumps(r.get(c)) if isinstance(r.get(c), (list, dict)) else r.get(c, r.get("error") if c == "ver_status" else "") for c in cols])
    print(json.dumps(agg, indent=2))


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("single"); s.add_argument("--tc", required=True)
    s.add_argument("--config", required=True); s.add_argument("--out", required=True)
    r = sub.add_parser("run"); r.add_argument("--config", required=True)
    r.add_argument("--cases"); r.add_argument("--subset", action="store_true")
    r.add_argument("--timeout", type=int, default=300); r.add_argument("--force", action="store_true")
    m = sub.add_parser("summarize"); m.add_argument("--config", required=True)
    args = p.parse_args()
    {"single": cmd_single, "run": cmd_run, "summarize": cmd_summarize}[args.cmd](args)


if __name__ == "__main__":
    main()
