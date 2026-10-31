from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "Technical Deliverlables and Documents"
PDF_PATH = DOCS / "DeepCompile_Final_Dossier.pdf"


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleCenter",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17324D"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetaCenter",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#425466"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#17324D"),
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#425466"),
            spaceAfter=4,
        )
    )
    return styles


def bullet_list(items, styles):
    return ListFlowable(
        [
            ListItem(Paragraph(item, styles["Body"]), leftIndent=12)
            for item in items
        ],
        bulletType="bullet",
        start="circle",
        leftIndent=16,
    )


def metrics_table(styles):
    rows = [
        ["Metric", "Measured Value"],
        ["Cases executed", "12"],
        ["Workflow PASS", "10"],
        ["Workflow ESCALATE", "2"],
        ["Workflow ROLLBACK", "0"],
        ["New vulnerabilities introduced", "0"],
        ["Correctness-style pass rate", "83.3%"],
        ["Average orchestrated latency", "4.5553 s"],
        ["Median orchestrated latency", "3.0267 s"],
        ["Average baseline pipeline latency", "0.0025 s"],
        ["Verification parallel checks", "4.2473 s average"],
    ]
    table = Table(rows, colWidths=[85 * mm, 65 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("LEADING", (0, 0), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9FB3C8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#EDF2F7")]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def inventory_table(styles):
    rows = [
        ["Artifact", "Status"],
        ["Phase 2 Integration Report", "Completed"],
        ["Refinement and Orchestrator Design Note", "Completed"],
        ["Conflict Resolution Framework", "Completed"],
        ["CLI and Explainability Guide", "Completed"],
        ["Domain Optimization Note", "Completed"],
        ["Failure Taxonomy", "Completed"],
        ["Phase 3 Completion Report", "Completed"],
        ["Complete Test Report", "Completed"],
        ["Performance Benchmark Report", "Completed"],
        ["Comparative Analysis Report", "Completed"],
        ["User Manual", "Completed"],
        ["Developer Guide", "Completed"],
        ["Final Presentation Deck", "Completed in this packaging phase"],
        ["Combined Final Dossier PDF", "Completed in this packaging phase"],
    ]
    table = Table(rows, colWidths=[110 * mm, 40 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F6F8B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9FB3C8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FB")]),
                ("FONTSIZE", (0, 0), (-1, -1), 9.2),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#5B6871"))
    canvas.drawString(18 * mm, 10 * mm, "DeepCompile Final Dossier")
    canvas.drawRightString(192 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf():
    styles = build_styles()
    story = []

    story.append(Spacer(1, 14 * mm))
    story.append(Paragraph("DeepCompile Final Dossier", styles["TitleCenter"]))
    story.append(Paragraph("AI-Driven Source-to-Source Optimization with Verification and Security Review", styles["MetaCenter"]))
    story.append(Paragraph("Roll Number: 24CSB0A06", styles["MetaCenter"]))
    story.append(Paragraph("Module: CD Refined", styles["MetaCenter"]))
    story.append(Paragraph("Date: April 19, 2026", styles["MetaCenter"]))
    story.append(Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')} UTC", styles["MetaCenter"]))
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Executive Summary", styles["SectionTitle"]))
    story.append(
        Paragraph(
            "DeepCompile is a multi-agent source-to-source optimization system for C and C++ programs. "
            "The final submission path emphasizes conservative rewrites, deterministic verification, "
            "security regression checks, bounded refinement, and explainability exports.",
            styles["Body"],
        )
    )

    story.append(Paragraph("Final Scope", styles["SectionTitle"]))
    story.append(
        bullet_list(
            [
                "Source-to-source optimization only",
                "Formal evidence generated in deterministic no-LLM mode",
                "Optional LLM support retained as a non-required feature",
                "No LLVM, Clang, or g++ dependency in the required submission path",
            ],
            styles,
        )
    )

    story.append(Paragraph("Architecture Summary", styles["SectionTitle"]))
    story.append(
        Paragraph(
            "The baseline workflow is Analysis -> Optimization -> Verification -> Security. "
            "An orchestrator sits above this path and decides whether the initial result is accepted, "
            "whether bounded refinement is needed, or whether the case must escalate for review.",
            styles["Body"],
        )
    )
    story.append(
        bullet_list(
            [
                "Analysis Agent: rule-based issue detection plus domain findings",
                "Optimization Agent: conservative rewrites and domain-aware transforms",
                "Verification Agent: rollback-capable safety checks with recorded timings",
                "Security Agent: layered audit for regression detection",
                "Refinement Agent: bounded retry loop with repeated-diff and no-improvement stopping",
                "Orchestrator Agent: workflow verdicts, escalation metadata, and deterministic control flow",
            ],
            styles,
        )
    )

    story.append(Paragraph("Weeks 8-14 Delivery Status", styles["SectionTitle"]))
    story.append(
        bullet_list(
            [
                "Week 8: baseline 4-stage pipeline frozen and Phase 2 report updated",
                "Week 9: refinement agent, orchestrator agent, and conflict-resolution notes completed",
                "Week 10: canonical CLI path and explainability report contract completed",
                "Week 11: domain optimization modules, caching, and stage timings completed",
                "Week 12: failure taxonomy and Phase 3 completion documentation completed",
                "Week 13: deterministic benchmark suite executed and formal report set generated",
                "Week 14: user manual, developer guide, presentation deck, and final dossier packaging completed",
            ],
            styles,
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("Deterministic Evaluation Summary", styles["SectionTitle"]))
    story.append(
        Paragraph(
            "Formal evaluation was executed across 12 representative benchmark cases in deterministic "
            "rule-based mode. Optional LLM behavior is excluded from these reported metrics.",
            styles["Body"],
        )
    )
    story.append(metrics_table(styles))
    story.append(Spacer(1, 5 * mm))
    story.append(
        Paragraph(
            "Interpretation: The measured workflow is strongest on safety and auditability. It introduced "
            "zero new vulnerabilities in the evaluated set, but the observed 83.3% pass rate remains below "
            "the original aspirational 95% target and should be presented honestly as current measured performance.",
            styles["Body"],
        )
    )

    story.append(Paragraph("Explainability and Reporting", styles["SectionTitle"]))
    story.append(
        bullet_list(
            [
                "Unified report contract for findings, transformations, verdicts, reasoning summary, diff, and workflow metadata",
                "Export modes available as terminal summary, Markdown, and HTML",
                "Shared reporting path now aligns CLI, pipeline, and final documentation outputs",
            ],
            styles,
        )
    )

    story.append(Paragraph("Failure Taxonomy", styles["SectionTitle"]))
    story.append(
        bullet_list(
            [
                "false positive",
                "false negative",
                "unsafe optimization",
                "verification miss",
                "security miss",
                "refinement oscillation",
                "orchestration conflict",
                "toolchain failure",
                "unsupported code path",
            ],
            styles,
        )
    )

    story.append(Paragraph("Deliverable Inventory", styles["SectionTitle"]))
    story.append(inventory_table(styles))
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            "Primary supporting artifacts remain in the Technical Deliverlables and Documents directory and the "
            "evaluation directory, including the generated Week 13 JSON evidence set.",
            styles["Small"],
        )
    )

    story.append(Paragraph("Limitations and Honest Notes", styles["SectionTitle"]))
    story.append(
        bullet_list(
            [
                "The verification stage is currently the dominant latency bottleneck.",
                "Two benchmark cases escalated for review instead of being automatically repaired.",
                "The formal evaluation path is intentionally rule-based and deterministic.",
                "Compiler integration is outside the final revised scope for this submission package.",
            ],
            styles,
        )
    )

    story.append(Paragraph("Conclusion", styles["SectionTitle"]))
    story.append(
        Paragraph(
            "DeepCompile now has a complete and documented source-to-source submission path covering orchestration, "
            "bounded refinement, deterministic evidence generation, explainability exports, and final academic packaging. "
            "The strongest next engineering step would be improving verification efficiency and expanding safe rule coverage.",
            styles["Body"],
        )
    )

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="DeepCompile Final Dossier",
        author="OpenAI Codex",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build_pdf()
