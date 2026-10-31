# CLI and Explainability Guide

## Revised Scope
The CLI is now centered on source-to-source optimization and explainability.

Out of scope for the revised submission:
- LLVM/Clang integration
- `g++` toolchain integration as a required deliverable

## Canonical Entry Point
Main CLI:
- `run_pipeline.py`

Default behavior:
- runs the orchestrated workflow unless `--basic-pipeline` is supplied

## Useful Commands

Deterministic orchestrated run:

```powershell
python run_pipeline.py .\MicroBenchmarks\Testcases\TC11_buffer_overflow_loop.cpp --no-llm
```

Basic legacy 4-stage run:

```powershell
python run_pipeline.py .\MicroBenchmarks\Testcases\TC11_buffer_overflow_loop.cpp --basic-pipeline --no-llm
```

Export Markdown explainability report:

```powershell
python run_pipeline.py .\MicroBenchmarks\Testcases\TC11_buffer_overflow_loop.cpp --no-llm --export-md .\logs\report.md
```

Export HTML explainability report:

```powershell
python run_pipeline.py .\MicroBenchmarks\Testcases\TC11_buffer_overflow_loop.cpp --no-llm --export-html .\logs\report.html
```

## Orchestration Controls
- `--basic-pipeline`: disable orchestration/refinement
- `--max-cycles`: maximum refinement cycles
- `--low-conf-threshold`: minimum confidence before refinement is attempted

## Explainability Contract
The shared report contract is implemented in:
- `src/reporting/report_contract.py`

Exporters are implemented in:
- `src/reporting/exporters.py`

The report includes:
- findings
- transformations
- verification verdict
- security verdict
- reasoning summary
- unified diff
- output artifact path
- workflow status
- iteration count
- stop reason
- escalation reasons

## Recommended Submission Mode
For formal submission evidence, use:
- `--no-llm`

This keeps the run deterministic and reproducible.
