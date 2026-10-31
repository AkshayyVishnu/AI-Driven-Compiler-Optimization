"""
SecurityFixer — applies rule-based fixes for detected security vulnerabilities.

Processes findings in reverse line order (bottom-to-top) so that earlier
fixes do not shift line numbers for later ones.

Returns (fixed_code, fixes_applied, unified_diff).
"""

import difflib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SecurityFixer:
    """
    Applies deterministic rule-based fixes to C/C++ source code.

    Usage
    -----
    fixer = SecurityFixer()
    fixed_code, fixes_applied, diff = fixer.apply_all_fixes(code, findings)
    """

    def apply_all_fixes(
        self,
        source_code: str,
        findings: List[Dict[str, Any]],
    ) -> Tuple[str, List[Dict], str]:
        """
        Apply all fixable findings to source_code.

        Returns
        -------
        (fixed_code, fixes_applied, unified_diff)
        """
        fixable = [f for f in findings if f.get("fixable", False)]
        if not fixable:
            return source_code, [], ""

        # Sort by descending line so we process bottom-to-top
        fixable_sorted = sorted(fixable, key=lambda f: f.get("line") or 0, reverse=True)

        code         = source_code
        fixes_applied: List[Dict] = []

        for finding in fixable_sorted:
            vtype = finding.get("type", "")
            line  = finding.get("line", 0)

            handler = self._HANDLERS.get(vtype)
            if not handler:
                continue

            new_code, description = handler(self, code, finding)
            if new_code != code and description:
                code = new_code
                fixes_applied.append({
                    "type":        vtype,
                    "line":        line,
                    "description": description,
                })
                logger.debug(f"SecurityFixer: fixed {vtype} at line {line}")

        diff = self._make_diff(source_code, code)
        logger.info(f"SecurityFixer: {len(fixes_applied)} fix(es) applied")
        return code, fixes_applied, diff

    # ── Individual fix handlers ────────────────────────────────────────────
    # Each handler: (self, code, finding) -> (new_code, description_or_None)

    def _fix_gets(self, code: str, finding: Dict) -> Tuple[str, Optional[str]]:
        """gets(buf) -> fgets(buf, sizeof(buf), stdin)"""
        pattern = re.compile(r'\bgets\s*\(\s*(\w+)\s*\)')
        def replacer(m):
            buf = m.group(1)
            return f'fgets({buf}, sizeof({buf}), stdin)'
        new_code, n = pattern.subn(replacer, code)
        if n:
            return new_code, f"Replaced gets() with fgets(buf, sizeof(buf), stdin) ({n} occurrence(s))."
        return code, None

    def _fix_scanf_s(self, code: str, finding: Dict) -> Tuple[str, Optional[str]]:
        """scanf("%s", ...) -> scanf("%127s", ...) — adds width limit."""
        pattern = re.compile(r'(scanf\s*\(\s*"[^"]*)(%s)([^"]*")')
        new_code, n = pattern.subn(r'\g<1>%127s\g<3>', code)
        if n:
            return new_code, f"Added field-width limit to scanf %s -> %127s ({n} occurrence(s))."
        return code, None

    def _fix_strcpy(self, code: str, finding: Dict) -> Tuple[str, Optional[str]]:
        """strcpy(dst, src) -> strncpy(dst, src, sizeof(dst)-1); dst[sizeof(dst)-1]='\\0';"""
        pattern = re.compile(r'\bstrcpy\s*\(\s*(\w+)\s*,\s*([^)]+)\)\s*;')
        def replacer(m):
            dst = m.group(1)
            src = m.group(2).strip()
            return (
                f'strncpy({dst}, {src}, sizeof({dst})-1);\n'
                f'    {dst}[sizeof({dst})-1] = \'\\0\'; /* fix: strcpy -> strncpy */'
            )
        new_code, n = pattern.subn(replacer, code)
        if n:
            return new_code, f"Replaced strcpy() with strncpy() + null-termination ({n} occurrence(s))."
        return code, None

    def _fix_strcat(self, code: str, finding: Dict) -> Tuple[str, Optional[str]]:
        """strcat(dst, src) -> strncat(dst, src, sizeof(dst)-strlen(dst)-1)"""
        pattern = re.compile(r'\bstrcat\s*\(\s*(\w+)\s*,\s*([^)]+)\)\s*;')
        def replacer(m):
            dst = m.group(1)
            src = m.group(2).strip()
            return f'strncat({dst}, {src}, sizeof({dst})-strlen({dst})-1); /* fix: strcat -> strncat */'
        new_code, n = pattern.subn(replacer, code)
        if n:
            return new_code, f"Replaced strcat() with strncat() with size guard ({n} occurrence(s))."
        return code, None

    def _fix_sprintf(self, code: str, finding: Dict) -> Tuple[str, Optional[str]]:
        """sprintf(buf, fmt, ...) -> snprintf(buf, sizeof(buf), fmt, ...)"""
        pattern = re.compile(r'\bsprintf\s*\(\s*(\w+)\s*,')
        def replacer(m):
            buf = m.group(1)
            return f'snprintf({buf}, sizeof({buf}),'
        new_code, n = pattern.subn(replacer, code)
        if n:
            return new_code, f"Replaced sprintf() with snprintf() with size limit ({n} occurrence(s))."
        return code, None

    def _fix_format_string(self, code: str, finding: Dict) -> Tuple[str, Optional[str]]:
        """printf(var) -> printf("%s", var)
        Only handles printf — sprintf/snprintf have a destination buffer as first arg
        so they are handled by _fix_sprintf, not here.
        """
        pattern = re.compile(r'\bprintf\s*\(\s*(\w+)\s*([,)])')
        changed = False
        def replacer(m):
            nonlocal changed
            arg  = m.group(1)
            rest = m.group(2)
            if arg.startswith('"'):
                return m.group(0)
            changed = True
            sep = ', ' if rest == ',' else ''
            return f'printf("%s", {arg}{sep}'
        new_code = pattern.sub(replacer, code)
        if changed:
            return new_code, "Added literal format string to printf() call."
        return code, None

    def _fix_use_after_free(self, code: str, finding: Dict) -> Tuple[str, Optional[str]]:
        """Insert `ptr = NULL;` after free(ptr)"""
        # Extract variable name from description
        m = re.search(r"Variable '(\w+)'", finding.get("description", ""))
        if not m:
            return code, None
        var = m.group(1)
        pattern = re.compile(rf'(\bfree\s*\(\s*{re.escape(var)}\s*\)\s*;)')
        def replacer(match):
            return match.group(1) + f'\n    {var} = NULL; /* fix: prevent use-after-free */'
        new_code, n = pattern.subn(replacer, code)
        if n:
            return new_code, f"Added '{var} = NULL;' after free() to prevent use-after-free."
        return code, None

    def _fix_double_free(self, code: str, finding: Dict) -> Tuple[str, Optional[str]]:
        """Insert `ptr = NULL;` after first free(ptr)"""
        m = re.search(r"Variable '(\w+)'", finding.get("description", ""))
        if not m:
            return code, None
        var = m.group(1)
        pattern = re.compile(rf'(\bfree\s*\(\s*{re.escape(var)}\s*\)\s*;)')
        count = [0]
        def replacer(match):
            count[0] += 1
            if count[0] == 1:
                return match.group(1) + f'\n    {var} = NULL; /* fix: prevent double-free */'
            return match.group(1)
        new_code = pattern.sub(replacer, code)
        if count[0] > 0 and new_code != code:
            return new_code, f"Added '{var} = NULL;' after first free() to prevent double-free."
        return code, None

    def _fix_unchecked_malloc(self, code: str, finding: Dict) -> Tuple[str, Optional[str]]:
        """Insert NULL check after malloc line."""
        m = re.search(r"assigned to '(\w+)'", finding.get("description", ""))
        if not m:
            return code, None
        var = m.group(1)
        line_no = finding.get("line", 0)
        if not line_no:
            return code, None
        lines = code.splitlines(keepends=True)
        if line_no > len(lines):
            return code, None
        # Find the malloc line
        malloc_line = lines[line_no - 1]
        indent = malloc_line[:len(malloc_line) - len(malloc_line.lstrip())]
        null_check = (
            f'{indent}if (!{var}) {{\n'
            f'{indent}    /* TODO: handle allocation failure */\n'
            f'{indent}    return -1;\n'
            f'{indent}}} /* fix: unchecked malloc */\n'
        )
        new_lines = lines[:line_no] + [null_check] + lines[line_no:]
        return ''.join(new_lines), f"Added NULL check for '{var}' after malloc()."

    def _fix_hardcoded_secret(self, code: str, finding: Dict) -> Tuple[str, Optional[str]]:
        """Replace hardcoded secret value with getenv() call."""
        pattern = re.compile(
            r'(\b(?:password|passwd|secret|api_key|apikey|token|auth_key|authkey'
            r'|access_key|private_key|credentials?)\s*=\s*)"[^"]+"',
            re.IGNORECASE,
        )
        new_code, n = pattern.subn(
            r'\1getenv("SECRET_NAME") /* fix: load from environment variable */',
            code,
        )
        # Also handle #define
        define_pattern = re.compile(
            r'(#define\s+(?:PASSWORD|PASSWD|SECRET|API_KEY|TOKEN|AUTH)\s+)"[^"]+"',
            re.IGNORECASE,
        )
        new_code, n2 = define_pattern.subn(
            r'\1"" /* fix: replace hardcoded secret — load from env */',
            new_code,
        )
        if n + n2:
            return new_code, f"Replaced hardcoded secret(s) with getenv() placeholder ({n + n2} occurrence(s))."
        return code, None

    def _fix_malloc_overflow(self, code: str, finding: Dict) -> Tuple[str, Optional[str]]:
        """Insert overflow guard before malloc(a * b)."""
        # Factor can be a plain word OR sizeof(type) — match both
        _FACTOR = r'(?:sizeof\s*\([^)]+\)|\w+)'
        m = re.search(
            r'malloc\((' + r'\w+' + r')\s*\*\s*(' + _FACTOR + r')\)',
            finding.get("description", ""),
        )
        if not m:
            dm = re.search(
                r'malloc\((' + r'\w+' + r')\s*\*\s*(' + _FACTOR + r')\)',
                code,
            )
            if not dm:
                return code, None
            a, b = dm.group(1), dm.group(2)
        else:
            a, b = m.group(1), m.group(2)

        line_no = finding.get("line", 0)
        if not line_no:
            return code, None
        lines = code.splitlines(keepends=True)
        if line_no > len(lines):
            return code, None
        malloc_line = lines[line_no - 1]
        indent = malloc_line[:len(malloc_line) - len(malloc_line.lstrip())]
        guard = (
            f'{indent}/* fix: integer overflow check before malloc */\n'
            f'{indent}if ({b} != 0 && {a} > SIZE_MAX / {b}) {{\n'
            f'{indent}    /* TODO: handle overflow error */\n'
            f'{indent}    return -1;\n'
            f'{indent}}}\n'
        )
        new_lines = [guard] + lines[line_no - 1:]
        result_lines = lines[:line_no - 1] + new_lines
        return ''.join(result_lines), f"Added overflow guard before malloc({a} * {b})."

    def _fix_memcpy(self, code: str, finding: Dict) -> Tuple[str, Optional[str]]:
        """Change memcpy size arg to sizeof(dst).

        Uses (?:[^()]|\\([^)]*\\))+ for the size argument so that expressions
        like sizeof(type) are treated as a single unit and the pattern ends at
        the correct closing ')' of the memcpy call.
        """
        m = re.search(r"memcpy\('(\w+)'.*?size is not sizeof\((\w+)\)", finding.get("description", ""))
        if not m:
            return code, None
        dst = m.group(1)
        # Size arg may contain one level of nested parens, e.g. sizeof(type)
        pattern = re.compile(
            rf'\bmemcpy\s*\(\s*{re.escape(dst)}\s*,\s*(\w+)\s*,\s*((?:[^()]|\([^)]*\))+)\)'
        )
        changed = False
        def replacer(match):
            nonlocal changed
            src  = match.group(1)
            size = match.group(2).strip()
            if size == f'sizeof({dst})':
                return match.group(0)   # already correct — do not touch
            changed = True
            return f'memcpy({dst}, {src}, sizeof({dst})) /* fix: use sizeof(dst) */'
        new_code = pattern.sub(replacer, code)
        if changed:
            return new_code, f"Changed memcpy size argument to sizeof({dst})."
        return code, None

    # ── handler dispatch table ─────────────────────────────────────────────

    _HANDLERS: Dict[str, Any] = {
        "unsafe_gets":            _fix_gets,
        "unsafe_scanf_s":         _fix_scanf_s,
        "unsafe_strcpy":          _fix_strcpy,
        "unsafe_strcat":          _fix_strcat,
        "unsafe_sprintf":         _fix_sprintf,
        "format_string_bug":      _fix_format_string,
        "use_after_free":         _fix_use_after_free,
        "double_free":            _fix_double_free,
        "unchecked_malloc":       _fix_unchecked_malloc,
        "hardcoded_secret":       _fix_hardcoded_secret,
        "integer_overflow_malloc":_fix_malloc_overflow,
        "unsafe_memcpy":          _fix_memcpy,
    }

    # ── diff ──────────────────────────────────────────────────────────────

    def _make_diff(self, original: str, fixed: str, label: str = "source") -> str:
        orig_lines  = original.splitlines(keepends=True)
        fixed_lines = fixed.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines, fixed_lines,
            fromfile=f"original/{label}",
            tofile=f"fixed/{label}",
            lineterm="",
        )
        return "".join(diff)
