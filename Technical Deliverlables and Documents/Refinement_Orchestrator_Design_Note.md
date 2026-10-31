# Refinement and Orchestrator Design Note

## Scope
This note documents the Week 9 implementation for the revised DeepCompile scope:
- source-to-source optimization only
- deterministic rule-based evaluation as the formal submission mode
- optional LLM assistance retained as a non-required feature

## Implemented Components

### Orchestrator Agent
Location:
- `src/agents/orchestrator_agent.py`

Responsibilities:
- run the baseline 4-stage pipeline
- evaluate whether the result is acceptable without refinement
- trigger bounded refinement when verification fails, security fails, or confidence is too low
- emit a workflow-level verdict independent of the inner pipeline status

Workflow statuses used:
- `PASS`
- `ROLLBACK`
- `ESCALATE`
- `ABORTED`

Returned orchestration metadata includes:
- `workflow_status`
- `iteration_count`
- `stop_reason`
- `review_required`
- `escalation_reasons`
- `cache_hits`

### Refinement Agent
Location:
- `src/agents/refinement_agent.py`

Responsibilities:
- retry optimization in a bounded loop
- merge verification/security feedback back into the analysis context
- stop safely instead of looping indefinitely

Implemented guardrails:
- maximum `3` cycles by default
- stop on repeated diff signature
- stop on no material improvement
- stop on rollback trigger
- stop immediately on successful pass

## Convergence Rules
- If the initial pipeline passes verification and security with sufficient confidence, refinement is skipped.
- The first retry prefers a conservative rule-only path.
- Later retries may reuse the configured LLM path if available, but this is optional.
- If the same effective diff reappears, the workflow escalates.
- If a retry does not improve verification/security/confidence, the workflow escalates.

## Deterministic Evaluation Mode
Formal testing for submission should run with:
- `--no-llm`
- the orchestrated path enabled by default

This makes the refinement/orchestration logic reproducible without depending on external model availability.

## Validation Completed
Validated by deterministic unit tests in:
- `tests/test_orchestration_reporting.py`

Covered cases:
- direct pass from initial pipeline
- successful refinement promoted to final `PASS`
- explainability export consistency
