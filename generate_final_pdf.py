"""
generate_final_pdf.py — Custom PDF Generator for DeepCompile Final Report

Modified from evaluation/build_pdf.py to support image inclusion and report formatting.
"""

import argparse
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.platypus.flowables import KeepTogether

# ── Colour palette ─────────────────────────────────────────────────────────────
C_DARK    = colors.HexColor("#1a1a2e")   # deep navy
C_ACCENT  = colors.HexColor("#0f3460")   # medium blue
C_CODE_BG = colors.HexColor("#f4f4f8")   # light grey
C_CODE_FG = colors.HexColor("#2d2d2d")
C_TABLE_H = colors.HexColor("#0f3460")
C_TABLE_A = colors.HexColor("#eef2ff")
C_RULE    = colors.HexColor("#4361ee")
C_WHITE   = colors.white
C_GREY    = colors.HexColor("#666680")

W, H = A4

def _styles():
    base = getSampleStyleSheet()

    def add(name, **kw):
        base.add(ParagraphStyle(name=name, **kw))

    add("DocTitle",
        fontName="Helvetica-Bold", fontSize=24,
        textColor=C_DARK, spaceAfter=8, alignment=TA_CENTER)

    add("DocSubtitle",
        fontName="Helvetica", fontSize=14,
        textColor=C_ACCENT, spaceAfter=4, alignment=TA_CENTER)

    add("DocVersion",
        fontName="Helvetica", fontSize=10,
        textColor=C_GREY, spaceAfter=20, alignment=TA_CENTER)

    add("H1",
        fontName="Helvetica-Bold", fontSize=16,
        textColor=C_WHITE, spaceAfter=6, spaceBefore=16,
        backColor=C_DARK, borderPad=6,
        leftIndent=0, rightIndent=0)

    add("H2",
        fontName="Helvetica-Bold", fontSize=13,
        textColor=C_ACCENT, spaceAfter=4, spaceBefore=12,
        leftIndent=0)

    add("H3",
        fontName="Helvetica-Bold", fontSize=11,
        textColor=C_DARK, spaceAfter=3, spaceBefore=8,
        leftIndent=0)

    add("Body",
        fontName="Helvetica", fontSize=10,
        textColor=C_DARK, spaceAfter=6,
        leading=14)

    add("MyBullet",
        fontName="Helvetica", fontSize=10,
        textColor=C_DARK, spaceAfter=3,
        leftIndent=20, bulletIndent=10, leading=14)

    return base

def _rule():
    return HRFlowable(
        width="100%", thickness=1.5,
        color=C_RULE, spaceAfter=8, spaceBefore=4,
    )

def parse_md(md_text, styles, base_dir):
    story = []
    lines = md_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        # ── Image syntax: ![alt](path)
        img_match = re.match(r"^!\[.*?\]\((.*?)\)", line.strip())
        if img_match:
            img_path = img_match.group(1)
            full_path = os.path.join(base_dir, img_path)
            if os.path.exists(full_path):
                story.append(Spacer(1, 0.5 * cm))
                # Adjust width to fit page
                img = Image(full_path, width=15*cm, height=8*cm, kind='proportional')
                story.append(img)
                story.append(Spacer(1, 0.5 * cm))
            else:
                story.append(Paragraph(f"[Image not found: {img_path}]", styles["Body"]))
            i += 1
            continue

        # ── H1
        if line.startswith("# "):
            if i > 0: story.append(Spacer(1, 10))
            story.append(Paragraph(line[2:].strip(), styles["H1"]))
            i += 1
            continue

        # ── H2
        if line.startswith("## "):
            story.append(Paragraph(line[3:].strip(), styles["H2"]))
            i += 1
            continue

        # ── Bullet list
        if re.match(r"^[-*]\s+", line):
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i]):
                text = re.sub(r"^[-*]\s+", "", lines[i]).strip()
                text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
                story.append(Paragraph(f"• {text}", styles["MyBullet"]))
                i += 1
            continue

        # ── Horizontal rule
        if line.strip() == "---":
            story.append(_rule())
            i += 1
            continue

        # ── Blank line
        if not line.strip():
            story.append(Spacer(1, 6))
            i += 1
            continue

        # ── Body paragraph
        text = line.strip()
        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
        story.append(Paragraph(text, styles["Body"]))
        i += 1

    return story

def build_pdf(md_path: str, out_path: str):
    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()

    base_dir = os.path.dirname(os.path.abspath(md_path))
    styles = _styles()

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title="DeepCompile Final Submission",
    )

    story = []
    
    # Title parsing from MD headers (first few lines)
    # For simplicity, manually add cover info
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("Final Project Submission", styles["DocTitle"]))
    story.append(Paragraph("DeepCompile: AI-Driven Compiler Optimization", styles["DocSubtitle"]))
    story.append(Paragraph("Roll Number: 24CSB0A06  ·  Date: April 19, 2026", styles["DocVersion"]))
    story.append(_rule())
    story.append(Spacer(1, 1 * cm))

    # Parse body
    story.extend(parse_md(md_text, styles, base_dir))

    # Page number callback
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(C_GREY)
        canvas.drawRightString(W - 2.5 * cm, 1.5 * cm, f"Page {doc.page}")
        canvas.drawString(2.5 * cm, 1.5 * cm, "DeepCompile Final Report — 24CSB0A06")
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"Final Report PDF saved to: {out_path}")

if __name__ == "__main__":
    md_file = "FINAL_SUBMISSION.md"
    out_file = "DeepCompile_Final_Submission.pdf"
    build_pdf(md_file, out_file)
