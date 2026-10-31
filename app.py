"""
app.py — Flask REST + Server-Sent Events backend for DeepCompile
==============================================================================
Run with:  python app.py
Then open: http://localhost:5173  (after running `npm run dev` in frontend/)
"""

from __future__ import annotations

import json
import logging
import os
import queue
import sys
import tempfile
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

# ── Ensure project root is on sys.path ──────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from src.sustainability import estimate_run_footprint
from src.sustainability.hardware_monitor import get_monitor
from src.sustainability.benchmarks import get_benchmarks
from src.temp_paths import runtime_temp_dir

DIST_DIR = os.path.join(ROOT, "frontend", "dist")
app = Flask(__name__, static_folder=DIST_DIR, static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ────────────────────────────────────────────────────────────────────────────
# Streaming infrastructure
# ────────────────────────────────────────────────────────────────────────────

class StreamQueue:
    """Thread-safe queue that feeds SSE events to the HTTP response."""

    def __init__(self) -> None:
        self._q: "queue.Queue[Optional[dict]]" = queue.Queue()

    def push(self, event_type: str, data: Any) -> None:
        self._q.put({
            "type": event_type,
            "data": data,
            "ts":   datetime.utcnow().isoformat(timespec="milliseconds"),
        })

    def close(self) -> None:
        """Send sentinel to signal end-of-stream."""
        self._q.put(None)

    def pop(self, timeout: float = 180.0) -> Optional[dict]:
        return self._q.get(timeout=timeout)


class _QueueLogHandler(logging.Handler):
    """Captures Python log records and forwards them to the StreamQueue."""

    def __init__(self, sq: StreamQueue) -> None:
        super().__init__()
        self._sq = sq

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._sq.push("log", {
                "level":   record.levelname,
                "logger":  record.name,
                "message": self.format(record),
            })
        except Exception:
            pass


class _QueueMessageLogger:
    """
    Drop-in replacement for src.message_logger.MessageLogger.

    The pipeline calls  self._msg_logger._on_message(msg)  for every
    inter-agent message.  We forward those messages as SSE events.
    """

    def __init__(self, sq: StreamQueue) -> None:
        self._sq    = sq
        self._count = 0

    def _on_message(self, message) -> None:
        self._count += 1

        # Build a safe, size-limited payload preview
        preview: Dict[str, Any] = {}
        for k, v in (message.payload or {}).items():
            if k in ("source_code", "original_code", "optimized_code"):
                preview[k] = f"<{len(str(v).splitlines())} lines>"
            elif k == "unified_diff":
                preview[k] = f"<diff {len(str(v))} chars>"
            elif isinstance(v, (dict, list)) and len(str(v)) > 200:
                preview[k] = f"<{type(v).__name__} …>"
            else:
                preview[k] = (
                    v if isinstance(v, (str, int, float, bool, type(None)))
                    else str(v)
                )

        self._sq.push("agent_message", {
            "seq":             self._count,
            "sender":          message.sender_id,
            "receiver":        message.receiver_id,
            "type":            message.message_type.value,
            "priority":        message.priority.value,
            "msg_id":          message.message_id[:8],
            "corr_id":         (message.correlation_id or "")[:8],
            "payload_keys":    list((message.payload or {}).keys()),
            "payload_preview": preview,
        })

    # pipeline may call this — keep it a no-op
    def print_summary(self) -> None:
        pass


# ────────────────────────────────────────────────────────────────────────────
# LLM factory
# ────────────────────────────────────────────────────────────────────────────

def _make_llm(use_llm: bool, backend: str = "ollama"):
    from src.llm.llm_client import make_llm_client
    client = make_llm_client(backend)
    if not use_llm:
        client._available = False
    return client


# ────────────────────────────────────────────────────────────────────────────
# Mode runners (each runs in a background thread)
# ────────────────────────────────────────────────────────────────────────────

def _run_full_pipeline(sq: StreamQueue, file_path: str, use_llm: bool, backend: str = "ollama", hardware_metrics: Dict[str, Any] = None) -> None:
    from src.agents.analysis_agent import AnalysisAgent
    from src.agents.optimization_agent import OptimizationAgent
    from src.agents.verification_agent import VerificationAgent
    from src.agents.security_agent import SecurityAgent
    from agent_framework import ContextManager

    sq.push("status", {"phase": "pipeline_init", "message": "Initialising 4-agent pipeline…"})
    llm = _make_llm(use_llm, backend)
    ctx = ContextManager()

    # Read source from temp file
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            source_code = fh.read()
    except OSError as exc:
        sq.push("error", {"message": f"Cannot read temp file: {exc}"})
        return

    # ── Step 1: Analysis ──────────────────────────────────────────────────────
    sq.push("status", {"phase": "analysis_running", "message": "Step 1/4 — Analysis Agent running…"})
    analysis_result = AnalysisAgent("analysis_1", ctx, llm).process(
        {"source_code": source_code, "file_path": file_path}
    )
    sq.push("analysis_result", analysis_result)
    n_findings = len(analysis_result.get("all_findings", []))
    sq.push("status", {
        "phase":   "analysis_done",
        "message": f"Analysis complete — {n_findings} finding(s) found",
    })

    # ── Step 2: Optimization ──────────────────────────────────────────────────
    sq.push("status", {"phase": "optimization_running", "message": "Step 2/4 — Optimization Agent running…"})
    opt_result = OptimizationAgent("optimization_1", ctx, llm).process({
        "source_code":     source_code,
        "file_path":       file_path,
        "analysis_report": analysis_result,
    })
    sq.push("optimization_result", opt_result)
    n_transforms = len(opt_result.get("transformations", []))
    sq.push("status", {
        "phase":   "optimization_done",
        "message": f"Optimization complete — {n_transforms} transformation(s) applied",
    })

    # ── Step 3: Verification ──────────────────────────────────────────────────
    sq.push("status", {"phase": "verification_running", "message": "Step 3/4 — Verification Agent running…"})
    ver_result = VerificationAgent("verification_1", ctx, llm).process({
        "original_code":  source_code,
        "optimized_code": opt_result.get("optimized_code", source_code),
        "file_path":      file_path,
    })
    sq.push("verification_result", ver_result)
    ver_status = ver_result.get("status", "UNKNOWN")
    sq.push("status", {
        "phase":   "verification_done",
        "message": f"Verification complete — {ver_status}",
    })

    # ── Step 4: Security ──────────────────────────────────────────────────────
    sq.push("status", {"phase": "security_running", "message": "Step 4/4 — Security Agent running…"})
    # Use original code if verification rolled back the optimization
    final_code = (
        opt_result.get("optimized_code", source_code)
        if ver_status not in ("ROLLBACK", "FAIL")
        else source_code
    )
    sec_result = SecurityAgent("security_1", ctx, llm).process({
        "original_code":  source_code,
        "optimized_code": final_code,
        "file_path":      file_path,
    })
    # Push scanner-level findings for editor glyph decorations
    from src.security.security_scanner import SecurityScanner
    sq.push("security_findings", {"findings": SecurityScanner().scan(final_code)})
    sq.push("security_result", sec_result)
    n_vulns = len(sec_result.get("all_vulnerabilities", []))
    n_new   = len(sec_result.get("new_vulnerabilities", []))
    sq.push("status", {
        "phase":   "security_done",
        "message": f"Security audit complete — {n_vulns} finding(s), {n_new} new",
    })

    # ── Pipeline summary ──────────────────────────────────────────────────────
    if ver_status in ("ROLLBACK", "FAIL") or sec_result.get("status") == "ROLLBACK":
        overall = "rollback"
    else:
        overall = "success"

    sq.push("pipeline_result", {
        "status":              overall,
        "analysis_findings":   n_findings,
        "transformations":     n_transforms,
        "verification_status": ver_status,
        "security_vulns":      n_vulns,
        "new_vulns":           n_new,
        "security_risk":       sec_result.get("overall_risk", "unknown"),
        "sustainability":      estimate_run_footprint(
            "pipeline",
            source_code,
            {
                "transformations": opt_result.get("transformations", []),
                "all_findings": analysis_result.get("all_findings", []),
                "stage_timings": {
                    "analysis": analysis_result.get("stage_timings", {}),
                    "optimization": opt_result.get("stage_timings", {}),
                    "verification": ver_result.get("stage_timings", {}),
                    "security": sec_result.get("stage_timings", {}),
                },
            },
            use_llm=use_llm,
        ),
    })


def _run_analyze_only(sq: StreamQueue, source_code: str, file_path: str, use_llm: bool, backend: str = "ollama", hardware_metrics: Dict[str, Any] = None) -> None:
    from src.agents.analysis_agent import AnalysisAgent
    from agent_framework import ContextManager

    sq.push("status", {"phase": "analysis_init", "message": "Initialising Analysis Agent…"})
    llm   = _make_llm(use_llm, backend)
    ctx   = ContextManager()
    agent = AnalysisAgent("analysis_1", ctx, llm)

    sq.push("status", {"phase": "analysis_running", "message": "Running code analysis…"})
    result = agent.process({"source_code": source_code, "file_path": file_path})
    sq.push("analysis_result", result)
    sq.push("status", {
        "phase":   "analysis_done",
        "message": f"Analysis complete — {len(result.get('all_findings', []))} finding(s) found",
    })


def _run_optimize_only(sq: StreamQueue, source_code: str, file_path: str, use_llm: bool, backend: str = "ollama", hardware_metrics: Dict[str, Any] = None) -> None:
    from src.agents.analysis_agent import AnalysisAgent
    from src.agents.optimization_agent import OptimizationAgent
    from agent_framework import ContextManager

    llm = _make_llm(use_llm, backend)
    ctx = ContextManager()

    sq.push("status", {"phase": "analysis_running", "message": "Step 1/2 — Running analysis…"})
    analysis_agent  = AnalysisAgent("analysis_1", ctx, llm)
    analysis_result = analysis_agent.process({"source_code": source_code, "file_path": file_path})
    sq.push("analysis_result", analysis_result)
    sq.push("status", {
        "phase":   "optimization_init",
        "message": f"Step 2/2 — Initialising Optimization Agent…",
    })

    opt_agent  = OptimizationAgent("optimization_1", ctx, llm)
    sq.push("status", {"phase": "optimization_running", "message": "Applying optimizations…"})
    opt_result = opt_agent.process({
        "source_code":     source_code,
        "file_path":       file_path,
        "analysis_report": analysis_result,
    })
    opt_result = dict(opt_result)
    opt_result["sustainability"] = estimate_run_footprint(
        "optimize", source_code, opt_result, use_llm=use_llm, hardware_metrics=hardware_metrics
    )
    sq.push("optimization_result", opt_result)
    sq.push("status", {
        "phase":   "optimization_done",
        "message": f"Optimization complete — {len(opt_result.get('transformations', []))} transformation(s)",
    })


def _run_verify_only(sq: StreamQueue, source_code: str, file_path: str, use_llm: bool, backend: str = "ollama", hardware_metrics: Dict[str, Any] = None) -> None:
    from src.agents.analysis_agent import AnalysisAgent
    from src.agents.optimization_agent import OptimizationAgent
    from src.agents.verification_agent import VerificationAgent
    from agent_framework import ContextManager

    llm = _make_llm(use_llm, backend)
    ctx = ContextManager()

    sq.push("status", {"phase": "analysis_running", "message": "Step 1/3 — Running analysis…"})
    analysis_result = AnalysisAgent("analysis_1", ctx, llm).process(
        {"source_code": source_code, "file_path": file_path}
    )
    sq.push("analysis_result", analysis_result)

    sq.push("status", {"phase": "optimization_running", "message": "Step 2/3 — Running optimization…"})
    opt_result = OptimizationAgent("optimization_1", ctx, llm).process({
        "source_code":     source_code,
        "file_path":       file_path,
        "analysis_report": analysis_result,
    })
    sq.push("optimization_result", opt_result)

    sq.push("status", {"phase": "verification_init", "message": "Step 3/3 — Initialising Verification Agent…"})
    ver_agent = VerificationAgent("verification_1", ctx, llm)

    sq.push("status", {"phase": "verification_running", "message": "Running 4-layer verification…"})
    ver_result = ver_agent.process({
        "original_code":  source_code,
        "optimized_code": opt_result.get("optimized_code", source_code),
        "file_path":      file_path,
    })
    ver_result = dict(ver_result)
    ver_result["sustainability"] = estimate_run_footprint(
        "verify", source_code, ver_result, use_llm=use_llm, hardware_metrics=hardware_metrics
    )
    sq.push("verification_result", ver_result)
    sq.push("status", {
        "phase":   "verification_done",
        "message": f"Verification complete — status: {ver_result.get('status', 'UNKNOWN')}",
    })


def _run_security_only(sq: StreamQueue, source_code: str, file_path: str, use_llm: bool, backend: str = "ollama", hardware_metrics: Dict[str, Any] = None) -> None:
    from src.security.security_scanner import SecurityScanner
    from src.agents.security_agent import SecurityAgent
    from agent_framework import ContextManager

    sq.push("status", {"phase": "security_init", "message": "Initialising Security Scanner…"})
    findings = SecurityScanner().scan(source_code)
    # Push findings for editor glyph decorations
    sq.push("security_findings", {"findings": findings})
    sq.push("status", {
        "phase":   "security_scan_done",
        "message": f"Rule-based scan complete — {len(findings)} finding(s).",
    })

    sq.push("status", {"phase": "security_agent_running", "message": "Running Security Agent (deep audit)…"})
    llm = _make_llm(use_llm, backend)
    ctx = ContextManager()
    try:
        sec_result = SecurityAgent("security_1", ctx, llm).process({
            "original_code":  source_code,
            "optimized_code": source_code,
            "file_path":      file_path,
        })
    except Exception as exc:
        import traceback
        sq.push("error", {"message": f"Security Agent error: {exc}", "traceback": traceback.format_exc()})
        sec_result = {
            "all_vulnerabilities": findings,
            "new_vulnerabilities": [],
            "overall_risk": "unknown" if not findings else ("high" if any(f.get("severity") == "high" for f in findings) else "medium"),
            "status": "PASS" if not findings else "WARN",
            "summary": f"Deep audit failed ({exc}); showing rule-based findings only.",
        }
    # For a standalone scan original == optimized, so new_vulns is always empty
    # and status is always PASS — override to WARN when findings actually exist.
    if sec_result.get("status") == "PASS" and sec_result.get("all_vulnerabilities"):
        sec_result = dict(sec_result)
        sec_result["status"] = "WARN"

    sq.push("security_result", sec_result)
    sq.push("status", {
        "phase":   "security_done",
        "message": f"Security audit complete — {len(sec_result.get('all_vulnerabilities', []))} finding(s).",
    })


# ────────────────────────────────────────────────────────────────────────────
# Top-level worker (runs in background thread)
# ────────────────────────────────────────────────────────────────────────────

def _worker(sq: StreamQueue, source_code: str, mode: str,
            use_llm: bool, language: str, backend: str = "ollama", hardware_metrics: Dict[str, Any] = None) -> None:
    """Runs the requested pipeline mode; pushes all events into sq."""

    # Attach a log handler so Python loggers stream to the UI
    handler = _QueueLogHandler(sq)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(name)s › %(message)s"))
    _watched_loggers = [
        logging.getLogger("src.pipeline.pipeline"),
        logging.getLogger("src.agents.analysis_agent"),
        logging.getLogger("src.agents.optimization_agent"),
        logging.getLogger("src.agents.verification_agent"),
        logging.getLogger("src.agents.security_agent"),
        logging.getLogger("src.security.security_scanner"),
        logging.getLogger("src.llm.llm_client"),
        logging.getLogger("src.verification.diff_tester"),
        logging.getLogger("src.verification.perf_benchmarker"),
        logging.getLogger("src.verification.z3_verifier"),
    ]
    for _lg in _watched_loggers:
        _lg.addHandler(handler)

    tmp_path: Optional[str] = None
    try:
        monitor = get_monitor()
        monitor.start()

        ext_map = {
            "cpp": ".cpp", "c": ".c",
            "python": ".py", "java": ".java", "go": ".go",
        }
        ext = ext_map.get(language, ".cpp")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=ext, delete=False, encoding="utf-8", prefix="ui_", dir=runtime_temp_dir()
        ) as fh:
            fh.write(source_code)
            tmp_path = fh.name

        sq.push("status", {"phase": "init", "message": "Code written to temp file — starting…"})

        # Pre-warm: send a tiny ping to Ollama so the model is loaded
        # before the real pipeline request hits (avoids cold-start timeout).
        # Skip for Gemini — it's a cloud API with no cold-start penalty.
        if use_llm and backend == "ollama":
            try:
                from src.llm.llm_client import LLMClient
                _warm = LLMClient()
                if _warm.is_available():
                    sq.push("status", {"phase": "warmup", "message": "Warming up LLM model (first run may take 1–2 min)…"})
                    _warm.generate("hi", max_tokens=1)
                    sq.push("status", {"phase": "warmup_done", "message": "LLM model ready."})
            except Exception:
                pass

        if mode == "pipeline":
            _run_full_pipeline_orchestrated(sq, tmp_path, use_llm, backend, hardware_metrics=hardware_metrics)
        elif mode == "analyze":
            _run_analyze_only(sq, source_code, tmp_path, use_llm, backend, hardware_metrics=hardware_metrics)
        elif mode == "optimize":
            _run_optimize_only(sq, source_code, tmp_path, use_llm, backend, hardware_metrics=hardware_metrics)
        elif mode == "verify":
            _run_verify_only(sq, source_code, tmp_path, use_llm, backend, hardware_metrics=hardware_metrics)
        elif mode == "security":
            _run_security_only(sq, source_code, tmp_path, use_llm, backend, hardware_metrics=hardware_metrics)
        else:
            sq.push("error", {"message": f"Unknown mode: {mode}"})

        sq.push("complete", {"status": "success"})

    except Exception as exc:
        import traceback
        sq.push("error", {
            "message":   str(exc),
            "traceback": traceback.format_exc(),
        })
        sq.push("complete", {"status": "error"})

    finally:
        hardware_metrics = monitor.stop() if 'monitor' in locals() else {}

        if mode == "pipeline":
             # We need a way to pass this to the orchestrated runner if we want it there
             # For now, let's update the individual mode runners logic
             pass
        
        for _lg in _watched_loggers:
            _lg.removeHandler(handler)
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        sq.close()


