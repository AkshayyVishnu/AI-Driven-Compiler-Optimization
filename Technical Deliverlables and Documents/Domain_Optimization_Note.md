# Domain Optimization Note

## Objective
Week 11 focuses on adding domain-aware source-to-source rules for two fixed buckets:
- scientific and numeric loops
- memory and buffer-heavy systems code

## Implemented Location
- `src/domains/domain_rules.py`

## Bucket 1: Scientific and Numeric Loops
Current detection:
- numeric reduction loops such as `acc += a[i]`

Current optimization:
- normalize loop iterator style toward prefix increment in recognized numeric-loop contexts

Intended benefit:
- cleaner low-overhead loop form
- domain visibility in analysis output

## Bucket 2: Memory and Buffer-Heavy Code
Current detection:
- exact-match element-wise copy loops

Current optimization:
- rewrite exact buffer copy loops to `memcpy(...)` when source and destination differ

Intended benefit:
- replace verbose element-by-element copies with a clear bulk-memory operation

## Integration Points
Domain findings are surfaced in:
- `AnalysisAgent`

Domain transforms are applied in:
- `OptimizationAgent`

## Deterministic Validation
Validated in:
- `tests/test_orchestration_reporting.py`

Covered checks:
- memory copy loop detection
- memory copy loop rewrite to `memcpy`
- scientific reduction pattern detection
