"""
SecurityScanner — standalone rule-based security vulnerability detector.

Runs on a single source string (no original/optimized comparison).
Designed for on-demand scans triggered from the frontend Scan Security button.

Returns a list of findings, each with line/col range so the Monaco editor
can render squiggly underlines and gutter icons.

Suppression: a line immediately preceding a finding that matches
  // SECURITY-IGNORE: <type>
will cause that finding to be omitted.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# ── helpers ────────────────────────────────────────────────────────────────

def _line_col(code: str, match_start: int) -> Tuple[int, int]:
    """Return 1-indexed (line, col) for a character offset in code."""
    before = code[:match_start]
    line   = before.count("\n") + 1
    col    = match_start - before.rfind("\n")
    return line, col


def _match_end_col(code: str, match_end: int) -> int:
    last_nl = code.rfind("\n", 0, match_end)
    return match_end - last_nl


def _strip_comments(code: str) -> str:
    code = re.sub(r'//[^\n]*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    return code


# ── main scanner ───────────────────────────────────────────────────────────

class SecurityScanner:
    """
    Pure rule-based security scanner.  No LLM, no compilation — runs in < 100 ms.

    Usage
    -----
    scanner  = SecurityScanner()
    findings = scanner.scan(source_code)
    """

    # ── R01: gets() ───────────────────────────────────────────────────────
    _RE_GETS = re.compile(r'\bgets\s*\(', re.MULTILINE)

    # ── R02: scanf with unbounded %s ──────────────────────────────────────
    _RE_SCANF_S = re.compile(r'\bscanf\s*\(\s*"[^"]*%s', re.MULTILINE)

    # ── R03: strcpy ───────────────────────────────────────────────────────
    _RE_STRCPY = re.compile(r'\bstrcpy\s*\(', re.MULTILINE)

    # ── R04: strcat ───────────────────────────────────────────────────────
    _RE_STRCAT = re.compile(r'\bstrcat\s*\(', re.MULTILINE)

    # ── R05: sprintf ─────────────────────────────────────────────────────
    _RE_SPRINTF = re.compile(r'\bsprintf\s*\(', re.MULTILINE)

    # ── R06: format string — printf/vprintf(var) where first arg is the format string.
    # sprintf/snprintf/fprintf are excluded: their first arg is a destination buffer
    # or FILE*, not the format string, so they are covered by other rules.
    _RE_FMT_STR = re.compile(
        r'\b(?:printf|vprintf)\s*\(\s*(\w+)\s*[,)]',
        re.MULTILINE,
    )

    # ── R08: double free ─────────────────────────────────────────────────
    # (detected in _scan_double_free)

    # ── R09: unchecked malloc ────────────────────────────────────────────
    _RE_MALLOC = re.compile(r'\b(\w+)\s*=\s*(?:\([^)]*\)\s*)?(?:malloc|calloc|realloc)\s*\(', re.MULTILINE)
    _RE_NULL_CHECK = re.compile(r'if\s*\(\s*!?\s*(\w+)\s*(?:==\s*NULL|!=\s*NULL)?\s*\)', re.MULTILINE)

    # ── R11: hardcoded secrets ───────────────────────────────────────────
    # Matches variable names that contain or equal the keyword (e.g. adminPass,
    # AUTH_TOKEN, password[], myApiKey) — \w* prefix/suffix + optional array []
    _RE_SECRET = re.compile(
        r'\b\w*(?:password|passwd|pass|secret|api_key|apikey|token|auth_key|authkey'
        r'|access_key|private_key|credentials?|passphrase)\w*'
        r'(?:\s*\[\s*\d*\s*\])?\s*=\s*"([^"]{4,})"',
        re.IGNORECASE | re.MULTILINE,
    )
    # Also catch #define macros whose name contains a keyword (e.g. SECRET_KEY, MY_TOKEN)
    _RE_SECRET_DEFINE = re.compile(
        r'#define\s+\w*(?:PASSWORD|PASSWD|SECRET|API_KEY|TOKEN|AUTH|PASS)\w*\s+"([^"]{3,})"',
        re.IGNORECASE | re.MULTILINE,
    )

    # ── R12: command injection ───────────────────────────────────────────
    _RE_SYSTEM = re.compile(r'\b(?:system|popen)\s*\(\s*(\w+)', re.MULTILINE)

    # ── R13: TOCTOU ──────────────────────────────────────────────────────
    _RE_ACCESS = re.compile(r'\baccess\s*\(\s*(\w+)', re.MULTILINE)
    _RE_OPEN   = re.compile(r'\b(?:open|fopen)\s*\(\s*(\w+)', re.MULTILINE)

    # ── R14: integer overflow in malloc argument ──────────────────────────
    _RE_MALLOC_MUL = re.compile(r'\bmalloc\s*\(\s*(\w+)\s*\*\s*(\w+)\s*\)', re.MULTILINE)

    # ── R15: unsafe memcpy ───────────────────────────────────────────────
    _RE_MEMCPY = re.compile(r'\bmemcpy\s*\(', re.MULTILINE)

    # ── R16: insecure rand near security context ──────────────────────────
    _RE_RAND = re.compile(r'\brand\s*\(\s*\)', re.MULTILINE)
    _SECURITY_WORDS = re.compile(r'\b(?:password|token|key|secret|session|nonce|salt|iv)\b', re.IGNORECASE)

    # ── R17: atoi/atof on external input ─────────────────────────────────
    _RE_ATOI = re.compile(r'\b(?:atoi|atof|atol|atoll)\s*\(\s*(\w+)', re.MULTILINE)
    _EXTERNAL_SOURCES = {'argv', 'input', 'buf', 'buffer', 'line', 'str', 'data', 'cmd', 'arg'}

    # ── R18: signed int used as array index ──────────────────────────────
    # (detected in _scan_signed_index)

    # ── R19: stack buffer with unsafe write ──────────────────────────────
    _RE_STACK_BUF = re.compile(r'\bchar\s+(\w+)\s*\[(\d+)\]', re.MULTILINE)

    # ── suppression pattern ───────────────────────────────────────────────
    _RE_SUPPRESS = re.compile(r'//\s*SECURITY-IGNORE:\s*(\S+)')

    def scan(self, code: str) -> List[Dict[str, Any]]:
        """
        Scan source code for security vulnerabilities.
        Returns list of findings sorted by line number.
        """
        if not code or not code.strip():
            return []

        lines = code.splitlines()

        # Build suppression map: line_number -> set of suppressed types
        suppressed: Dict[int, set] = {}
        for i, line in enumerate(lines, 1):
            m = self._RE_SUPPRESS.search(line)
            if m:
                suppressed[i + 1] = suppressed.get(i + 1, set())
                suppressed[i + 1].add(m.group(1))

        findings: List[Dict] = []

        findings.extend(self._scan_pattern(code, self._RE_GETS, "unsafe_gets", "high",
            "CWE-242", "gets() performs no bound checking on input length — unconditionally unsafe.",
            "Replace with fgets(buf, sizeof(buf), stdin)."))

        findings.extend(self._scan_pattern(code, self._RE_SCANF_S, "unsafe_scanf_s", "high",
            "CWE-134", "scanf %s reads an unbounded string — destination buffer may overflow.",
            "Add field width: scanf(\"%127s\", buf)."))

        findings.extend(self._scan_pattern(code, self._RE_STRCPY, "unsafe_strcpy", "medium",
            "CWE-676", "strcpy() copies without bound checking — destination may overflow.",
            "Replace with strncpy(dst, src, sizeof(dst)-1); dst[sizeof(dst)-1]='\\0';"))

        findings.extend(self._scan_pattern(code, self._RE_STRCAT, "unsafe_strcat", "medium",
            "CWE-676", "strcat() appends without bound checking — destination may overflow.",
            "Replace with strncat(dst, src, sizeof(dst)-strlen(dst)-1)."))

        findings.extend(self._scan_pattern(code, self._RE_SPRINTF, "unsafe_sprintf", "medium",
            "CWE-676", "sprintf() writes unbounded output — use snprintf() with explicit size.",
            "Replace with snprintf(buf, sizeof(buf), fmt, ...)."))

        findings.extend(self._scan_format_string(code))
        findings.extend(self._scan_use_after_free(code, lines))
        findings.extend(self._scan_double_free(code, lines))
        findings.extend(self._scan_unchecked_malloc(code))
        findings.extend(self._scan_secrets(code))
        findings.extend(self._scan_command_injection(code, lines))
        findings.extend(self._scan_toctou(code, lines))
        findings.extend(self._scan_malloc_overflow(code))
        findings.extend(self._scan_memcpy(code))
        findings.extend(self._scan_insecure_rand(code))
        findings.extend(self._scan_atoi_external(code))
        findings.extend(self._scan_signed_index(code))
        findings.extend(self._scan_stack_buf_overflow(code, lines))

        # Apply suppression
        filtered = []
        for f in findings:
            ln = f.get("line", 0)
            sup = suppressed.get(ln, set())
            if f["type"] not in sup:
                filtered.append(f)

        # Deduplicate on (type, line)
        seen = set()
        deduped = []
        for f in filtered:
            key = (f["type"], f.get("line"))
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        deduped.sort(key=lambda f: f.get("line") or 0)
        logger.info(f"SecurityScanner: {len(deduped)} finding(s)")
        return deduped

    # ── Generic pattern scanner ────────────────────────────────────────────

    def _scan_pattern(self, code, pattern, vtype, severity, cwe, desc, fix) -> List[Dict]:
        findings = []
        for m in pattern.finditer(code):
            line, col = _line_col(code, m.start())
            end_col   = _match_end_col(code, m.end())
            findings.append({
                "type":           vtype,
                "severity":       severity,
                "line":           line,
                "col_start":      col,
                "col_end":        end_col,
                "description":    desc,
                "cwe_id":         cwe,
                "recommendation": fix,
                "fixable":        True,
                "source":         "rule",
            })
        return findings

    # ── R06: format string bug ────────────────────────────────────────────

    def _scan_format_string(self, code: str) -> List[Dict]:
        findings = []
        for m in self._RE_FMT_STR.finditer(code):
            arg = m.group(1)
            if arg.startswith('"'):
                continue
            line, col = _line_col(code, m.start())
            end_col   = _match_end_col(code, m.end())
            findings.append({
                "type":           "format_string_bug",
                "severity":       "high",
                "line":           line,
                "col_start":      col,
                "col_end":        end_col,
                "description":    (
                    f"printf() called with variable '{arg}' as format string "
                    "— potential format string attack (CWE-134)."
                ),
                "cwe_id":         "CWE-134",
                "recommendation": f'Always use a literal format: printf("%s", {arg}).',
                "fixable":        True,
                "source":         "rule",
            })
        return findings

    # ── R07: use-after-free ───────────────────────────────────────────────

    def _scan_use_after_free(self, code: str, lines: List[str]) -> List[Dict]:
        findings = []
        dealloc_re = re.compile(
            r'\bfree\s*\(\s*(\w+)\s*\)'
            r'|\bdelete\s*\[\s*\]\s*(\w+)'
            r'|\bdelete\s+(\w+)',
        )
        freed: Dict[str, int] = {}
        for m in dealloc_re.finditer(code):
            var = m.group(1) or m.group(2) or m.group(3)
            freed[var] = code[: m.start()].count("\n") + 1

        for var, free_line in freed.items():
            deref_re = re.compile(
                rf'\*\s*{re.escape(var)}\b'
                rf'|{re.escape(var)}\s*->\s*\w+'
                rf'|{re.escape(var)}\s*\['
            )
            direct_assign = re.compile(rf'(?<![*\[])\b{re.escape(var)}\s*=\s*(?!=)')
            for ln_no, line in enumerate(lines, 1):
                if ln_no <= free_line:
                    continue
                if re.search(rf'\bfree\s*\(\s*{re.escape(var)}\s*\)'
                             rf'|\bdelete(?:\s*\[\s*\])?\s+{re.escape(var)}', line):
                    break
                if direct_assign.search(line) and '->' not in line and \
                        not re.search(rf'\*\s*{re.escape(var)}', line):
                    break
                if deref_re.search(line):
                    col = (line.index(var) + 1) if var in line else 1
                    findings.append({
                        "type":           "use_after_free",
                        "severity":       "high",
                        "line":           ln_no,
                        "col_start":      col,
                        "col_end":        col + len(var),
                        "description":    (
                            f"Variable '{var}' dereferenced at line {ln_no} "
                            f"after being freed at line {free_line}."
                        ),
                        "cwe_id":         "CWE-416",
                        "recommendation": f"Set '{var} = NULL;' immediately after free, and NULL-check before use.",
                        "fixable":        True,
                        "source":         "rule",
                    })
                    break
        return findings

    # ── R08: double free ─────────────────────────────────────────────────

    def _scan_double_free(self, code: str, lines: List[str]) -> List[Dict]:
        findings = []
        free_re = re.compile(r'\bfree\s*\(\s*(\w+)\s*\)')
        var_frees: Dict[str, List[int]] = {}
        for m in free_re.finditer(code):
            var = m.group(1)
            ln  = code[: m.start()].count("\n") + 1
            var_frees.setdefault(var, []).append(ln)

        reassign_re_cache: Dict[str, re.Pattern] = {}
        for var, free_lines in var_frees.items():
            if len(free_lines) < 2:
                continue
            if var not in reassign_re_cache:
                reassign_re_cache[var] = re.compile(
                    rf'(?<![*\[])\b{re.escape(var)}\s*=\s*(?!=)'
                )
            ra_re = reassign_re_cache[var]
            for i in range(1, len(free_lines)):
                first_free = free_lines[i - 1]
                second_free = free_lines[i]
                # Check if var was reassigned between the two frees
                between = "\n".join(lines[first_free: second_free - 1])
                if ra_re.search(between):
                    continue  # reassigned — not a double-free
                col = (lines[second_free - 1].index(var) + 1) if var in lines[second_free - 1] else 1
                findings.append({
                    "type":           "double_free",
                    "severity":       "high",
                    "line":           second_free,
                    "col_start":      col,
                    "col_end":        col + len(var) + 6,
                    "description":    (
                        f"Variable '{var}' freed at line {second_free} "
                        f"was already freed at line {first_free} without reassignment."
                    ),
                    "cwe_id":         "CWE-415",
                    "recommendation": f"Set '{var} = NULL;' after the first free() to prevent double-free.",
                    "fixable":        True,
                    "source":         "rule",
                })
        return findings

    # ── R09: unchecked malloc ─────────────────────────────────────────────

    def _scan_unchecked_malloc(self, code: str) -> List[Dict]:
        findings = []
        for m in self._RE_MALLOC.finditer(code):
            var  = m.group(1)
            line, col = _line_col(code, m.start())
            # Look in the next 5 lines for a NULL check on this var
            after_lines = code[m.end():].splitlines()[:5]
            after_text  = "\n".join(after_lines)
            null_check  = re.search(
                rf'if\s*\(\s*!?\s*{re.escape(var)}\s*(?:==\s*NULL|!=\s*NULL)?\s*\)'
                rf'|assert\s*\(\s*{re.escape(var)}\s*\)',
                after_text,
            )
            if not null_check:
                findings.append({
                    "type":           "unchecked_malloc",
                    "severity":       "medium",
                    "line":           line,
                    "col_start":      col,
                    "col_end":        col + 6,
                    "description":    (
                        f"Return value of malloc/calloc/realloc assigned to '{var}' "
                        "is not checked for NULL — NULL dereference on allocation failure."
                    ),
                    "cwe_id":         "CWE-476",
                    "recommendation": f"Add: if (!{var}) {{ /* handle error */ return -1; }}",
                    "fixable":        True,
                    "source":         "rule",
                })
        return findings

    # ── R11: hardcoded secrets ────────────────────────────────────────────

    def _scan_secrets(self, code: str) -> List[Dict]:
        findings = []
        for pattern in (self._RE_SECRET, self._RE_SECRET_DEFINE):
            for m in pattern.finditer(code):
                line, col = _line_col(code, m.start())
                findings.append({
                    "type":           "hardcoded_secret",
                    "severity":       "high",
                    "line":           line,
                    "col_start":      col,
                    "col_end":        col + len(m.group(0)),
                    "description":    (
                        "Hardcoded credential/secret detected in source code. "
                        "Secrets committed to source control are a critical security risk (CWE-798)."
                    ),
                    "cwe_id":         "CWE-798",
                    "recommendation": "Load from environment variable: getenv(\"SECRET_NAME\").",
                    "fixable":        True,
                    "source":         "rule",
                })
        return findings

    # ── R12: command injection ────────────────────────────────────────────

    def _scan_command_injection(self, code: str, lines: List[str]) -> List[Dict]:
        findings = []
        for m in self._RE_SYSTEM.finditer(code):
            arg = m.group(1)
            # Skip if arg is a string literal (already caught by format string check)
            col_in_code = m.start()
            line_text   = lines[code[:col_in_code].count("\n")]
            if '"' in line_text.split("(")[0]:
                continue
            line, col = _line_col(code, col_in_code)
            fn_name = m.group(0).split("(")[0].strip()
            findings.append({
                "type":           "command_injection",
                "severity":       "high",
                "line":           line,
                "col_start":      col,
                "col_end":        col + len(fn_name),
                "description":    (
                    f"{fn_name}() called with variable argument '{arg}' "
                    "— attacker-controlled input could execute arbitrary commands (CWE-78)."
                ),
                "cwe_id":         "CWE-78",
                "recommendation": "Validate and sanitize input before passing to system(). Prefer execvp() with an explicit argument array.",
                "fixable":        False,
                "source":         "rule",
            })
        return findings

    # ── R13: TOCTOU ──────────────────────────────────────────────────────

    def _scan_toctou(self, code: str, lines: List[str]) -> List[Dict]:
        findings = []
        access_hits: Dict[str, int] = {}
        for m in self._RE_ACCESS.finditer(code):
            var = m.group(1)
            ln  = code[:m.start()].count("\n") + 1
            access_hits[var] = ln

        for m in self._RE_OPEN.finditer(code):
            var = m.group(1)
            ln  = code[:m.start()].count("\n") + 1
            if var in access_hits:
                access_ln = access_hits[var]
                if 0 < ln - access_ln <= 10:
                    line, col = _line_col(code, m.start())
                    findings.append({
                        "type":           "toctou_race",
                        "severity":       "medium",
                        "line":           line,
                        "col_start":      col,
                        "col_end":        col + 6,
                        "description":    (
                            f"TOCTOU race: access() on '{var}' at line {access_ln} "
                            f"then open()/fopen() at line {ln} — another process could modify the file between checks."
                        ),
                        "cwe_id":         "CWE-367",
                        "recommendation": "Use open() with O_CREAT|O_EXCL instead of access()+open() to atomically check and open.",
                        "fixable":        False,
                        "source":         "rule",
                    })
        return findings

    # ── R14: integer overflow in malloc ───────────────────────────────────

    def _scan_malloc_overflow(self, code: str) -> List[Dict]:
        findings = []
        for m in self._RE_MALLOC_MUL.finditer(code):
            preceding = code[: m.start()][-500:]
            has_guard = bool(re.search(
                r'if\s*\([^)]*>\s*(?:SIZE_MAX|INT_MAX|UINT_MAX)', preceding
            ))
            if has_guard:
                continue
            line, col = _line_col(code, m.start())
            a, b = m.group(1), m.group(2)
            findings.append({
                "type":           "integer_overflow_malloc",
                "severity":       "high",
                "line":           line,
                "col_start":      col,
                "col_end":        col + len(m.group(0)),
                "description":    (
                    f"malloc({a} * {b}): multiplication may overflow before allocation "
                    "producing a smaller-than-expected buffer (CWE-190)."
                ),
                "cwe_id":         "CWE-190",
                "recommendation": f"Guard with: if ({b} && {a} > SIZE_MAX / {b}) {{ /* error */ }} before malloc.",
                "fixable":        True,
                "source":         "rule",
            })
        return findings

    # ── R15: unsafe memcpy ────────────────────────────────────────────────

    def _scan_memcpy(self, code: str) -> List[Dict]:
        findings = []
        memcpy_full = re.compile(
            r'\bmemcpy\s*\(\s*(\w+)\s*,\s*(\w+)\s*,\s*([^)]+)\)',
            re.MULTILINE,
        )
        for m in memcpy_full.finditer(code):
            dst, src, size_expr = m.group(1), m.group(2), m.group(3).strip()
            # Only flag if size is not sizeof(dst)
            if f'sizeof({dst})' in size_expr or f'sizeof {dst}' in size_expr:
                continue
            line, col = _line_col(code, m.start())
            findings.append({
                "type":           "unsafe_memcpy",
                "severity":       "medium",
                "line":           line,
                "col_start":      col,
                "col_end":        col + 6,
                "description":    (
                    f"memcpy('{dst}', '{src}', {size_expr}): size is not sizeof({dst}) "
                    "— destination may overflow if src is larger than dst."
                ),
                "cwe_id":         "CWE-120",
                "recommendation": f"Use sizeof({dst}) as the size argument: memcpy({dst}, {src}, sizeof({dst})).",
                "fixable":        True,
                "source":         "rule",
            })
        return findings

    # ── R16: insecure rand ────────────────────────────────────────────────

    def _scan_insecure_rand(self, code: str) -> List[Dict]:
        findings = []
        for m in self._RE_RAND.finditer(code):
            # Check if nearby context suggests security use
            start  = max(0, m.start() - 200)
            end    = min(len(code), m.end() + 200)
            ctx    = code[start:end]
            if self._SECURITY_WORDS.search(ctx):
                line, col = _line_col(code, m.start())
                findings.append({
                    "type":           "insecure_rand",
                    "severity":       "low",
                    "line":           line,
                    "col_start":      col,
                    "col_end":        col + 6,
                    "description":    (
                        "rand() is not cryptographically secure. "
                        "Its output is predictable and must not be used for security-sensitive values (CWE-338)."
                    ),
                    "cwe_id":         "CWE-338",
                    "recommendation": "Use /dev/urandom (via getrandom()) or a CSPRNG library for security-sensitive randomness.",
                    "fixable":        False,
                    "source":         "rule",
                })
        return findings

    # ── R17: atoi on external input ───────────────────────────────────────

    def _scan_atoi_external(self, code: str) -> List[Dict]:
        findings = []
        for m in self._RE_ATOI.finditer(code):
            arg = m.group(1)
            if arg in self._EXTERNAL_SOURCES or 'argv' in arg.lower():
                line, col = _line_col(code, m.start())
                fn = m.group(0).split("(")[0].strip()
                findings.append({
                    "type":           "atoi_no_validate",
                    "severity":       "low",
                    "line":           line,
                    "col_start":      col,
                    "col_end":        col + len(fn),
                    "description":    (
                        f"{fn}() converts external input '{arg}' to integer "
                        "without range or format validation — invalid input causes undefined behaviour (CWE-20)."
                    ),
                    "cwe_id":         "CWE-20",
                    "recommendation": f"Use strtol() with errno check and range validation instead of {fn}().",
                    "fixable":        False,
                    "source":         "rule",
                })
        return findings

    # ── R18: signed int used as array index ───────────────────────────────

    def _scan_signed_index(self, code: str) -> List[Dict]:
        findings = []
        nc = _strip_comments(code)
        int_vars = set(re.findall(r'\bint\s+(\w+)\s*[=;,\)]', nc))
        arr_idx  = re.compile(r'\b(\w+)\s*\[\s*(' + '|'.join(re.escape(v) for v in int_vars) + r')\s*\]')
        if not int_vars:
            return findings
        for m in arr_idx.finditer(nc):
            arr, idx = m.group(1), m.group(2)
            line, col = _line_col(code, m.start())
            findings.append({
                "type":           "signed_index",
                "severity":       "medium",
                "line":           line,
                "col_start":      col,
                "col_end":        col + len(m.group(0)),
                "description":    (
                    f"Signed int '{idx}' used as index into '{arr}' "
                    "— a negative value wraps to a large unsigned offset, causing out-of-bounds access (CWE-195)."
                ),
                "cwe_id":         "CWE-195",
                "recommendation": f"Use size_t or unsigned int for array indices. Add: if ({idx} < 0) check.",
                "fixable":        False,
                "source":         "rule",
            })
        return findings

    # ── R19: small stack buffer with unsafe write ─────────────────────────

    def _scan_stack_buf_overflow(self, code: str, lines: List[str]) -> List[Dict]:
        findings = []
        unsafe_writes = re.compile(
            r'\b(?:strcpy|scanf|gets|sprintf|strcat)\s*\(\s*(\w+)',
            re.MULTILINE,
        )
        small_bufs: Dict[str, Tuple[int, int]] = {}
        for m in self._RE_STACK_BUF.finditer(code):
            name = m.group(1)
            size = int(m.group(2))
            if size <= 256:
                ln = code[:m.start()].count("\n") + 1
                small_bufs[name] = (size, ln)

        for m in unsafe_writes.finditer(code):
            target = m.group(1)
            if target in small_bufs:
                size, decl_line = small_bufs[target]
                line, col = _line_col(code, m.start())
                fn = m.group(0).split("(")[0].strip()
                findings.append({
                    "type":           "stack_buf_overflow",
                    "severity":       "high",
                    "line":           line,
                    "col_start":      col,
                    "col_end":        col + len(fn),
                    "description":    (
                        f"{fn}() writes into stack buffer '{target}[{size}]' (declared at line {decl_line}) "
                        "without a size check — potential stack-based buffer overflow (CWE-121)."
                    ),
                    "cwe_id":         "CWE-121",
                    "recommendation": f"Use the size-bounded equivalent and validate input length <= {size - 1}.",
                    "fixable":        False,
                    "source":         "rule",
                })
        return findings
