"""
Analysis Agent — Week 6

Detects bugs, performance issues, and security vulnerabilities in C/C++ code.
Uses a hybrid approach:
  1. Rule-based pattern matching (always works, no LLM required)
  2. LLM reasoning via Qwen 2.5 Coder (enriches results when online)
"""

import logging
import os
import re
import time
from copy import deepcopy
from typing import Any, Dict, List

# Add project root to sys.path if needed
import sys
_root = os.path.join(os.path.dirname(__file__), "..", "..")
if _root not in sys.path:
    sys.path.insert(0, _root)

from agent_framework import BaseAgent, ContextManager
from src.domains.domain_rules import detect_domain_findings
from src.llm.llm_client import LLMClient
from src.llm.prompt_templates import AnalysisPromptTemplate
from src.parser.code_parser import CodeParser
from src.reasoning.cot_validator import CoTValidator
from src.runtime_cache import ResultCache, make_cache_key

logger = logging.getLogger(__name__)
_ANALYSIS_CACHE = ResultCache(max_entries=128)


class AnalysisAgent(BaseAgent):
    """
    Analysis Agent: detects code issues in C/C++ source files.

    Input  (passed to process()):
        {
            "source_code": "<C++ source as string>",
            "file_path":   "<optional path for labelling>"
        }

    Output:
        {
            "file_path":        str,
            "rule_findings":    [...],   # always populated
            "llm_findings":     [...],   # populated if LLM online
            "all_findings":     [...],   # merged, deduplicated
            "reasoning_steps":  [...],
            "conclusion":       str,
            "confidence":       float,
            "summary":          str,     # text for display
        }
    """

    def __init__(self, agent_id: str, context_manager: ContextManager,
                 llm_client: LLMClient = None):
        super().__init__(agent_id, "analysis", context_manager)
        self.llm     = llm_client or LLMClient()
        self.parser  = CodeParser()
        self.cot_val = CoTValidator()

    # ── BaseAgent interface ────────────────────────────────────────────────────

    def get_capabilities(self) -> List[str]:
        return [
            "uninitialized_variable_detection",
            "buffer_overflow_detection",
            "nested_loop_detection",
            "memory_leak_detection",
            "division_by_zero_detection",
            "llm_severity_classification",
        ]

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point called by the base agent framework."""
        source_code = input_data.get("source_code", "")
        file_path   = input_data.get("file_path", "<unknown>")
        cache_enabled = input_data.get("use_cache", True)

        if not source_code:
            logger.error("AnalysisAgent: no source_code provided")
            return {"error": "No source_code provided", "all_findings": []}

        cache_key = make_cache_key("analysis", source_code)
        if cache_enabled:
            cached = _ANALYSIS_CACHE.get(cache_key)
            if cached is not None:
                cached_result = deepcopy(cached)
                cached_result["cache_hit"] = True
                self.context.set("analysis_results", cached_result)
                self.context.set("original_code", source_code)
                self.context.set("source_file", file_path)
                return cached_result

        logger.info(f"AnalysisAgent: parsing '{os.path.basename(file_path)}' "
                    f"({len(source_code)} chars)")
        parse_started = time.perf_counter()
        # 1. Parse
        parse_result = self.parser.parse_string(source_code, file_path)
        parse_elapsed = time.perf_counter() - parse_started
        rule_started = time.perf_counter()

        logger.debug(f"AnalysisAgent: parse done — {parse_result.line_count} lines, "
                     f"{len(parse_result.functions)} function(s), "
                     f"max loop depth={parse_result.max_loop_depth}")

        # 2. Rule-based findings (offline-capable)
        logger.info("AnalysisAgent: running rule-based checks …")
        rule_findings = self._rule_based_analysis(parse_result, source_code)
        domain_findings = detect_domain_findings(source_code)
        if domain_findings:
            rule_findings.extend(domain_findings)
        rule_elapsed = time.perf_counter() - rule_started
        logger.info(f"AnalysisAgent: rule-based → {len(rule_findings)} finding(s)")

        # 3. LLM-based findings (enriches when online)
        logger.info("AnalysisAgent: calling LLM for enrichment …")
        llm_started = time.perf_counter()
        llm_findings, reasoning_steps, conclusion, confidence = \
            self._llm_analysis(source_code, file_path, parse_result, rule_findings)
        llm_elapsed = time.perf_counter() - llm_started

        logger.info(f"AnalysisAgent: LLM returned {len(llm_findings)} additional finding(s) "
                     f"(confidence={confidence:.2f})")

        # 4. Merge
        all_findings = self._merge_findings(rule_findings, llm_findings)
        logger.info(f"AnalysisAgent: merged total = {len(all_findings)} finding(s)")

        result = {
            "file_path":       file_path,
            "rule_findings":   rule_findings,
            "llm_findings":    llm_findings,
            "all_findings":    all_findings,
            "reasoning_steps": reasoning_steps,
            "conclusion":      conclusion,
            "confidence":      confidence,
            "cache_hit":       False,
            "summary":         self._build_summary(file_path, all_findings, conclusion),
            "parse_meta": {
                "line_count":      parse_result.line_count,
                "functions":       [f.name for f in parse_result.functions],
                "has_nested_loops": parse_result.has_nested_loops,
                "max_loop_depth":  parse_result.max_loop_depth,
            },
            "stage_timings": {
                "parse_s": round(parse_elapsed, 4),
                "rule_s": round(rule_elapsed, 4),
                "llm_s": round(llm_elapsed, 4),
            },
        }

        # Store in shared context
        self.context.set("analysis_results", result)
        self.context.set("original_code", source_code)
        self.context.set("source_file", file_path)
        if cache_enabled:
            _ANALYSIS_CACHE.set(cache_key, deepcopy(result))

        logger.info(f"Analysis complete: {len(all_findings)} findings in {file_path}")
        return result

    # ── Rule-based analysis ───────────────────────────────────────────────────

    def _rule_based_analysis(self, parse_result, source_code: str) -> List[Dict]:
        findings = []

        # Uninitialized variables
        for v in parse_result.uninitialized_vars:
            findings.append({
                "type":           "uninitialized_variable",
                "description":    (
                    f"Variable '{v['variable']}' declared at line "
                    f"{v['declared_line']} may be used before initialization."
                ),
                "recommendation": f"Initialize at declaration: `int {v['variable']} = 0;`",
                "line":           v["declared_line"],
                "severity":       "high",
                "source":         "rule",
            })

        # Buffer overflow heuristic: array[N] accessed with <= N in loop
        if parse_result.has_nested_loops or parse_result.loops:
            for acc in parse_result.array_accesses:
                if acc.get("is_var_index"):
                    findings.append({
                        "type":           "potential_buffer_overflow",
                        "description":    (
                            f"Array '{acc['array']}' accessed with variable index "
                            f"'{acc['index']}' at line {acc['line']}. "
                            "Verify bounds checking."
                        ),
                        "recommendation": f"Add a bounds check: `if ({acc['index']} < sizeof({acc['array']})/sizeof({acc['array']}[0]))`",
                        "line":           acc["line"],
                        "severity":       "high",
                        "source":         "rule",
                    })

        # Off-by-one in for-loop array access: i <= N instead of i < N
        off_by_one = re.findall(
            r'for\s*\([^;]*;\s*\w+\s*<=\s*(\d+)', source_code
        )
        if off_by_one:
            for ln_no, ln in enumerate(source_code.splitlines(), 1):
                if re.search(r'for\s*\([^;]*;\s*\w+\s*<=\s*\d+', ln):
                    findings.append({
                        "type":           "off_by_one_error",
                        "description":    (
                            f"Loop at line {ln_no} uses '<=' which may cause "
                            "off-by-one buffer overflow."
                        ),
                        "recommendation": "Change `<=` to `<` in the loop condition.",
                        "line":           ln_no,
                        "severity":       "high",
                        "source":         "rule",
                    })

        # Nested O(n²) loops
        if parse_result.has_nested_loops:
            findings.append({
                "type":           "algorithmic_inefficiency",
                "description":    (
                    "Nested loops detected (potential O(n²) complexity). "
                    "Consider algorithmic optimization."
                ),
                "recommendation": "Replace nested loops with a hash map or sorting-based approach to reduce complexity.",
                "line":           None,
                "severity":       "medium",
                "source":         "rule",
            })

        # Memory: malloc without free
        if len(parse_result.malloc_calls) > len(parse_result.free_calls):
            findings.append({
                "type":           "memory_leak",
                "description":    (
                    f"{len(parse_result.malloc_calls)} malloc call(s) but only "
                    f"{len(parse_result.free_calls)} free call(s) found."
                ),
                "recommendation": "Ensure every malloc() has a corresponding free() on all exit paths. Consider using a cleanup label or RAII.",
                "line":           parse_result.malloc_calls[0] if parse_result.malloc_calls else None,
                "severity":       "high",
                "source":         "rule",
            })

        # Division by zero heuristic — strip comments first to avoid false positives
        _src_nc = re.sub(r'//[^\n]*', '', source_code)                       # remove // comments
        _src_nc = re.sub(r'/\*.*?\*/', '', _src_nc, flags=re.DOTALL)         # remove /* */ blocks
        _CPP_KW = frozenset({
            'int', 'char', 'float', 'double', 'long', 'short', 'unsigned',
            'bool', 'void', 'return', 'if', 'else', 'for', 'while', 'do',
            'switch', 'case', 'break', 'continue', 'struct', 'class',
        })
        # Only match: something / varname  (not: varname / literal)
        div_pattern = re.findall(r'\b\w+\s*/\s*(\w+)\b', _src_nc)
        seen_div = set()
        for var in div_pattern:
            if var in seen_div or var in _CPP_KW:
                continue
            seen_div.add(var)
            # Only flag if var is assigned 0 as a direct statement
            if re.search(rf'(?:^|\s){re.escape(var)}\s*=\s*0\s*;', _src_nc, re.MULTILINE):
                findings.append({
                    "type":           "division_by_zero_risk",
                    "description":    f"Variable '{var}' may be 0 when used as divisor.",
                    "recommendation": f"Add a guard before division: `if ({var} != 0) {{ ... }}`",
                    "line":           None,
                    "severity":       "high",
                    "source":         "rule",
                })

        # Type mismatch: string literal assigned to integer variable
        # e.g.  int count = "five";   int flag = "true";
        int_string_re = re.compile(
            r'\b(int|long|short|unsigned)\s+(\w+)\s*=\s*"([^"]*)"',
            re.MULTILINE,
        )
        for m in int_string_re.finditer(_src_nc):
            ln_no = _src_nc[:m.start()].count("\n") + 1
            int_type = m.group(1)
            var      = m.group(2)
            val      = m.group(3)
            findings.append({
                "type":           "type_mismatch_int_string",
                "description":    (
                    f"Variable '{var}' is declared as '{int_type}' but assigned "
                    f"a string literal \"{val}\". "
                    "This stores a pointer address, not the intended value."
                ),
                "recommendation": f"Change the type to `const char* {var} = \"{val}\";` or assign a numeric value.",
                "line":           ln_no,
                "severity":       "high",
                "source":         "rule",
            })

        # Redundant / loop-invariant statements inside a loop body
        for body, body_offset, loop_var in self._extract_loop_bodies(source_code):
            # R1: strlen(arg) where arg is not the loop variable
            for sm in re.finditer(r'\bstrlen\s*\(\s*(\w+)\s*\)', body):
                arg = sm.group(1)
                if arg != loop_var:
                    ln_no = source_code[:body_offset + sm.start()].count("\n") + 1
                    findings.append({
                        "type":           "loop_invariant_strlen",
                        "description":    (
                            f"strlen({arg}) is called on every iteration but '{arg}' "
                            "does not change inside the loop — compute it once before the loop."
                        ),
                        "recommendation": f"Hoist before the loop: `size_t len_{arg} = strlen({arg});` and use `len_{arg}` inside.",
                        "line":           ln_no,
                        "severity":       "medium",
                        "source":         "rule",
                    })

            # R2: constant integer declaration inside loop  e.g.  int x = 5;
            for cm in re.finditer(
                r'\b(?:int|float|double|long|short)\s+\w+\s*=\s*\d+\s*;', body
            ):
                ln_no = source_code[:body_offset + cm.start()].count("\n") + 1
                # skip for-loop init declarations: "for (int j = 0; ...)"
                full_line = source_code.splitlines()[ln_no - 1].strip()
                if full_line.startswith("for"):
                    continue
                var_m = re.search(r'\b(\w+)\s*=\s*\d+', cm.group())
                var   = var_m.group(1) if var_m else "variable"
                findings.append({
                    "type":           "redundant_constant_in_loop",
                    "description":    (
                        f"Constant value assigned to '{var}' inside the loop body. "
                        "Move this declaration outside the loop to avoid repeated allocation."
                    ),
                    "recommendation": f"Move `{cm.group().strip()}` to before the loop.",
                    "line":           ln_no,
                    "severity":       "low",
                    "source":         "rule",
                })

            # R3: sizeof expression inside a loop — sizeof never changes at runtime
            for sm in re.finditer(r'\bsizeof\s*\(', body):
                ln_no = source_code[:body_offset + sm.start()].count("\n") + 1
                findings.append({
                    "type":           "loop_invariant_sizeof",
                    "description":    (
                        "sizeof() is evaluated inside the loop. "
                        "sizeof is a compile-time constant — assign it to a variable before the loop."
                    ),
                    "recommendation": "Hoist before the loop: `const size_t sz = sizeof(...);` and use `sz` inside.",
                    "line":           ln_no,
                    "severity":       "low",
                    "source":         "rule",
                })

        # Empty if / else body
        _lines = source_code.splitlines()
        empty_if_re   = re.compile(r'\bif\s*\([^)]*\)\s*\{\s*\}')
        empty_else_re = re.compile(r'\belse\s*\{\s*\}')
        for ln_no, ln in enumerate(_lines, 1):
            if empty_if_re.search(ln):
                findings.append({
                    "type":           "empty_if_body",
                    "description":    (
                        f"Empty if-body at line {ln_no}. "
                        "The condition has no effect — add logic or remove the block."
                    ),
                    "recommendation": "Add the intended logic inside the if-block or remove the empty `if (...) {}`.",
                    "line":           ln_no,
                    "severity":       "medium",
                    "source":         "rule",
                })
            if empty_else_re.search(ln):
                findings.append({
                    "type":           "empty_else_body",
                    "description":    (
                        f"Empty else-body at line {ln_no}. "
                        "The else branch has no effect — add logic or remove it."
                    ),
                    "recommendation": "Remove the empty `else {}` or add the intended logic inside.",
                    "line":           ln_no,
                    "severity":       "medium",
                    "source":         "rule",
                })

        # Dead code after return
        # Strategy: when a line contains a complete return statement, look at the
        # next non-empty / non-comment line. If it has the same or greater indent
        # and is not a closing brace / case / default, it is unreachable.
        i = 0
        while i < len(_lines):
            raw_line    = _lines[i]
            stripped    = raw_line.strip()
            # skip comment-only lines
            if stripped.startswith("//") or stripped.startswith("/*"):
                i += 1
                continue
            # a line that contains a return statement and ends the statement (has ';')
            if re.search(r'\breturn\b', stripped) and ";" in stripped:
                return_indent = len(raw_line) - len(raw_line.lstrip())
                j = i + 1
                while j < len(_lines):
                    next_raw     = _lines[j]
                    next_stripped = next_raw.strip()
                    if not next_stripped or next_stripped.startswith("//"):
                        j += 1
                        continue
                    next_indent = len(next_raw) - len(next_raw.lstrip())
                    if (next_indent >= return_indent
                            and not re.match(r'^[})\]]|^case\b|^default\b', next_stripped)):
                        findings.append({
                            "type":           "dead_code_after_return",
                            "description":    (
                                f"Statement at line {j + 1} is unreachable — "
                                f"it follows a 'return' at line {i + 1}."
                            ),
                            "recommendation": "Remove or relocate the unreachable code.",
                            "line":           j + 1,
                            "severity":       "medium",
                            "source":         "rule",
                        })
                    break
            i += 1

        # Deduplicate: same (type, line) pair can be emitted by both outer and
        # inner loop passes in _extract_loop_bodies — keep first occurrence only.
        seen_keys: set = set()
        deduped: List[Dict] = []
        for f in findings:
            key = (f["type"], f.get("line"))
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(f)
        findings = deduped

        logger.debug(f"Rule-based: {len(findings)} findings")
        return findings

    # ── Loop body extractor ────────────────────────────────────────────────────

    def _extract_loop_bodies(self, source_code: str):
        """
        Yields (body_str, body_start_offset, loop_variable) for every
        for/while loop found in source_code.

        body_start_offset is the character index of '{' in source_code so
        callers can compute absolute line numbers.
        """
        # Match for-loops and capture the loop variable (first identifier after '(')
        for_re = re.compile(
            r'\bfor\s*\(\s*(?:(?:int|size_t|unsigned|long)\s+)?(\w+)\s*='
        )
        # while loops have no obvious loop variable — use empty string
        while_re = re.compile(r'\bwhile\s*\(')

        candidates = []
        for m in for_re.finditer(source_code):
            candidates.append((m.start(), m.group(1)))
        for m in while_re.finditer(source_code):
            candidates.append((m.start(), ""))

        for start_pos, loop_var in candidates:
            brace_pos = source_code.find("{", start_pos)
            if brace_pos == -1:
                continue
            depth, end_pos = 0, brace_pos
            for i, ch in enumerate(source_code[brace_pos:], start=brace_pos):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end_pos = i
                        break
            body = source_code[brace_pos + 1: end_pos]
            yield body, brace_pos + 1, loop_var

    # ── LLM-based analysis ────────────────────────────────────────────────────

    def _llm_analysis(self, source_code, file_path, parse_result, rule_findings):
        if not self.llm.is_available():
            logger.info("AnalysisAgent: LLM not available — skipping LLM enrichment")
            return [], ["LLM unavailable — rule-based analysis only."], \
                   f"{len(rule_findings)} rule-based finding(s).", 0.85

        prompt = AnalysisPromptTemplate.build(
            source_code,
            file_path,
            parse_result.to_summary(),
        )
        raw = self.llm.generate(
            prompt,
            system_prompt=AnalysisPromptTemplate.SYSTEM,
        )

        if "offline stub" in raw.lower():
            logger.warning("AnalysisAgent: LLM returned stub (API unavailable) — skipping LLM findings")
            return [], ["LLM returned stub response — rule-based analysis only."], \
                   f"{len(rule_findings)} rule-based finding(s).", 0.85

        cot = self.cot_val.validate(raw)
        if cot.is_valid:
            logger.info(f"AnalysisAgent: LLM CoT valid — {len(cot.findings)} finding(s)")
            return cot.findings, cot.reasoning_steps, cot.conclusion, cot.confidence
        else:
            logger.warning(f"LLM CoT invalid: {cot.error}")
            return [], ["Rule-based analysis only (LLM CoT invalid)."], \
                   f"{len(rule_findings)} rule-based findings.", 0.6

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _merge_findings(self, rule: List[Dict], llm: List[Dict]) -> List[Dict]:
        """Merge rule-based and LLM findings, deduplicating on (type, line) pair."""
        merged = list(rule)
        seen = {(f["type"], f.get("line")) for f in rule}
        for f in llm:
            key = (f.get("type", "unknown"), f.get("line"))
            if key not in seen:
                f.setdefault("source", "llm")
                merged.append(f)
                seen.add(key)
        return merged

    def _build_summary(self, file_path, findings, conclusion) -> str:
        high   = sum(1 for f in findings if f.get("severity") == "high")
        medium = sum(1 for f in findings if f.get("severity") == "medium")
        low    = sum(1 for f in findings if f.get("severity") == "low")
        lines  = [
            f"Analysis Report: {file_path}",
            f"Total findings : {len(findings)} "
            f"(High: {high}, Medium: {medium}, Low: {low})",
            f"Conclusion     : {conclusion}",
        ]
        for i, f in enumerate(findings, 1):
            sev  = f.get("severity", "?").upper()
            ln   = f" [line {f['line']}]" if f.get("line") else ""
            lines.append(f"  {i}. [{sev}]{ln} {f.get('type')}: {f.get('description')}")
        return "\n".join(lines)