# ────────────────────────────────────────────────────────────────────────────
# Flask routes
# ────────────────────────────────────────────────────────────────────────────

def _run_full_pipeline_orchestrated(
    sq: StreamQueue,
    file_path: str,
    use_llm: bool,
    backend: str = "ollama",
    hardware_metrics: Dict[str, Any] = None,
) -> None:
    from src.pipeline.pipeline import CompilerOptimizationPipeline, PipelineResult
    from src.reporting.report_contract import build_explainability_report
    from src.security.security_scanner import SecurityScanner

    sq.push("status", {"phase": "pipeline_init", "message": "Initialising orchestrated pipelineâ€¦"})
    llm = _make_llm(use_llm, backend)
    pipeline = CompilerOptimizationPipeline(llm_client=llm, message_logger=_QueueMessageLogger(sq))

    if not use_llm:
        for agent in (
            pipeline.analysis_agent,
            pipeline.optimization_agent,
            pipeline.verification_agent,
            pipeline.security_agent,
        ):
            if agent is not None:
                agent.llm._available = False

    orchestration = pipeline.run_orchestrated(file_path, max_cycles=3, low_conf_threshold=0.8)
    payload = orchestration.get("pipeline_result", {})
    result = PipelineResult(
        file_path=payload.get("file_path", file_path),
        status=payload.get("status", "failed"),
        analysis_report=payload.get("analysis_report", {}),
        optimization_report=payload.get("optimization_report", {}),
        verification_report=payload.get("verification_report", {}),
        security_report=payload.get("security_report", {}),
        error=payload.get("error"),
    )

    analysis_result = result.analysis_report or {}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            source_code = fh.read()
    except OSError:
        source_code = ""

    opt_result = dict(result.optimization_report or {})
    ver_result = dict(result.verification_report or {})
    sec_result = result.security_report or {}

    opt_result["sustainability"] = estimate_run_footprint(
        "optimize", source_code, opt_result, use_llm=use_llm, hardware_metrics=hardware_metrics
    )
    ver_result["sustainability"] = estimate_run_footprint(
        "verify", source_code, ver_result, use_llm=use_llm, hardware_metrics=hardware_metrics
    )

    sq.push("analysis_result", analysis_result)
    sq.push("optimization_result", opt_result)
    sq.push("verification_result", ver_result)
    sq.push("security_result", sec_result)

    final_code = opt_result.get("optimized_code", "")
    if ver_result.get("status") in ("ROLLBACK", "FAIL") or sec_result.get("status") == "ROLLBACK":
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                final_code = fh.read()
        except OSError:
            pass

    sq.push("security_findings", {"findings": SecurityScanner().scan(final_code)})
    explainability = build_explainability_report(file_path, result, orchestration)

    sq.push("status", {
        "phase": "orchestration_done",
        "message": (
            f"Workflow {orchestration.get('workflow_status', 'UNKNOWN')} "
            f"after {orchestration.get('iteration_count', 0)} iteration(s)"
        ),
    })

    sq.push("pipeline_result", {
        "status":              result.status,
        "analysis_findings":   len(analysis_result.get("all_findings", [])),
        "transformations":     len(opt_result.get("transformations", [])),
        "verification_status": ver_result.get("status", "UNKNOWN"),
        "security_vulns":      len(sec_result.get("all_vulnerabilities", [])),
        "new_vulns":           len(sec_result.get("new_vulnerabilities", [])),
        "security_risk":       sec_result.get("overall_risk", "unknown"),
        "workflow_status":     orchestration.get("workflow_status", "UNKNOWN"),
        "iteration_count":     orchestration.get("iteration_count", 0),
        "stop_reason":         orchestration.get("stop_reason", ""),
        "review_required":     orchestration.get("review_required", False),
        "escalation_reasons":  orchestration.get("escalation_reasons", []),
        "explainability":      explainability.to_dict(),
        "sustainability":      estimate_run_footprint(
            "pipeline",
            source_code,
            {
                "transformations": opt_result.get("transformations", []),
                "all_findings": analysis_result.get("all_findings", []),
                "stage_timings": {
                    "analysis": analysis_result.get("stage_timings", {}),
                    "optimization": opt_result.get("stage_timings", {}),
                    "verification": ver_result.get("stage_timings", {}),
                    "security": sec_result.get("stage_timings", {}),
                },
            },
            use_llm=use_llm,
            hardware_metrics=hardware_metrics,
        ),
    })


