# Conflict Resolution Framework

## Purpose
This document defines how DeepCompile resolves disagreements between optimization, verification, and security outcomes in the revised source-to-source workflow.

## Priority Order
The system uses a strict priority order:

1. Verification and security veto unsafe output.
2. Correctness-preserving optimization is preferred over cosmetic changes.
3. Cosmetic or explainability-only changes are lowest priority.

## Decision Rules

### Accept
Accept the optimized source when:
- verification status is `PASS`
- security status is `PASS`
- no rollback trigger is present

### Roll Back
Roll back when:
- verification returns `ROLLBACK`
- security returns `ROLLBACK`

### Retry
Retry through the refinement agent when:
- the initial run does not pass cleanly
- or the optimization confidence is below threshold

### Escalate
Escalate for human review when:
- refinement repeats the same diff pattern
- refinement shows no material improvement
- refinement exhausts the maximum cycle count
- multiple competing fixes cannot be resolved automatically

## Human-in-the-Loop Cases
The following conditions should be explicitly treated as review cases:
- unresolved verification failure
- repeated rollback
- oscillating or repeated refinement behavior
- conflicting but plausible fixes

## Evidence in the Codebase
Implemented in:
- `src/agents/orchestrator_agent.py`
- `src/agents/refinement_agent.py`

Reported through:
- `src/reporting/report_contract.py`
- `src/reporting/exporters.py`
