# DeepCompile Developer Guide

## Canonical Code Paths
- agent framework: `agent_framework/`
- active implementation: `src/`
- CLI entry point: `run_pipeline.py`

## Main Modules
- `src/agents/analysis_agent.py`
- `src/agents/optimization_agent.py`
- `src/agents/verification_agent.py`
- `src/agents/security_agent.py`
- `src/agents/refinement_agent.py`
- `src/agents/orchestrator_agent.py`
- `src/reporting/report_contract.py`
- `src/reporting/exporters.py`
- `src/domains/domain_rules.py`

## Adding a New Rule-Based Optimization
1. Add the detection or transform in `src/domains/domain_rules.py` or the relevant agent.
2. Surface the new finding through `AnalysisAgent`.
3. Apply the rewrite through `OptimizationAgent`.
4. Add deterministic coverage in `tests/`.

## Adding a New Workflow Decision
1. Update `RefinementAgent` if the change affects retry logic.
2. Update `OrchestratorAgent` if the change affects workflow-level acceptance or escalation.
3. Reflect the metadata in `src/reporting/report_contract.py`.
4. Update the Markdown notes in `Technical Deliverlables and Documents/`.

## Deterministic Testing
Use built-in `unittest` where possible so the suite can run without extra packages.

Current deterministic orchestration/reporting/domain coverage:

```powershell
python -m unittest tests.test_orchestration_reporting -v
```

## Revised Project Boundary
The current formal delivery scope is source-to-source optimization and explainability.

Out of scope for the revised path:
- LLVM/Clang integration
- `g++` integration as a required deliverable
- LLM-only evaluation as formal evidence
