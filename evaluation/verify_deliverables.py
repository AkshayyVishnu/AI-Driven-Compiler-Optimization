from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    ROOT / "Technical Deliverlables and Documents" / "Phase2_Integration_Report.md",
    ROOT / "Technical Deliverlables and Documents" / "Refinement_Orchestrator_Design_Note.md",
    ROOT / "Technical Deliverlables and Documents" / "Conflict_Resolution_Framework.md",
    ROOT / "Technical Deliverlables and Documents" / "CLI_Explainability_Guide.md",
    ROOT / "Technical Deliverlables and Documents" / "Domain_Optimization_Note.md",
    ROOT / "Technical Deliverlables and Documents" / "Failure_Taxonomy.md",
    ROOT / "Technical Deliverlables and Documents" / "Phase3_Completion_Report.md",
    ROOT / "Technical Deliverlables and Documents" / "Complete_Test_Report.md",
    ROOT / "Technical Deliverlables and Documents" / "Performance_Benchmark_Report.md",
    ROOT / "Technical Deliverlables and Documents" / "Comparative_Analysis_Report.md",
    ROOT / "Technical Deliverlables and Documents" / "User_Manual.md",
    ROOT / "Technical Deliverlables and Documents" / "Developer_Guide.md",
    ROOT / "Technical Deliverlables and Documents" / "DeepCompile_Final_Dossier.md",
    ROOT / "Technical Deliverlables and Documents" / "DeepCompile_Final_Dossier.pdf",
    ROOT / "Technical Deliverlables and Documents" / "DeepCompile_Final_Presentation.pptx",
    ROOT / "Technical Deliverlables and Documents" / "Week8_14_Implementation_Checklist.md",
    ROOT / "evaluation" / "week13_results.json",
]


def verify_pptx(pptx_path: Path) -> list[str]:
    issues: list[str] = []
    with zipfile.ZipFile(pptx_path, "r") as archive:
        names = archive.namelist()
        if "[Content_Types].xml" not in names:
            issues.append("PPTX missing [Content_Types].xml")
        slide_count = sum(
            1
            for name in names
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        )
        notes_count = sum(
            1
            for name in names
            if name.startswith("ppt/notesSlides/notesSlide") and name.endswith(".xml")
        )
        if slide_count < 1:
            issues.append("PPTX contains no slide XML")
        if notes_count < 1:
            issues.append("PPTX contains no notes pages")
    return issues


def verify_week13_json(results_path: Path) -> list[str]:
    issues: list[str] = []
    data = json.loads(results_path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        issues.append("week13_results.json is empty or not a list")
        return issues
    required_keys = {
        "filename",
        "workflow_status",
        "verification_status",
        "security_status",
        "elapsed_s",
    }
    for idx, item in enumerate(data, start=1):
        missing = sorted(required_keys - set(item))
        if missing:
            issues.append(f"week13_results.json item {idx} missing keys: {', '.join(missing)}")
            break
    return issues


def main() -> int:
    missing = [path for path in REQUIRED if not path.exists()]
    if missing:
        for path in missing:
            print(f"MISSING: {path}")
        return 1

    issues: list[str] = []
    issues.extend(
        verify_pptx(ROOT / "Technical Deliverlables and Documents" / "DeepCompile_Final_Presentation.pptx")
    )
    issues.extend(verify_week13_json(ROOT / "evaluation" / "week13_results.json"))

    if issues:
        for issue in issues:
            print(f"ISSUE: {issue}")
        return 1

    print("deliverables_ok=True")
    print(f"required_count={len(REQUIRED)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