@app.route("/api/security-scan", methods=["POST"])
def security_scan():
    """On-demand rule-based security scan — synchronous, < 100 ms."""
    body = request.get_json(silent=True) or {}
    code = body.get("code", "").strip()
    if not code:
        return jsonify({"error": "No code provided"}), 400

    import time
    from src.security.security_scanner import SecurityScanner
    t0       = time.monotonic()
    findings = SecurityScanner().scan(code)
    elapsed  = int((time.monotonic() - t0) * 1000)
    return jsonify({"findings": findings, "total": len(findings), "scan_time_ms": elapsed})


@app.route("/api/security-fix", methods=["POST"])
def security_fix():
    """Apply all rule-based fixes and return fixed code + unified diff."""
    body     = request.get_json(silent=True) or {}
    code     = body.get("code", "").strip()
    findings = body.get("findings", [])
    if not code:
        return jsonify({"error": "No code provided"}), 400

    from src.security.security_fixer import SecurityFixer
    fixed_code, fixes_applied, diff = SecurityFixer().apply_all_fixes(code, findings)
    return jsonify({"fixed_code": fixed_code, "unified_diff": diff, "fixes_applied": fixes_applied})


@app.route("/api/health", methods=["GET"])
def health():
    try:
        from src.llm.llm_client import LLMClient, GeminiLLMClient
        ollama_info = LLMClient().health_check()
    except Exception as exc:
        ollama_info = {"available": False, "error": str(exc)}
    try:
        gemini_info = GeminiLLMClient().health_check()
    except Exception as exc:
        gemini_info = {"available": False, "error": str(exc)}
    return jsonify({"status": "ok", "ollama": ollama_info, "gemini": gemini_info})


