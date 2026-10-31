
import os
import re
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
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
    Preformatted
)

C_DARK    = colors.HexColor("#1a1a2e")
C_ACCENT  = colors.HexColor("#0f3460")
C_CODE_BG = colors.HexColor("#f4f4f8")
C_CODE_FG = colors.HexColor("#2d2d2d")
C_TABLE_H = colors.HexColor("#0f3460")
C_RULE    = colors.HexColor("#4361ee")
C_WHITE   = colors.white
C_GREY    = colors.HexColor("#666680")

W, H = A4

def _styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(name="DocTitle", fontName="Helvetica-Bold", fontSize=26, textColor=C_DARK, spaceAfter=12, alignment=TA_CENTER))
    base.add(ParagraphStyle(name="DocSubtitle", fontName="Helvetica", fontSize=16, textColor=C_ACCENT, spaceAfter=8, alignment=TA_CENTER))
    base.add(ParagraphStyle(name="DocInfo", fontName="Helvetica", fontSize=12, textColor=C_GREY, spaceAfter=20, alignment=TA_CENTER))
    base.add(ParagraphStyle(name="H1", fontName="Helvetica-Bold", fontSize=18, textColor=C_WHITE, spaceAfter=10, spaceBefore=20, backColor=C_DARK, borderPad=8))
    base.add(ParagraphStyle(name="H2", fontName="Helvetica-Bold", fontSize=15, textColor=C_ACCENT, spaceAfter=8, spaceBefore=14))
    base.add(ParagraphStyle(name="H3", fontName="Helvetica-Bold", fontSize=12, textColor=C_DARK, spaceAfter=6, spaceBefore=10))
    base.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=11, textColor=C_DARK, spaceAfter=8, leading=15, alignment=TA_JUSTIFY))
    base.add(ParagraphStyle(name="Bullet", fontName="Helvetica", fontSize=11, textColor=C_DARK, spaceAfter=4, leftIndent=25, bulletIndent=10, leading=15))
    base.add(ParagraphStyle(name="Code", fontName="Courier", fontSize=9, textColor=C_CODE_FG, leftIndent=10, rightIndent=10, spaceBefore=6, spaceAfter=6))
    return base

def parse_markdown(md_text, styles):
    story = []
    lines = md_text.splitlines()
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        if line.startswith("# "):
            if i > 0: story.append(PageBreak())
            story.append(Paragraph(line[2:].strip(), styles["H1"]))
            i += 1
        elif line.startswith("## "):
            story.append(Paragraph(line[3:].strip(), styles["H2"]))
            i += 1
        elif line.startswith("### "):
            story.append(Paragraph(line[4:].strip(), styles["H3"]))
            i += 1
        elif line.strip() == "---":
            story.append(HRFlowable(width="100%", thickness=1, color=C_RULE, spaceBefore=10, spaceAfter=10))
            i += 1
        elif line.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_block = "\n".join(code_lines)
            story.append(Spacer(1, 0.2*cm))
            story.append(Preformatted(code_block, styles["Code"], backColor=C_CODE_BG))
            story.append(Spacer(1, 0.2*cm))
            i += 1
        elif line.startswith("|"):
            table_data = []
            while i < len(lines) and line.startswith("|"):
                row = [cell.strip() for cell in line.split("|")[1:-1]]
                if not all(c.startswith("---") for c in row):
                    table_data.append([Paragraph(c, styles["Body"]) for c in row])
                i += 1
                if i < len(lines): line = lines[i]
            if table_data:
                t = Table(table_data, hAlign='LEFT', colWidths=[W*0.18]*len(table_data[0]))
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), C_TABLE_H),
                    ('TEXTCOLOR', (0, 0), (-1, 0), C_WHITE),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 0.5, C_GREY)
                ]))
                story.append(t)
                story.append(Spacer(1, 10))
        elif re.match(r"^[-*]\s+", line.strip()):
            text = re.sub(r"^[-*]\s+", "", line.strip())
            text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
            story.append(Paragraph(text, styles["Bullet"], bulletText="•"))
            i += 1
        elif line.strip():
            text = line.strip()
            text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
            text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
            # Basic LaTeX support for PDF (limited)
            text = text.replace("$$\\eta = ", "<b>Efficiency (eta) = </b>")
            story.append(Paragraph(text, styles["Body"]))
            i += 1
        else:
            story.append(Spacer(1, 6))
            i += 1
    return story

def create_report_pdf():
    md_path = "FINAL_20_PAGE_REPORT.md"
    pdf_path = "DeepCompile_20Page_Final_Report.pdf"
    
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    styles = _styles()
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    story = []
    # Cover Page
    story.append(Spacer(1, 4*cm))
    story.append(Paragraph("National Institute of Technology Warangal", styles["DocSubtitle"]))
    story.append(Paragraph("Department of Computer Science and Engineering", styles["DocInfo"]))
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("DeepCompile: An AI-Driven Multi-Agent Framework for Deterministic Source-to-Source Compiler Optimization", styles["DocTitle"]))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Project Report - CD Refined (PBL)", styles["DocSubtitle"]))
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph("Submitted By: Akshay Vishnu (24CSB0A06)", styles["DocInfo"]))
    story.append(Paragraph("Date: April 19, 2026", styles["DocInfo"]))
    story.append(PageBreak())
    
    story.extend(parse_markdown(content, styles))
    
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(C_GREY)
        canvas.drawRightString(W - 2*cm, 1*cm, f"Page {doc.page}")
        canvas.drawString(2*cm, 1*cm, "DeepCompile Final Report | NIT Warangal")
        canvas.restoreState()
        
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF generated: {pdf_path}")

if __name__ == "__main__":
    create_report_pdf()
