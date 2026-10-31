# Failure Taxonomy

## Purpose
This taxonomy organizes the main failure modes for the revised source-to-source DeepCompile workflow.

## Categories

### 1. False Positive
Trigger:
- a rule flags a problem that is not materially unsafe or inefficient

Current mitigation:
- conservative rule patterns
- verification/security veto before acceptance

Residual risk:
- noisy findings can still reduce report clarity

### 2. False Negative
Trigger:
- a real issue is not detected by current rules

Current mitigation:
- layered analysis plus security scan
- explicit documentation of unsupported patterns

Residual risk:
- rule coverage is incomplete by design

### 3. Unsafe Optimization
Trigger:
- a transformation changes semantics or introduces undefined behavior

Current mitigation:
- verification stage
- rollback mechanism

Residual risk:
- verification coverage depends on the available checks for that case

### 4. Verification Miss
Trigger:
- verification passes a transformation that should have been rejected

Current mitigation:
- differential testing, Z3, and performance checks where available
- refinement/escalation path

Residual risk:
- some program behaviors remain difficult to prove under all conditions

### 5. Security Miss
Trigger:
- security scanning fails to recognize a newly introduced weakness

Current mitigation:
- multi-layer security scan
- rollback on new high-severity rule/heuristic findings

Residual risk:
- heuristic coverage is not complete

### 6. Refinement Oscillation
Trigger:
- retries keep producing the same or equivalent ineffective diff

Current mitigation:
- repeated diff detection
- bounded max cycle count

Residual risk:
- near-duplicate but non-identical retries may still consume a cycle

### 7. Orchestration Conflict
Trigger:
- multiple plausible outcomes compete without a clear automatic winner

Current mitigation:
- explicit priority order
- escalation for review

Residual risk:
- review is still required in ambiguous cases

### 8. Toolchain Failure
Trigger:
- optional external tooling is unavailable

Current mitigation:
- deterministic no-LLM mode
- source-to-source workflow does not require compiler integration for formal scope

Residual risk:
- optional verification depth may be reduced

### 9. Unsupported Code Path
Trigger:
- source shape falls outside the current parser/rule assumptions

Current mitigation:
- conservative transformation rules
- escalation and documentation

Residual risk:
- unsupported constructs remain a known boundary