@app.route("/api/stream", methods=["POST"])
def stream_endpoint():
    body     = request.get_json(silent=True) or {}
    code     = body.get("code", "").strip()
    mode     = body.get("mode", "pipeline")
    use_llm  = bool(body.get("use_llm", True))
    language = body.get("language", "cpp")
    backend  = body.get("backend", "ollama")

    if not code:
        return jsonify({"error": "No code provided"}), 400

    sq = StreamQueue()
    threading.Thread(
        target=_worker,
        args=(sq, code, mode, use_llm, language, backend),
        daemon=True,
    ).start()

    def generate():
        while True:
            try:
                item = sq.pop(timeout=180)
                if item is None:
                    yield "data: " + json.dumps({"type": "done"}) + "\n\n"
                    break
                yield "data: " + json.dumps(item, default=str) + "\n\n"
            except queue.Empty:
                yield "data: " + json.dumps({"type": "timeout"}) + "\n\n"
                break

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )


# ────────────────────────────────────────────────────────────────────────────
# Serve React frontend (catch-all for client-side routing)
# ────────────────────────────────────────────────────────────────────────────

@app.route("/api/sustainability-benchmarks", methods=["GET"])
def sustainability_benchmarks():
    return jsonify(get_benchmarks())


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path: str):
    if os.path.exists(os.path.join(DIST_DIR, path)):
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, "index.html")


# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("\n  CompilerAI Backend — http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
