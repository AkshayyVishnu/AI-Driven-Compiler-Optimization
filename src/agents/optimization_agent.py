"""
Optimization Agent — Week 6

Transforms C/C++ code to fix detected issues and improve performance.
Uses a hybrid approach:
  1. Rule-based auto-fixes (always work offline)
  2. LLM-generated optimizations (when Ollama is available)

Saves output to MicroBenchmarks/Generated_optimisation/
"""

import difflib
import logging
import os
import re
import time
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

import sys
_root = os.path.join(os.path.dirname(__file__), "..", "..")
if _root not in sys.path:
    sys.path.insert(0, _root)

from agent_framework import BaseAgent, ContextManager
from src.domains.domain_rules import apply_domain_optimizations
from src.llm.llm_client import LLMClient
from src.llm.prompt_templates import OptimizationPromptTemplate
from src.reasoning.cot_validator import CoTValidator
from src.runtime_cache import ResultCache, make_cache_key

logger = logging.getLogger(__name__)
_OPTIMIZATION_CACHE = ResultCache(max_entries=128)

# Where optimized files get saved
_OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MicroBenchmarks", "Generated_optimisation"
)


class OptimizationAgent(BaseAgent):
    """
    Optimization Agent: fixes bugs and improves performance of C/C++ code.

    Input  (passed to process()):
        {
            "source_code":     "<C++ source string>",
            "file_path":       "<optional original path>",
            "analysis_report": {<output from AnalysisAgent>}   # optional
        }

    Output:
        {
            "file_path":        str,
            "original_code":    str,
            "optimized_code":   str,
            "unified_diff":     str,
            "transformations":  [...],
            "reasoning_steps":  [...],
            "conclusion":       str,
            "confidence":       float,
            "output_file":      str,    # path where file was saved
            "summary":          str,
        }
    """

    def __init__(self, agent_id: str, context_manager: ContextManager,
                 llm_client: LLMClient = None, output_dir: str = _OUTPUT_DIR):
        super().__init__(agent_id, "optimization", context_manager)
        self.llm        = llm_client or LLMClient()
        self.cot_val    = CoTValidator()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # ── BaseAgent interface ────────────────────────────────────────────────────

    def get_capabilities(self) -> List[str]:
        return [
            "off_by_one_fix",
            "uninitialized_variable_fix",
            "loop_bound_correction",
            "algorithm_replacement_suggestion",
            "diff_generation",
            "llm_code_transformation",
        ]

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        source_code     = input_data.get("source_code", "")
        file_path       = input_data.get("file_path", "<unknown>")
        analysis_report = input_data.get("analysis_report") or \
                          self.context.get("analysis_results") or {}
        cache_enabled = input_data.get("use_cache", True)

        if not source_code:
            logger.error("OptimizationAgent: no source_code provided")
            return {"error": "No source_code provided"}

        cache_key = make_cache_key(
            "optimization",
            source_code,
            [finding.get("type") for finding in analysis_report.get("all_findings", [])],
        )
        if cache_enabled:
            cached = _OPTIMIZATION_CACHE.get(cache_key)
            if cached is not None:
                cached_result = deepcopy(cached)
                cached_result["cache_hit"] = True
                self.context.set("optimization_suggestions", cached_result)
                return cached_result

        logger.info(f"OptimizationAgent: optimising '{os.path.basename(file_path)}'")
        n_findings = len(analysis_report.get('all_findings', []))
        logger.info(f"OptimizationAgent: {n_findings} finding(s) from analysis to address")

        # 1. Rule-based fixes
        logger.info("OptimizationAgent: applying rule-based fixes …")
        rule_started = time.perf_counter()
        rule_code, rule_transforms = self._rule_based_fix(source_code, analysis_report)
        rule_elapsed = time.perf_counter() - rule_started

        logger.info(f"OptimizationAgent: {len(rule_transforms)} rule-based fix(es) applied")
        for t in rule_transforms:
            logger.debug(f"  → {t.get('type')}: {t.get('description')}")

        # 2. LLM transforms
        logger.info("OptimizationAgent: calling LLM for additional transforms …")
        llm_started = time.perf_counter()
        llm_code, llm_transforms, reasoning_steps, conclusion, confidence = \
            self._llm_optimize(source_code, analysis_report)
        llm_elapsed = time.perf_counter() - llm_started
        logger.info(f"OptimizationAgent: LLM produced "
                    f"{'new code' if (llm_code and llm_code != source_code) else 'no change'} "
                    f"+ {len(llm_transforms)} transform(s)")

        # 3. Choose best code: prefer LLM if it produced different code, else rule-based
        if llm_code and llm_code != source_code:
            final_code   = llm_code
            all_transforms = rule_transforms + llm_transforms
        else:
            final_code   = rule_code
            all_transforms = rule_transforms

        # 4. Build unified diff
        diff = self._make_diff(source_code, final_code, file_path)

        # 5. Save to disk
        output_file = self._save_output(final_code, file_path)

        result = {
            "file_path":       file_path,
            "original_code":   source_code,
            "optimized_code":  final_code,
            "unified_diff":    diff,
            "transformations": all_transforms,
            "reasoning_steps": reasoning_steps,
            "conclusion":      conclusion,
            "confidence":      confidence,
            "cache_hit":       False,
            "output_file":     output_file,
            "stage_timings": {
                "rule_s": round(rule_elapsed, 4),
                "llm_s": round(llm_elapsed, 4),
            },
            "summary":         self._build_summary(
                file_path, all_transforms, conclusion, diff
            ),
        }

        # Store in shared context
        self.context.set("optimization_suggestions", result)
        if cache_enabled:
            _OPTIMIZATION_CACHE.set(cache_key, deepcopy(result))

        logger.info(
            f"Optimization complete: {len(all_transforms)} transforms, "
            f"saved to {output_file}"
        )
        return result

    # ── Rule-based fixes ──────────────────────────────────────────────────────

    def _rule_based_fix(
        self, src: str, analysis_report: Dict
    ) -> Tuple[str, List[Dict]]:
        code   = src
        transforms: List[Dict] = []
        findings = analysis_report.get("all_findings", []) or \
                   analysis_report.get("rule_findings", [])

        # Group findings by type for efficient lookup
        by_type: Dict[str, List[Dict]] = {}
        for f in findings:
            by_type.setdefault(f.get("type", ""), []).append(f)

        # ── 1. Off-by-one / buffer overflow ──────────────────────────────────
        if "off_by_one_error" in by_type or "potential_buffer_overflow" in by_type:
            fixed, change = self._fix_off_by_one(code)
            if change:
                code = fixed
                transforms.append({
                    "type":        "off_by_one_fix",
                    "description": "Changed '<=' to '<' in loop condition to prevent buffer overflow.",
                    "severity":    "info",
                })

        # ── 2. Uninitialized variables ────────────────────────────────────────
        for finding in by_type.get("uninitialized_variable", []):
            var = self._extract_varname(finding.get("description", ""))
            if var:
                fixed, change = self._fix_uninit_var(code, var)
                if change:
                    code = fixed
                    transforms.append({
                        "type":        "initialize_variable",
                        "description": f"Initialized variable '{var}' to 0.",
                        "severity":    "info",
                    })

        # ── 3. Type mismatch: int var = "str" → const char* ──────────────────
        if by_type.get("type_mismatch_int_string"):
            fixed, change = self._fix_type_mismatch(code)
            if change:
                code = fixed
                transforms.append({
                    "type":        "fix_type_mismatch",
                    "description": "Changed int variables assigned string literals to const char*.",
                    "severity":    "info",
                })

        # ── 4. Loop-invariant hoisting ────────────────────────────────────────
        invariant_findings = (
            by_type.get("loop_invariant_strlen", [])
            + by_type.get("redundant_constant_in_loop", [])
            + by_type.get("loop_invariant_sizeof", [])
        )
        if invariant_findings:
            fixed, inv_transforms = self._hoist_loop_invariants(code, invariant_findings)
            if inv_transforms:
                code = fixed
                transforms.extend(inv_transforms)

        # ── 5. Empty if bodies ────────────────────────────────────────────────
        if by_type.get("empty_if_body"):
            fixed, change = self._fix_empty_if_bodies(code)
            if change:
                code = fixed
                transforms.append({
                    "type":        "remove_empty_if",
                    "description": "Removed empty if-body blocks.",
                    "severity":    "info",
                })

        # ── 6. Empty else bodies ──────────────────────────────────────────────
        if by_type.get("empty_else_body"):
            fixed, change = self._fix_empty_else_bodies(code)
            if change:
                code = fixed
                transforms.append({
                    "type":        "remove_empty_else",
                    "description": "Removed empty else-body blocks.",
                    "severity":    "info",
                })

        # ── 7. Dead code after return ─────────────────────────────────────────
        if by_type.get("dead_code_after_return"):
            fixed, change = self._fix_dead_code_after_return(code)
            if change:
                code = fixed
                transforms.append({
                    "type":        "remove_dead_code",
                    "description": "Commented out unreachable code after return statements.",
                    "severity":    "info",
                })

        # ── 8. Memory leak: add free() for unfreed malloc vars ────────────────
        if by_type.get("memory_leak"):
            fixed, change = self._fix_memory_leak(code)
            if change:
                code = fixed
                transforms.append({
                    "type":        "fix_memory_leak",
                    "description": "Added free() calls for unfreed malloc'd variables.",
                    "severity":    "info",
                })

        # ── 9. Strength reduction: multiply/divide by powers of 2 → bit shifts ──
        fixed, sr_transforms = self._apply_strength_reduction(code)
        if sr_transforms:
            code = fixed
            transforms.extend(sr_transforms)

        # ── 10. Pre-increment in for-loop iterators (i++ → ++i) ───────────────
        fixed, change = self._fix_postincrement_in_loops(code)
        if change:
            code = fixed
            transforms.append({
                "type":        "prefer_preincrement",
                "description": "Changed i++ to ++i in for-loop iterators (avoids copy for iterators).",
                "severity":    "info",
            })

        fixed, domain_transforms = apply_domain_optimizations(code)
        if domain_transforms:
            code = fixed
            transforms.extend(domain_transforms)

        return code, transforms

    def _fix_off_by_one(self, src: str) -> Tuple[str, bool]:
        """Replace `<= <integer>` in `for(...)` conditions → `< <integer>`."""
        pattern = re.compile(
            r'(for\s*\([^;]*;\s*\w+\s*)<=(\s*\d+)',
            re.MULTILINE,
        )
        new_src, n = pattern.subn(lambda m: m.group(1) + "<" + m.group(2), src)
        return new_src, n > 0

    def _fix_uninit_var(self, src: str, varname: str) -> Tuple[str, bool]:
        """Add `= 0` to a bare variable declaration."""
        pattern = re.compile(
            r'(\b(?:int|float|double|char|long|short|unsigned|bool)\s+'
            + re.escape(varname) + r')\s*;'
        )
        new_src, n = pattern.subn(r'\g<1> = 0;', src)
        return new_src, n > 0

    def _fix_type_mismatch(self, src: str) -> Tuple[str, bool]:
        """Change `int/long/short/unsigned var = "str"` → `const char* var = "str"`."""
        pattern = re.compile(
            r'\b(?:int|long|short|unsigned)\s+(\w+)\s*=\s*("(?:[^"]*)")',
            re.MULTILINE,
        )
        new_src, n = pattern.subn(r'const char* \1 = \2', src)
        return new_src, n > 0

    def _fix_empty_if_bodies(self, src: str) -> Tuple[str, bool]:
        """Remove lines containing only `if (cond) { }` (skips comment lines)."""
        lines = src.splitlines(keepends=True)
        new_lines: List[str] = []
        changed = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("*", "/*", "//")):
                new_lines.append(line)
                continue
            if re.search(r'\bif\s*\([^)]*\)\s*\{\s*\}', line):
                new_line = re.sub(r'\bif\s*\([^)]*\)\s*\{\s*\}\s*', '', line)
                changed = True
                if new_line.strip():
                    new_lines.append(new_line if new_line.endswith('\n') else new_line + '\n')
                # else: whole line was the empty-if — drop it
            else:
                new_lines.append(line)
        return ''.join(new_lines), changed

    def _fix_empty_else_bodies(self, src: str) -> Tuple[str, bool]:
        """Remove `else { }` clauses (skips comment lines)."""
        lines = src.splitlines(keepends=True)
        new_lines: List[str] = []
        changed = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("*", "/*", "//")):
                new_lines.append(line)
                continue
            new_line = re.sub(r'\s*else\s*\{\s*\}(\s*/\*.*?\*/)?', '', line)
            if new_line != line:
                changed = True
                new_line = new_line.rstrip('\n').rstrip() + '\n' if new_line.strip() else ''
                if new_line:
                    new_lines.append(new_line)
            else:
                new_lines.append(line)
        return ''.join(new_lines), changed

    def _fix_dead_code_after_return(self, src: str) -> Tuple[str, bool]:
        """Comment out statements that immediately follow a return at the same indent."""
        lines = src.splitlines(keepends=True)
        new_lines: List[str] = []
        changed = False
        skip_next = False
        return_indent = 0
        for line in lines:
            stripped = line.strip()
            if skip_next:
                if not stripped or stripped.startswith('//') or stripped.startswith('*'):
                    new_lines.append(line)
                    continue
                curr_indent = len(line) - len(line.lstrip())
                if (curr_indent >= return_indent
                        and not re.match(r'^[})\]]|^case\b|^default\b', stripped)):
                    indent = line[:curr_indent]
                    new_lines.append(f"{indent}// [dead code] {stripped}\n")
                    changed = True
                    skip_next = False
                    continue
                skip_next = False
            if re.search(r'\breturn\b', stripped) and ';' in stripped:
                skip_next = True
                return_indent = len(line) - len(line.lstrip())
            new_lines.append(line)
        return ''.join(new_lines), changed

    def _fix_memory_leak(self, src: str) -> Tuple[str, bool]:
        """Add free() before integer returns for malloc'd variables that were never freed."""
        malloc_re = re.compile(r'\b(\w+)\s*=\s*(?:\(\s*\w[\w\s]*\*\s*\))?\s*malloc\s*\(')
        free_re   = re.compile(r'\bfree\s*\(\s*(\w+)\s*\)')
        malloc_vars = {m.group(1) for m in malloc_re.finditer(src)}
        freed_vars  = {m.group(1) for m in free_re.finditer(src)}
        unfreed = malloc_vars - freed_vars
        if not unfreed:
            return src, False
        lines = src.splitlines(keepends=True)
        new_lines: List[str] = []
        changed = False
        for line in lines:
            stripped = line.strip()
            # Only add free before integer returns (main-like functions, not string returns)
            if re.match(r'return\s+-?\d+\s*;', stripped):
                indent = line[:len(line) - len(line.lstrip())]
                for var in sorted(unfreed):
                    new_lines.append(f"{indent}free({var}); /* fix: memory leak */\n")
                changed = True
            new_lines.append(line)
        return ''.join(new_lines), changed

    def _hoist_loop_invariants(
        self, src: str, findings: List[Dict]
    ) -> Tuple[str, List[Dict]]:
        """Move loop-invariant declarations to just before their enclosing loop."""
        transforms: List[Dict] = []
        code = src
        orig_lines = src.splitlines(keepends=True)

        for finding in sorted(findings, key=lambda f: f.get("line") or 0):
            line_no = finding.get("line")
            ftype   = finding.get("type", "")
            if not line_no or line_no > len(orig_lines):
                continue

            # Get the declaration text from the original source
            orig_stripped = orig_lines[line_no - 1].strip()
            if not orig_stripped or orig_stripped.startswith(("*", "/*", "//")):
                continue

            # Find this exact line in current (possibly modified) code
            current_lines = code.splitlines(keepends=True)
            found_idx = next(
                (i for i, cl in enumerate(current_lines) if cl.strip() == orig_stripped),
                None,
            )
            if found_idx is None:
                continue

            # Scan backwards from found_idx to find the innermost enclosing loop
            depth = 0
            enclosing_loop_idx: Optional[int] = None
            for i in range(found_idx - 1, -1, -1):
                for ch in reversed(current_lines[i]):
                    if ch == '{':
                        depth -= 1
                    elif ch == '}':
                        depth += 1
                if depth < 0:
                    # Found opening brace of enclosing block; look for for/while header
                    for j in range(i, max(i - 5, -1), -1):
                        if re.search(r'\b(?:for|while)\s*\(', current_lines[j]):
                            enclosing_loop_idx = j
                            break
                    break

            if enclosing_loop_idx is None:
                continue

            loop_line   = current_lines[enclosing_loop_idx]
            loop_indent = loop_line[:len(loop_line) - len(loop_line.lstrip())]
            hoisted     = loop_indent + orig_stripped + '\n'

            # Rebuild lines: remove from found_idx, insert before enclosing loop
            new_lines = (
                current_lines[:enclosing_loop_idx]
                + [hoisted]
                + current_lines[enclosing_loop_idx:found_idx]
                + current_lines[found_idx + 1:]
            )
            code = ''.join(new_lines)

            label = {
                "loop_invariant_strlen":      "strlen() call",
                "redundant_constant_in_loop": "constant declaration",
                "loop_invariant_sizeof":      "sizeof() expression",
            }.get(ftype, "loop-invariant statement")
            transforms.append({
                "type":        "hoist_loop_invariant",
                "description": f"Hoisted {label} '{orig_stripped}' before enclosing loop.",
                "severity":    "info",
            })

        return code, transforms

    def _apply_strength_reduction(self, src: str) -> Tuple[str, List[Dict]]:
        """Replace multiply/divide by constant powers of 2 with bit-shifts."""
        transforms: List[Dict] = []
        code = src
        # x * 2 → x << 1,  x * 4 → x << 2,  x * 8 → x << 3
        # x / 2 → x >> 1,  x / 4 → x >> 2,  x / 8 → x >> 3
        # Only applies to simple variable operands (not complex expressions)
        replacements = [
            (re.compile(r'\b(\w+)\s*\*\s*2\b'),  r'\1 << 1',  "x*2 → x<<1"),
            (re.compile(r'\b(\w+)\s*\*\s*4\b'),  r'\1 << 2',  "x*4 → x<<2"),
            (re.compile(r'\b(\w+)\s*\*\s*8\b'),  r'\1 << 3',  "x*8 → x<<3"),
            (re.compile(r'\b(\w+)\s*\*\s*16\b'), r'\1 << 4',  "x*16 → x<<4"),
            (re.compile(r'\b(\w+)\s*/\s*2\b'),   r'\1 >> 1',  "x/2 → x>>1"),
            (re.compile(r'\b(\w+)\s*/\s*4\b'),   r'\1 >> 2',  "x/4 → x>>2"),
            (re.compile(r'\b(\w+)\s*/\s*8\b'),   r'\1 >> 3',  "x/8 → x>>3"),
        ]
        # Strip comments before scanning to avoid false positives
        _no_comments = re.sub(r'//[^\n]*', '', code)
        _no_comments = re.sub(r'/\*.*?\*/', '', _no_comments, flags=re.DOTALL)
        for pattern, replacement, label in replacements:
            if pattern.search(_no_comments):
                new_code, n = pattern.subn(replacement, code)
                if n > 0:
                    code = new_code
                    _no_comments = re.sub(r'//[^\n]*', '', code)
                    _no_comments = re.sub(r'/\*.*?\*/', '', _no_comments, flags=re.DOTALL)
                    transforms.append({
                        "type":        "strength_reduction",
                        "description": f"Strength reduction: replaced {label} with bit-shift ({n} occurrence(s)).",
                        "severity":    "info",
                    })
        return code, transforms

    def _fix_postincrement_in_loops(self, src: str) -> Tuple[str, bool]:
        """Change i++ → ++i in for-loop increment clause only."""
        # Matches the third clause of a for-loop: for(...;...;  VAR++  )
        pattern = re.compile(
            r'(for\s*\([^;]*;[^;]*;\s*)(\w+)\+\+(\s*\))',
            re.MULTILINE,
        )
        # Strip the captured whitespace before ')' — produce clean `++i)`
        new_src, n = pattern.subn(lambda m: m.group(1) + "++" + m.group(2) + ")", src)
        return new_src, n > 0

    def _extract_varname(self, description: str) -> Optional[str]:
        m = re.search(r"Variable '(\w+)'", description)
        return m.group(1) if m else None

    # ── LLM optimization ──────────────────────────────────────────────────────

    def _llm_optimize(
        self, src: str, analysis_report: Dict
    ) -> Tuple[Optional[str], List[Dict], List[str], str, float]:
        _fallback = (None, [], ["Rule-based optimization only."], "Applied rule-based fixes.", 0.85)

        if not self.llm.is_available():
            logger.info("OptimizationAgent: LLM not available — skipping LLM transforms")
            return _fallback

        prompt = OptimizationPromptTemplate.build(src, analysis_report)
        raw    = self.llm.generate(
            prompt, system_prompt=OptimizationPromptTemplate.SYSTEM
        )

        if "offline stub" in raw or "LLM offline stub" in raw:
            logger.warning("OptimizationAgent: LLM returned stub — skipping LLM transforms")
            return _fallback

        cot = self.cot_val.validate(raw)
        if cot.is_valid and cot.optimized_code:
            return (
                cot.optimized_code,
                cot.findings,
                cot.reasoning_steps,
                cot.conclusion,
                cot.confidence,
            )
        logger.warning(f"LLM optimization CoT invalid or no code: {cot.error}")
        return _fallback

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _make_diff(self, original: str, optimized: str, file_path: str) -> str:
        orig_lines = original.splitlines(keepends=True)
        opt_lines  = optimized.splitlines(keepends=True)
        diff       = difflib.unified_diff(
            orig_lines, opt_lines,
            fromfile=f"original/{os.path.basename(file_path)}",
            tofile=f"optimized/{os.path.basename(file_path)}",
            lineterm="",
        )
        return "".join(diff)

    def _save_output(self, code: str, file_path: str) -> str:
        base     = os.path.basename(file_path) if file_path != "<unknown>" else "output.cpp"
        out_name = "OPT_" + base
        out_path = os.path.join(self.output_dir, out_name)
        try:
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(code)
            logger.info(f"Saved optimized code to {out_path}")
        except OSError as exc:
            logger.error(f"Could not save optimized file: {exc}")
        return out_path

    def _build_summary(
        self, file_path, transforms, conclusion, diff
    ) -> str:
        diff_lines = diff.count("\n+") + diff.count("\n-")
        lines = [
            f"Optimization Report: {file_path}",
            f"Transformations    : {len(transforms)}",
            f"Diff lines changed : ~{diff_lines}",
            f"Conclusion         : {conclusion}",
        ]
        for i, t in enumerate(transforms, 1):
            lines.append(f"  {i}. {t.get('type')}: {t.get('description')}")
        return "\n".join(lines)
