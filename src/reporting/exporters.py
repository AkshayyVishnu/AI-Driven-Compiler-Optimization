"""
Render explainability reports for terminal, Markdown, and HTML outputs.
"""

from __future__ import annotations

import html
import json
from typing import Iterable

from .report_contract import ExplainabilityReport


def render_terminal_report(report: ExplainabilityReport) -> str:
    lines = [
        f"Explainability Report: {report.file_path}",
        f"Status           : {report.status}",
        f"Workflow Status  : {report.workflow_status}",
        f"Findings         : {len(report.findings)}",
        f"Transformations  : {len(report.transformations)}",
        f"Verification     : {report.verification_verdict.get('status', 'UNKNOWN')}",
        f"Security         : {report.security_verdict.get('status', 'UNKNOWN')}",
    ]
    if report.output_artifact_path:
        lines.append(f"Output Artifact  : {report.output_artifact_path}")
    if report.stop_reason:
        lines.append(f"Stop Reason      : {report.stop_reason}")
    if report.review_required:
        lines.append("Review Required  : yes")
    if report.reasoning_summary:
        lines.append("")
        lines.append("Reasoning Summary:")
        for item in report.reasoning_summary:
            lines.append(f"  - {item}")
    return "\n".join(lines)


def export_markdown_report(report: ExplainabilityReport) -> str:
    lines = [
        f"# Explainability Report: `{report.file_path}`",
        "",
        f"- Status: **{report.status}**",
        f"- Workflow status: **{report.workflow_status}**",
        f"- Findings: **{len(report.findings)}**",
        f"- Transformations: **{len(report.transformations)}**",
        f"- Verification: **{report.verification_verdict.get('status', 'UNKNOWN')}**",
        f"- Security: **{report.security_verdict.get('status', 'UNKNOWN')}**",
    ]
    if report.output_artifact_path:
        lines.append(f"- Output artifact: `{report.output_artifact_path}`")
    if report.stop_reason:
        lines.append(f"- Stop reason: `{report.stop_reason}`")
    if report.escalation_reasons:
        lines.append(f"- Escalation reasons: {', '.join(report.escalation_reasons)}")
    lines.extend(_markdown_section("Reasoning Summary", report.reasoning_summary))
    lines.extend(_markdown_section(
        "Transformations",
        [f"{item.get('type')}: {item.get('description')}" for item in report.transformations],
    ))
    if report.unified_diff:
        lines.extend([
            "## Unified Diff",
            "",
            "```diff",
            report.unified_diff,
            "```",
        ])
    lines.extend([
        "",
        "## Raw Contract",
        "",
        "```json",
        json.dumps(report.to_dict(), indent=2),
        "```",
    ])
    return "\n".join(lines)


def export_html_report(report: ExplainabilityReport) -> str:
    summary_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in report.reasoning_summary
    )
    transform_items = "".join(
        "<li><strong>{}</strong>: {}</li>".format(
            html.escape(item.get("type", "unknown")),
            html.escape(item.get("description", "")),
        )
        for item in report.transformations
    )
    diff_block = ""
    if report.unified_diff:
        diff_block = (
            "<h2>Unified Diff</h2>"
            f"<pre>{html.escape(report.unified_diff)}</pre>"
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Explainability Report</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 32px; color: #1e293b; }}
    h1, h2 {{ color: #1d4ed8; }}
    .meta {{ background: #eff6ff; padding: 16px; border-radius: 8px; }}
    pre {{ background: #0f172a; color: #e2e8f0; padding: 16px; overflow-x: auto; border-radius: 8px; }}
    code {{ font-family: Consolas, monospace; }}
  </style>
</head>
<body>
  <h1>Explainability Report</h1>
  <div class="meta">
    <p><strong>File:</strong> {html.escape(report.file_path)}</p>
    <p><strong>Status:</strong> {html.escape(report.status)}</p>
    <p><strong>Workflow status:</strong> {html.escape(report.workflow_status)}</p>
    <p><strong>Verification:</strong> {html.escape(report.verification_verdict.get('status', 'UNKNOWN'))}</p>
    <p><strong>Security:</strong> {html.escape(report.security_verdict.get('status', 'UNKNOWN'))}</p>
  </div>
  <h2>Reasoning Summary</h2>
  <ul>{summary_items}</ul>
  <h2>Transformations</h2>
  <ul>{transform_items}</ul>
  {diff_block}
</body>
</html>
"""


def _markdown_section(title: str, items: Iterable[str]) -> list[str]:
    values = [item for item in items if item]
    if not values:
        return []
    lines = ["", f"## {title}", ""]
    lines.extend([f"- {item}" for item in values])
    return lines
