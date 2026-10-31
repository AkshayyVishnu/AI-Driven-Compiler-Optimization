"""
Domain-specific pattern detection and safe, exact-match optimizations.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


def detect_domain_findings(source_code: str) -> List[Dict]:
    findings: List[Dict] = []
    findings.extend(_detect_scientific_numeric_patterns(source_code))
    findings.extend(_detect_memory_buffer_patterns(source_code))
    return findings


def apply_domain_optimizations(source_code: str) -> Tuple[str, List[Dict]]:
    code = source_code
    transforms: List[Dict] = []

    code, scientific_transforms = _apply_scientific_numeric_rules(code)
    if scientific_transforms:
        transforms.extend(scientific_transforms)

    code, memory_transforms = _apply_memory_buffer_rules(code)
    if memory_transforms:
        transforms.extend(memory_transforms)

    return code, transforms


def _detect_scientific_numeric_patterns(source_code: str) -> List[Dict]:
    findings: List[Dict] = []

    reduction_re = re.compile(
        r"for\s*\([^)]*\)\s*\{\s*(\w+)\s*\+=\s*(\w+)\[(\w+)\]\s*;\s*\}",
        re.DOTALL,
    )
    for match in reduction_re.finditer(source_code):
        line = source_code[: match.start()].count("\n") + 1
        findings.append({
            "type": "scientific_numeric_reduction",
            "description": (
                "Numeric reduction loop detected. This is a scientific/numeric "
                "pattern that benefits from low-overhead loop structure and "
                "predictable accumulator handling."
            ),
            "recommendation": (
                "Prefer prefix increment and keep the accumulator loop body minimal."
            ),
            "line": line,
            "severity": "low",
            "source": "domain",
            "domain": "scientific_numeric",
        })

    return findings


def _detect_memory_buffer_patterns(source_code: str) -> List[Dict]:
    findings: List[Dict] = []

    copy_loop_re = re.compile(
        r"for\s*\(\s*int\s+(\w+)\s*=\s*0\s*;\s*\1\s*<\s*(\w+)\s*;\s*\1\+\+\s*\)\s*\{\s*(\w+)\[\1\]\s*=\s*(\w+)\[\1\]\s*;\s*\}",
        re.DOTALL,
    )
    for match in copy_loop_re.finditer(source_code):
        line = source_code[: match.start()].count("\n") + 1
        findings.append({
            "type": "memory_buffer_copy_loop",
            "description": (
                "Element-wise buffer copy loop detected. This is a memory/buffer-heavy "
                "systems pattern and may be replaced by memcpy when the source and "
                "destination are distinct buffers."
            ),
            "recommendation": "Use memcpy(dst, src, n * sizeof(dst[0])) when buffers do not overlap.",
            "line": line,
            "severity": "medium",
            "source": "domain",
            "domain": "memory_buffer",
        })

    return findings


def _apply_scientific_numeric_rules(source_code: str) -> Tuple[str, List[Dict]]:
    transforms: List[Dict] = []
    updated = source_code

    if not _detect_scientific_numeric_patterns(source_code):
        return updated, transforms

    prefix_increment_re = re.compile(
        r"(for\s*\([^;]*;[^;]*;\s*)(\w+)\+\+(\s*\))"
    )
    new_code, count = prefix_increment_re.subn(
        lambda match: match.group(1) + "++" + match.group(2) + match.group(3),
        updated,
    )
    if count > 0:
        updated = new_code
        transforms.append({
            "type": "scientific_numeric_loop_tuning",
            "description": (
                "Normalized numeric reduction loops to use prefix increment in the "
                "loop clause for a lower-overhead scientific/numeric loop style."
            ),
            "severity": "info",
            "domain": "scientific_numeric",
        })

    return updated, transforms


def _apply_memory_buffer_rules(source_code: str) -> Tuple[str, List[Dict]]:
    transforms: List[Dict] = []

    copy_loop_re = re.compile(
        r"for\s*\(\s*int\s+(\w+)\s*=\s*0\s*;\s*\1\s*<\s*(\w+)\s*;\s*\1\+\+\s*\)\s*\{\s*(\w+)\[\1\]\s*=\s*(\w+)\[\1\]\s*;\s*\}",
        re.DOTALL,
    )

    def repl(match: re.Match) -> str:
        index_var = match.group(1)
        bound = match.group(2)
        dst = match.group(3)
        src = match.group(4)
        if dst == src:
            return match.group(0)
        return f"memcpy({dst}, {src}, {bound} * sizeof({dst}[0])); /* domain: memory_buffer */"

    updated, count = copy_loop_re.subn(repl, source_code)
    if count > 0 and updated != source_code:
        transforms.append({
            "type": "memory_buffer_copy_loop_to_memcpy",
            "description": (
                "Replaced an exact-match element-wise copy loop with memcpy for "
                "buffer-heavy systems code."
            ),
            "severity": "info",
            "domain": "memory_buffer",
        })

    return updated, transforms
