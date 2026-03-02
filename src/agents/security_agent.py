"""
Security Agent — Week 8

Detects security vulnerabilities in C/C++ code using four layers:
  Layer 1: Rule-based   — exact unsafe function patterns   (confidence 0.90)
  Layer 2: Heuristic    — multi-signal context-aware scoring (confidence 0.65-0.85)
  Layer 3: LLM          — semantic analysis via SecurityPromptTemplate (confidence 0.70)
  Layer 4: cppcheck     — static analysis tool XML output  (confidence 0.85, optional)

Compares original vs optimized code internally.
Only NEW HIGH-severity findings from Layer 1 or Layer 2 (score >= 0.8) trigger rollback.
"""

import logging
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

_root = os.path.join(os.path.dirname(__file__), "..", "..")
if _root not in sys.path:
    sys.path.insert(0, _root)

from agent_framework import BaseAgent, ContextManager
from src.llm.llm_client import LLMClient
from src.llm.prompt_templates import SecurityPromptTemplate
from src.reasoning.cot_validator import CoTValidator

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    """
    Security Agent: detects and compares vulnerabilities in original vs optimized code.

    Input (passed to process()):
        {
            "original_code":  "<original C++ source>",
            "optimized_code": "<optimized C++ source>",
            "file_path":      "<optional path for labelling>"
        }

    Output:
        {
            "file_path":           str,
            "all_vulnerabilities": [...],   # all findings in optimized code
            "new_vulnerabilities": [...],   # only newly introduced ones
            "heuristic_scores":    {},      # per-signal scores for transparency
            "overall_risk":        str,     # critical/high/medium/low/none
            "status":              str,     # "PASS" | "ROLLBACK"
            "rollback_triggers":   [...],   # findings that caused rollback
            "llm_reasoning":       [...],
            "llm_conclusion":      str,
            "sources":             [...],
            "summary":             str,
        }
    """

    # ── Layer 1: Unsafe function patterns ─────────────────────────────────────
    # (regex, type, severity, cwe_id, description)
    _UNSAFE_FUNCTIONS = [
        (
            r"\bgets\s*\(",
            "unsafe_gets", "high", "CWE-242",
            "gets() is unconditionally unsafe — no bound checking on input length.",
            "Replace gets() with fgets(buf, sizeof(buf), stdin).",
        ),
        (
            r'\bscanf\s*\(\s*"[^"]*%s',
            "unsafe_scanf_s", "high", "CWE-134",
            "scanf %s reads an unbounded string — add a field width limit e.g. %127s.",
            "Add field width to format: scanf(\"%127s\", buf).",
        ),
        (
            r"\bstrcpy\s*\(",
            "unsafe_strcpy", "medium", "CWE-676",
            "strcpy() copies without bound checking — destination may overflow.",
            "Replace with strncpy(dst, src, sizeof(dst) - 1) or strlcpy().",
        ),
        (
            r"\bstrcat\s*\(",
            "unsafe_strcat", "medium", "CWE-676",
            "strcat() appends without bound checking — destination may overflow.",
            "Replace with strncat(dst, src, sizeof(dst) - strlen(dst) - 1).",
        ),
        (
            r"\bsprintf\s*\(",
            "unsafe_sprintf", "medium", "CWE-676",
            "sprintf() writes unbounded output — use snprintf() with explicit size.",
            "Replace with snprintf(buf, sizeof(buf), fmt, ...).",
        ),
    ]

    # ── Layer 1: Format string pattern ────────────────────────────────────────
    _FORMAT_STRING_RE = re.compile(
        r"\b(printf|fprintf|sprintf|snprintf|vprintf|vsprintf)\s*\(\s*(\w+)\s*[,)]",
        re.MULTILINE,
    )

    def __init__(self, agent_id: str, context_manager: ContextManager,
                 llm_client: LLMClient = None):
        # Set instance attributes BEFORE super().__init__() because BaseAgent
        # calls get_capabilities() during initialisation.
        self._cppcheck_available = self._check_cppcheck()
        self.llm = llm_client or LLMClient()
        self.cot_val = CoTValidator()
        super().__init__(agent_id, "security", context_manager)
        if self._cppcheck_available:
            logger.info("SecurityAgent: cppcheck detected")
        else:
            logger.info("SecurityAgent: cppcheck not found — skipping Layer 4")

    # ── BaseAgent interface ────────────────────────────────────────────────────

    def get_capabilities(self) -> List[str]:
        caps = [
            "buffer_overflow_detection",
            "format_string_detection",
            "use_after_free_detection",
            "integer_overflow_detection",
            "null_dereference_detection",
            "taint_flow_heuristics",
            "security_rollback",
            "llm_security_analysis",
        ]
        if self._cppcheck_available:
            caps.append("cppcheck_static_analysis")
        return caps

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point called by the pipeline."""
        original_code  = input_data.get("original_code", "")
        optimized_code = input_data.get("optimized_code", original_code)
        file_path      = input_data.get("file_path", "<unknown>")

        if not optimized_code.strip():
            logger.error("SecurityAgent: no code provided")
            return {"error": "No code provided", "status": "PASS",
                    "new_vulnerabilities": [], "all_vulnerabilities": []}

        logger.info(
            f"SecurityAgent: auditing '{os.path.basename(file_path)}' "
            f"({len(optimized_code)} chars)"
        )

        sources: List[str] = []

        # ── Layer 1: Rule-based ───────────────────────────────────────────────
        logger.info("SecurityAgent: Layer 1 — rule-based scan …")
        orig_rule = self._rule_scan(original_code)
        opt_rule  = self._rule_scan(optimized_code)
        sources.append("rules")
        logger.info(
            f"SecurityAgent: rules → original={len(orig_rule)}, "
            f"optimized={len(opt_rule)}"
        )

        # ── Layer 2: Heuristic ────────────────────────────────────────────────
        logger.info("SecurityAgent: Layer 2 — heuristic scan …")
        orig_heuristic, _           = self._heuristic_scan(original_code)
        opt_heuristic,  opt_scores  = self._heuristic_scan(optimized_code)
        sources.append("heuristics")
        logger.info(
            f"SecurityAgent: heuristics → original={len(orig_heuristic)}, "
            f"optimized={len(opt_heuristic)}"
        )

        # Merge all findings per code version
        orig_all = orig_rule + orig_heuristic
        opt_all  = opt_rule  + opt_heuristic

        # ── Layer 3: LLM ──────────────────────────────────────────────────────
        logger.info("SecurityAgent: Layer 3 — LLM semantic scan …")
        baseline_types = [f["type"] for f in orig_all]
        llm_findings, llm_reasoning, llm_conclusion, llm_conf = \
            self._llm_scan(optimized_code, original_code, baseline_types)
        if llm_findings:
            opt_all.extend(llm_findings)
            sources.append("llm")
        logger.info(f"SecurityAgent: LLM → {len(llm_findings)} finding(s)")

        # ── Layer 4: cppcheck ─────────────────────────────────────────────────
        cppcheck_findings: List[Dict] = []
        if self._cppcheck_available:
            logger.info("SecurityAgent: Layer 4 — cppcheck …")
            cppcheck_findings = self._cppcheck_scan(optimized_code, file_path)
            if cppcheck_findings:
                opt_all.extend(cppcheck_findings)
                sources.append("cppcheck")
            logger.info(f"SecurityAgent: cppcheck → {len(cppcheck_findings)} finding(s)")

        # ── New vulnerability detection ───────────────────────────────────────
        new_vulns = self._find_new_vulnerabilities(orig_all, opt_all)
        logger.info(f"SecurityAgent: {len(new_vulns)} NEW finding(s)")

        # ── Overall risk ──────────────────────────────────────────────────────
        overall_risk = self._compute_risk(opt_all)

        # ── Rollback decision ─────────────────────────────────────────────────
        # Only Layer 1 (rules) or high-scoring Layer 2 (heuristic >= 0.8)
        # findings with HIGH severity trigger rollback. LLM alone cannot rollback.
        rollback_triggers = [
            v for v in new_vulns
            if v.get("severity") == "high"
            and v.get("source") in ("rule", "heuristic")
            and v.get("confidence", 0) >= 0.8
        ]
        if rollback_triggers:
            logger.warning(
                f"SecurityAgent: ROLLBACK triggered — "
                f"{len(rollback_triggers)} new HIGH-severity vulnerability(ies) "
                "introduced by optimization."
            )
            self.context.rollback()
            status = "ROLLBACK"
        else:
            status = "PASS"

        result = {
            "file_path":           file_path,
            "all_vulnerabilities": opt_all,
            "new_vulnerabilities": new_vulns,
            "heuristic_scores":    opt_scores,
            "overall_risk":        overall_risk,
            "status":              status,
            "rollback_triggers":   rollback_triggers,
            "llm_reasoning":       llm_reasoning,
            "llm_conclusion":      llm_conclusion,
            "sources":             sources,
            "summary":             self._build_summary(
                file_path, opt_all, new_vulns, overall_risk, status
            ),
        }

        self.context.set("security_findings", result)
        logger.info(
            f"SecurityAgent: complete — status={status}, risk={overall_risk}, "
            f"total={len(opt_all)}, new={len(new_vulns)}"
        )
        return result

    # ── Layer 1: Rule-based scan ───────────────────────────────────────────────

    def _rule_scan(self, code: str) -> List[Dict]:
        findings: List[Dict] = []
        if not code.strip():
            return findings

        lines = code.splitlines()

        # Unsafe function patterns
        for pattern, vtype, severity, cwe, desc, fix in self._UNSAFE_FUNCTIONS:
            for ln_no, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    findings.append({
                        "type":           vtype,
                        "severity":       severity,
                        "line":           ln_no,
                        "description":    desc,
                        "cwe_id":         cwe,
                        "recommendation": fix,
                        "confidence":     0.9,
                        "source":         "rule",
                    })

        # Format string: printf/fprintf with a variable as first arg (not a literal)
        for m in self._FORMAT_STRING_RE.finditer(code):
            fn_name, arg = m.group(1), m.group(2)
            if not arg.startswith('"'):
                ln_no = code[: m.start()].count("\n") + 1
                findings.append({
                    "type":           "format_string_bug",
                    "severity":       "high",
                    "line":           ln_no,
                    "description":    (
                        f"{fn_name}() called with variable '{arg}' as format string "
                        "— potential format string attack (CWE-134)."
                    ),
                    "cwe_id":         "CWE-134",
                    "recommendation": (
                        f"Always use a literal format string: "
                        f'{fn_name}("%s", {arg}).'
                    ),
                    "confidence":     0.9,
                    "source":         "rule",
                })

        # Use-after-free
        findings.extend(self._detect_use_after_free(code, lines))

        return findings

    def _detect_use_after_free(self, code: str, lines: List[str]) -> List[Dict]:
        """
        Detect use-after-free for both C (free()) and C++ (delete / delete[]).
        Pattern: deallocation followed by dereference of the same variable.
        """
        findings: List[Dict] = []

        # Match both C free() and C++ delete / delete[]
        dealloc_re = re.compile(
            r"\bfree\s*\(\s*(\w+)\s*\)"    # free(ptr)
            r"|\bdelete\s*\[\s*\]\s*(\w+)" # delete[] ptr
            r"|\bdelete\s+(\w+)",           # delete ptr
            re.MULTILINE,
        )

        freed_vars: Dict[str, int] = {}
        for m in dealloc_re.finditer(code):
            var = m.group(1) or m.group(2) or m.group(3)
            freed_vars[var] = code[: m.start()].count("\n") + 1

        for var, free_line in freed_vars.items():
            deref_re = re.compile(
                rf"\*\s*{re.escape(var)}\b"
                rf"|{re.escape(var)}\s*->\s*\w+"
                rf"|{re.escape(var)}\s*\["
            )
            # Direct reassignment: "ptr = ..." but NOT "*ptr = ..." or "ptr[i] = ..."
            direct_assign_re = re.compile(
                rf"(?<![*\[])\b{re.escape(var)}\s*=\s*(?!=)"
            )
            for ln_no, line in enumerate(lines, 1):
                if ln_no <= free_line:
                    continue
                # Another deallocation of same var — stop looking
                if re.search(
                    rf"\bfree\s*\(\s*{re.escape(var)}\s*\)"
                    rf"|\bdelete(?:\s*\[\s*\])?\s+{re.escape(var)}",
                    line,
                ):
                    break
                # Direct reassignment of the pointer itself — it's no longer freed
                if direct_assign_re.search(line) and "->" not in line and \
                        not re.search(rf"\*\s*{re.escape(var)}", line):
                    break
                if deref_re.search(line):
                    findings.append({
                        "type":           "use_after_free",
                        "severity":       "high",
                        "line":           ln_no,
                        "description":    (
                            f"Variable '{var}' dereferenced at line {ln_no} "
                            f"after being deallocated at line {free_line}."
                        ),
                        "cwe_id":         "CWE-416",
                        "recommendation": (
                            f"Set '{var} = NULL/nullptr' immediately after "
                            "deallocation, and NULL-check before use."
                        ),
                        "confidence":     0.9,
                        "source":         "rule",
                    })
                    break

        return findings

    # ── Layer 2: Heuristic scan ────────────────────────────────────────────────

    def _heuristic_scan(self, code: str) -> Tuple[List[Dict], Dict[str, float]]:
        """
        Run all heuristic checks. Returns (findings, scores_dict).
        Each heuristic returns a score in [0, 1]; threshold to emit a finding
        is documented per check. Multi-signal: severity elevates only when
        score >= 0.8.
        """
        findings: List[Dict] = []
        scores: Dict[str, float] = {}

        if not code.strip():
            return findings, scores

        lines = code.splitlines()

        # H1: Taint flow — user input → buffer write without size check
        h1 = self._h_taint_flow(code)
        scores["taint_flow"] = h1
        if h1 >= 0.5:
            findings.append({
                "type":           "taint_flow_risk",
                "severity":       "high" if h1 >= 0.8 else "medium",
                "line":           None,
                "description":    (
                    "User input source (scanf/argv/fgets) flows into a buffer "
                    "write (strcpy/memcpy) without an apparent size check."
                ),
                "cwe_id":         "CWE-120",
                "recommendation": (
                    "Validate input length before copying into fixed-size buffers."
                ),
                "confidence":     h1,
                "source":         "heuristic",
            })

        # H2: Unchecked malloc return
        h2 = self._h_unchecked_malloc(code)
        scores["unchecked_malloc"] = h2
        if h2 >= 0.6:
            findings.append({
                "type":           "unchecked_malloc",
                "severity":       "medium",
                "line":           None,
                "description":    (
                    "malloc/calloc/realloc return value not checked for NULL "
                    "before use — NULL dereference on allocation failure."
                ),
                "cwe_id":         "CWE-476",
                "recommendation": (
                    "Always check: if (!ptr) { /* handle error */ }"
                ),
                "confidence":     h2,
                "source":         "heuristic",
            })

        # H3: Signed integer used as size / array index
        h3 = self._h_signed_unsigned(code)
        scores["signed_unsigned_mismatch"] = h3
        if h3 >= 0.6:
            findings.append({
                "type":           "signed_unsigned_mismatch",
                "severity":       "medium",
                "line":           None,
                "description":    (
                    "Signed integer used as array index or in a malloc size "
                    "expression — negative value wraps to a large unsigned number."
                ),
                "cwe_id":         "CWE-195",
                "recommendation": (
                    "Use size_t or unsigned types for sizes and array indices."
                ),
                "confidence":     h3,
                "source":         "heuristic",
            })

        # H4: Integer overflow in malloc argument
        h4, h4_line = self._h_int_overflow_malloc(code)
        scores["int_overflow_malloc"] = h4
        if h4 >= 0.7:
            findings.append({
                "type":           "integer_overflow_malloc",
                "severity":       "high",
                "line":           h4_line,
                "description":    (
                    "malloc() called with a multiplication expression — "
                    "may overflow before allocation (CWE-190)."
                ),
                "cwe_id":         "CWE-190",
                "recommendation": (
                    "Check for overflow: if (a > SIZE_MAX / b) { /* error */ } "
                    "before malloc(a * b)."
                ),
                "confidence":     h4,
                "source":         "heuristic",
            })

        # H5: Fixed-size buffer written in a variable-bound loop
        h5, h5_line = self._h_buffer_loop_write(code, lines)
        scores["buffer_loop_write"] = h5
        if h5 >= 0.7:
            findings.append({
                "type":           "unbounded_loop_write",
                "severity":       "high",
                "line":           h5_line,
                "description":    (
                    "Fixed-size stack buffer written inside a loop whose bound "
                    "is a variable — potential stack buffer overflow."
                ),
                "cwe_id":         "CWE-121",
                "recommendation": (
                    "Add explicit bound check: ensure loop index < sizeof(buffer)."
                ),
                "confidence":     h5,
                "source":         "heuristic",
            })

        # H6: Recursive function with large local buffer
        h6 = self._h_recursive_large_buffer(code)
        scores["recursive_buffer"] = h6
        if h6 >= 0.6:
            findings.append({
                "type":           "stack_overflow_risk",
                "severity":       "medium",
                "line":           None,
                "description":    (
                    "Recursive function contains a large (>= 1 KB) local buffer — "
                    "deep recursion may exhaust the call stack."
                ),
                "cwe_id":         "CWE-674",
                "recommendation": (
                    "Use dynamic allocation or an iterative approach for "
                    "large buffers inside recursive functions."
                ),
                "confidence":     h6,
                "source":         "heuristic",
            })

        # H7: Global variable modified inside thread-like functions without lock
        h7 = self._h_global_thread_write(code)
        scores["global_thread_write"] = h7
        if h7 >= 0.6:
            findings.append({
                "type":           "race_condition_risk",
                "severity":       "medium",
                "line":           None,
                "description":    (
                    "Global variable modified inside a thread-like function "
                    "without an apparent mutex or atomic guard."
                ),
                "cwe_id":         "CWE-362",
                "recommendation": (
                    "Protect shared global state with a mutex or use std::atomic."
                ),
                "confidence":     h7,
                "source":         "heuristic",
            })

        return findings, scores

    # ── Heuristic implementations ──────────────────────────────────────────────

    def _h_taint_flow(self, code: str) -> float:
        has_input  = bool(re.search(
            r"\b(scanf|fgets|gets|argv|cin\s*>>|read\s*\()", code
        ))
        has_sink   = bool(re.search(
            r"\b(strcpy|strcat|memcpy|memmove|sprintf)\s*\(", code
        ))
        has_guard  = bool(re.search(
            r"\b(strlen|sizeof|strncpy|snprintf|strlcpy|strncat)\s*\(", code
        ))
        score = 0.0
        if has_input: score += 0.4
        if has_sink:  score += 0.4
        if has_guard: score -= 0.3
        return max(0.0, min(1.0, score))

    def _h_unchecked_malloc(self, code: str) -> float:
        malloc_count = len(re.findall(r"\b(malloc|calloc|realloc)\s*\(", code))
        null_count   = len(re.findall(
            r"if\s*\(.*?==\s*NULL|\bif\s*\(!\s*\w+|\bassert\s*\(", code
        ))
        if malloc_count == 0:
            return 0.0
        ratio = null_count / malloc_count
        return min(0.9, 0.7 * (1.0 - ratio)) if ratio < 1.0 else 0.0

    def _h_signed_unsigned(self, code: str) -> float:
        score = 0.0
        int_vars = set(re.findall(r"\bint\s+(\w+)\s*[=;]", code))
        for var in int_vars:
            if re.search(rf"\bmalloc\s*\([^)]*\b{re.escape(var)}\b", code):
                score += 0.4
                break
        if re.search(r"\bint\s+\w+\s*;.*?\[\s*\w+\s*\]", code, re.DOTALL):
            score += 0.3
        return min(0.9, score)

    def _h_int_overflow_malloc(self, code: str) -> Tuple[float, Optional[int]]:
        pattern = re.compile(r"\bmalloc\s*\(\s*(\w+)\s*\*\s*(\w+)\s*\)")
        for m in pattern.finditer(code):
            ln = code[: m.start()].count("\n") + 1
            preceding = code[: m.start()][-500:]
            has_guard = bool(re.search(
                r"if\s*\([^)]*>\s*(?:SIZE_MAX|INT_MAX|UINT_MAX)", preceding
            ))
            if not has_guard:
                return 0.85, ln
        return 0.0, None

    def _h_buffer_loop_write(self, code: str,
                              lines: List[str]) -> Tuple[float, Optional[int]]:
        has_buf  = bool(re.search(r"char\s+\w+\s*\[\d+\]", code))
        loop_m   = re.search(r"for\s*\([^;]*;\s*\w+\s*<\s*(\w+)\s*;", code)
        if has_buf and loop_m:
            bound = loop_m.group(1)
            if not bound.isdigit():
                ln = code[: loop_m.start()].count("\n") + 1
                if re.search(r"\w+\s*\[\s*\w+\s*\]\s*=", code):
                    return 0.8, ln
        return 0.0, None

    def _h_recursive_large_buffer(self, code: str) -> float:
        fn_re  = re.compile(r"\w+\s+(\w+)\s*\([^)]*\)\s*\{", re.MULTILINE)
        buf_re = re.compile(r"char\s+\w+\s*\[(\d+)\]")
        for fn_m in fn_re.finditer(code):
            fn_name = fn_m.group(1)
            body = code[fn_m.start(): fn_m.start() + 1000]
            if re.search(rf"\b{re.escape(fn_name)}\s*\(", code[fn_m.end(): fn_m.end() + 500]):
                for buf_m in buf_re.finditer(body):
                    if int(buf_m.group(1)) >= 1024:
                        return 0.75
        return 0.0

    def _h_global_thread_write(self, code: str) -> float:
        global_vars = set(re.findall(
            r"^(?:int|char|float|double|long|unsigned)\s+(\w+)\s*[=;]",
            code, re.MULTILINE,
        ))
        has_thread_fn = bool(re.search(
            r"(?:thread|worker|task|handler|callback|run)\w*\s*\([^)]*\)\s*\{",
            code, re.IGNORECASE | re.MULTILINE,
        ))
        if not global_vars or not has_thread_fn:
            return 0.0
        has_lock = bool(re.search(
            r"\b(mutex|lock|pthread_mutex|std::mutex|atomic)", code
        ))
        if has_lock:
            return 0.0
        for var in global_vars:
            if re.search(rf"\b{re.escape(var)}\s*[+\-*|&^]?=", code):
                return 0.7
        return 0.0

    # ── Layer 3: LLM scan ─────────────────────────────────────────────────────

    def _llm_scan(self, optimized_code: str, original_code: str,
                  baseline_types: List[str]
                  ) -> Tuple[List[Dict], List[str], str, float]:
        prompt = SecurityPromptTemplate.build(
            optimized_code, original_code, baseline_types
        )
        raw = self.llm.generate(prompt, system_prompt=SecurityPromptTemplate.SYSTEM)
        cot = self.cot_val.validate(raw)
        if cot.is_valid:
            for f in cot.findings:
                f.setdefault("source", "llm")
                f["confidence"] = min(0.7, cot.confidence)
                f.setdefault("cwe_id", None)
                f.setdefault("recommendation", "Review and fix the identified vulnerability.")
            return cot.findings, cot.reasoning_steps, cot.conclusion, cot.confidence
        else:
            logger.warning(f"SecurityAgent: LLM CoT invalid — {cot.error}")
            return (
                [],
                ["LLM unavailable — rule+heuristic analysis only."],
                "LLM analysis skipped.",
                0.0,
            )

    # ── Layer 4: cppcheck ─────────────────────────────────────────────────────

    def _cppcheck_scan(self, code: str, file_path: str) -> List[Dict]:
        """Write code to a temp file, run cppcheck --xml, parse XML output."""
        import tempfile
        findings: List[Dict] = []
        tmp_path: Optional[str] = None
        try:
            suffix = ".cpp" if str(file_path).endswith(".cpp") else ".c"
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=suffix, delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(code)
                tmp_path = tmp.name

            result = subprocess.run(
                [
                    "cppcheck",
                    "--xml", "--xml-version=2",
                    "--enable=warning,error",
                    "--quiet",
                    tmp_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stderr.strip():
                findings = self._parse_cppcheck_xml(result.stderr)

        except subprocess.TimeoutExpired:
            logger.warning("SecurityAgent: cppcheck timed out (30 s)")
        except FileNotFoundError:
            logger.warning("SecurityAgent: cppcheck binary not found")
        except Exception as exc:
            logger.warning(f"SecurityAgent: cppcheck error — {exc}")
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        return findings

    def _parse_cppcheck_xml(self, xml_text: str) -> List[Dict]:
        findings: List[Dict] = []
        _sev_map = {
            "error": "high", "warning": "medium",
            "style": "low", "performance": "low",
            "portability": "low", "information": "low",
        }
        try:
            root = ET.fromstring(xml_text)
            for error in root.iter("error"):
                raw_sev  = error.get("severity", "warning")
                severity = _sev_map.get(raw_sev, "low")
                cwe      = error.get("cwe")
                msg      = error.get("msg", "cppcheck finding")
                eid      = error.get("id", "unknown")
                ln: Optional[int] = None
                loc = error.find("location")
                if loc is not None:
                    try:
                        ln = int(loc.get("line", 0)) or None
                    except (ValueError, TypeError):
                        ln = None
                findings.append({
                    "type":           f"cppcheck_{eid}",
                    "severity":       severity,
                    "line":           ln,
                    "description":    msg,
                    "cwe_id":         f"CWE-{cwe}" if cwe else None,
                    "recommendation": "Review and fix per cppcheck guidance.",
                    "confidence":     0.85,
                    "source":         "cppcheck",
                })
        except ET.ParseError as exc:
            logger.warning(f"SecurityAgent: cppcheck XML parse error — {exc}")
        return findings

    # ── New vulnerability comparison ───────────────────────────────────────────

    def _find_new_vulnerabilities(
        self, orig_findings: List[Dict], opt_findings: List[Dict]
    ) -> List[Dict]:
        """
        Return findings in opt_findings whose type was NOT present in orig_findings.
        Line numbers are intentionally ignored because optimization shifts lines.
        """
        orig_types = {f["type"] for f in orig_findings}
        return [f for f in opt_findings if f["type"] not in orig_types]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _compute_risk(self, findings: List[Dict]) -> str:
        if not findings:
            return "none"
        sevs = [f.get("severity", "low") for f in findings]
        if "high" in sevs:
            return "critical" if sevs.count("high") >= 3 else "high"
        if "medium" in sevs:
            return "medium"
        return "low"

    def _build_summary(
        self,
        file_path: str,
        all_vulns: List[Dict],
        new_vulns: List[Dict],
        risk: str,
        status: str,
    ) -> str:
        high   = sum(1 for v in all_vulns if v.get("severity") == "high")
        medium = sum(1 for v in all_vulns if v.get("severity") == "medium")
        low    = sum(1 for v in all_vulns if v.get("severity") == "low")
        lines  = [
            f"Security Report: {file_path}",
            f"Status        : {status}",
            f"Overall Risk  : {risk.upper()}",
            f"Findings      : {len(all_vulns)} "
            f"(High: {high}, Medium: {medium}, Low: {low})",
            f"New vulns     : {len(new_vulns)} introduced by optimization",
        ]
        if new_vulns:
            lines.append("Newly introduced vulnerabilities:")
            for v in new_vulns:
                ln  = f" [line {v['line']}]" if v.get("line") else ""
                cwe = f" {v['cwe_id']}" if v.get("cwe_id") else ""
                lines.append(
                    f"  ! [{v.get('severity','?').upper()}]{ln}{cwe} "
                    f"{v.get('type')}: {v.get('description')}"
                )
        return "\n".join(lines)

    @staticmethod
    def _check_cppcheck() -> bool:
        try:
            subprocess.run(
                ["cppcheck", "--version"],
                capture_output=True, timeout=5,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
