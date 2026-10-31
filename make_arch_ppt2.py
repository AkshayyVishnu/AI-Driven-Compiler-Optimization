"""
DeepCompile — Architecture PowerPoint Generator
Minimalistic White + Blue palette
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from pptx.enum.dml import MSO_THEME_COLOR
import copy

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY       = RGBColor(0x0D, 0x23, 0x4E)   # very dark blue  (titles, borders)
ROYAL      = RGBColor(0x1A, 0x56, 0xDB)   # royal blue      (primary shapes)
SKY        = RGBColor(0x76, 0xA9, 0xFA)   # sky blue        (accent shapes)
ICE        = RGBColor(0xEB, 0xF5, 0xFF)   # ice blue        (shape fills)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
DARK_TEXT  = RGBColor(0x1E, 0x29, 0x3B)
MID_TEXT   = RGBColor(0x3B, 0x4A, 0x68)

# ── Slide dimensions (16:9 widescreen) ───────────────────────────────────────
W = Inches(13.33)
H = Inches(7.5)

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H

BLANK_LAYOUT = prs.slide_layouts[6]   # completely blank


# ═══════════════════════════════════════════════════════════════════════════════
# Helper utilities
# ═══════════════════════════════════════════════════════════════════════════════

def add_slide():
    return prs.slides.add_slide(BLANK_LAYOUT)


def bg(slide, color=WHITE):
    """Fill slide background."""
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def rect(slide, x, y, w, h, fill=ICE, line=ROYAL, line_w=Pt(1.5), radius=None):
    """Add a filled rectangle (optionally rounded)."""
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = line_w
    return shape


def rounded_rect(slide, x, y, w, h, fill=ICE, line=ROYAL, line_w=Pt(1.5)):
    """Add rounded rectangle."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    shape = slide.shapes.add_shape(
        5,  # ROUNDED_RECTANGLE
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = line_w
    shape.adjustments[0] = 0.08
    return shape


def txt(slide, text, x, y, w, h, size=Pt(12), bold=False,
        color=DARK_TEXT, align=PP_ALIGN.CENTER, wrap=True):
    """Add a text box."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    p  = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size  = size
    run.font.bold  = bold
    run.font.color.rgb = color
    return tb


def label_shape(slide, shape, text, size=Pt(11), bold=False, color=DARK_TEXT):
    """Write centred text directly into a shape's text frame."""
    tf = shape.text_frame
    tf.word_wrap = True
    p  = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size  = size
    run.font.bold  = bold
    run.font.color.rgb = color


def arrow(slide, x1, y1, x2, y2, color=ROYAL, w=Pt(1.8)):
    """Draw a straight connector with an arrowhead at (x2,y2)."""
    from pptx.util import Inches
    from pptx.oxml.ns import qn
    from lxml import etree

    connector = slide.shapes.add_connector(
        1,  # STRAIGHT
        Inches(x1), Inches(y1), Inches(x2), Inches(y2)
    )
    connector.line.color.rgb = color
    connector.line.width = w

    # Add end arrowhead via XML
    ln = connector.line._ln
    tailEnd = ln.find(qn('a:tailEnd'))
    if tailEnd is not None:
        ln.remove(tailEnd)
    headEnd = ln.find(qn('a:headEnd'))
    if headEnd is None:
        headEnd = etree.SubElement(ln, qn('a:headEnd'))
    headEnd.set('type', 'arrow')
    headEnd.set('w', 'med')
    headEnd.set('len', 'med')
    return connector


def section_header(slide, title, subtitle=""):
    """Blue banner at top of slide."""
    banner = rect(slide, 0, 0, 13.33, 1.1, fill=NAVY, line=NAVY, line_w=Pt(0))
    label_shape(slide, banner, title, size=Pt(26), bold=True, color=WHITE)
    if subtitle:
        txt(slide, subtitle, 0.3, 1.1, 12.73, 0.35,
            size=Pt(12), color=MID_TEXT, align=PP_ALIGN.LEFT)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Title
# ═══════════════════════════════════════════════════════════════════════════════

slide = add_slide()
bg(slide, WHITE)

# Full-width navy bar at top
top = rect(slide, 0, 0, 13.33, 3.2, fill=NAVY, line=NAVY, line_w=Pt(0))

# Royal blue accent stripe
accent = rect(slide, 0, 3.2, 13.33, 0.12, fill=ROYAL, line=ROYAL, line_w=Pt(0))

txt(slide, "DeepCompile",
    0.5, 0.5, 12.33, 1.4,
    size=Pt(36), bold=True, color=WHITE, align=PP_ALIGN.CENTER)

txt(slide, "Multi-Agent Architecture & Pipeline",
    0.5, 1.95, 12.33, 0.9,
    size=Pt(20), bold=False, color=SKY, align=PP_ALIGN.CENTER)

# Tagline
txt(slide, "Analysis  ·  Optimization  ·  Verification",
    0.5, 3.6, 12.33, 0.55,
    size=Pt(16), bold=False, color=ROYAL, align=PP_ALIGN.CENTER)

# Three pillars
pillars = [
    ("Analysis Agent",      "Rule-based + LLM\nbug detection"),
    ("Optimization Agent",  "Auto-fix + LLM code\ntransformation"),
    ("Verification Agent",  "4-layer: Diff · Z3\nPerf · LLM"),
]
for i, (title, desc) in enumerate(pillars):
    px = 1.0 + i * 3.9
    box = rounded_rect(slide, px, 4.35, 3.3, 2.3, fill=ICE, line=ROYAL)
    txt(slide, title, px, 4.45, 3.3, 0.5, size=Pt(13), bold=True,
        color=NAVY, align=PP_ALIGN.CENTER)
    txt(slide, desc, px + 0.1, 5.05, 3.1, 1.4, size=Pt(11),
        color=MID_TEXT, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — System Overview (end-to-end)
# ═══════════════════════════════════════════════════════════════════════════════

slide = add_slide()
bg(slide, WHITE)
section_header(slide, "System Overview",
               "End-to-end flow from user input to verified optimized code")

# Layer boxes (horizontal swim-lanes)
layers = [
    ("Presentation Layer",   "React / Vite UI  ·  Monaco Editor  ·  Result Panels",  ICE,  ROYAL),
    ("API Layer",            "Flask REST + Server-Sent Events (SSE)  ·  Port 5000",  ICE,  ROYAL),
    ("Agent Framework",      "BaseAgent  ·  ContextManager  ·  AgentRegistry  ·  MessageProtocol", ICE, ROYAL),
    ("Multi-Agent Pipeline", "Analysis Agent  →  Optimization Agent  →  Verification Agent", ICE, NAVY),
    ("Infrastructure",       "LLM Client (Ollama / Gemini)  ·  CodeParser  ·  CoT Validator  ·  Z3  ·  GCC", ICE, SKY),
]

top_y = 1.35
for i, (lname, ldesc, lfill, lline) in enumerate(layers):
    by = top_y + i * 1.12
    box = rounded_rect(slide, 0.35, by, 12.63, 0.9, fill=lfill, line=lline)
    txt(slide, lname, 0.45, by + 0.04, 2.8, 0.45,
        size=Pt(11), bold=True, color=NAVY, align=PP_ALIGN.LEFT)
    txt(slide, ldesc, 3.3, by + 0.04, 9.5, 0.8,
        size=Pt(11), color=MID_TEXT, align=PP_ALIGN.LEFT)
    # Vertical connector between layers (except last)
    if i < len(layers) - 1:
        cx = 6.665
        arrow(slide, cx, by + 0.9, cx, by + 1.12, color=ROYAL, w=Pt(1.5))


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — Full Architecture Diagram
# ═══════════════════════════════════════════════════════════════════════════════

slide = add_slide()
bg(slide, WHITE)
section_header(slide, "Overall Architecture",
               "Detailed component map showing every module and its relationships")

# ── Column layout ──────────────────────────────────────────────────────────
# Col 1: Frontend  Col 2: Backend  Col 3: Agents  Col 4: Infrastructure

col_x  = [0.25, 3.55, 6.85, 10.15]
col_w  = 3.0
top_y  = 1.5

# ── Column headers ──
for i, (hdr, sub) in enumerate([
    ("Frontend", "React · Vite"),
    ("Backend", "Flask · SSE"),
    ("Agents", "Multi-Agent"),
    ("Infrastructure", "LLM · Tools"),
]):
    hdr_box = rounded_rect(slide, col_x[i], top_y, col_w, 0.6, fill=NAVY, line=NAVY)
    label_shape(slide, hdr_box, f"{hdr}\n{sub}", size=Pt(10), bold=True, color=WHITE)

# ── Frontend components ──
fe_items = ["Code Editor\n(Monaco)", "Output Terminal\n(SSE stream)", "Results Panel\n(Analysis/Opt/Verify)", "Header Controls\n(Mode · Backend · Theme)"]
for j, item in enumerate(fe_items):
    iy = top_y + 0.8 + j * 1.1
    box = rounded_rect(slide, col_x[0], iy, col_w, 0.85, fill=ICE, line=ROYAL)
    label_shape(slide, box, item, size=Pt(10), color=DARK_TEXT)

# ── Backend components ──
be_items = ["Flask App\napp.py", "StreamQueue\n(SSE Events)", "QueueLogHandler\n(Log → SSE)", "Pipeline Runners\n(_run_* functions)"]
for j, item in enumerate(be_items):
    iy = top_y + 0.8 + j * 1.1
    box = rounded_rect(slide, col_x[1], iy, col_w, 0.85, fill=ICE, line=ROYAL)
    label_shape(slide, box, item, size=Pt(10), color=DARK_TEXT)

# ── Agent components ──
ag_items = ["Analysis Agent\nRule + LLM", "Optimization Agent\nFix + Transform", "Verification Agent\n4-Layer Check", "ContextManager\nShared State"]
ag_colors = [ROYAL, ROYAL, ROYAL, SKY]
for j, (item, clr) in enumerate(zip(ag_items, ag_colors)):
    iy = top_y + 0.8 + j * 1.1
    box = rounded_rect(slide, col_x[2], iy, col_w, 0.85, fill=ICE, line=clr)
    label_shape(slide, box, item, size=Pt(10), color=DARK_TEXT)

# ── Infrastructure components ──
inf_items = ["LLM Client\nOllama / Gemini", "Code Parser\nAST + Heuristics", "CoT Validator\nJSON reasoning", "Z3 + GCC\nSMT + Compile"]
for j, item in enumerate(inf_items):
    iy = top_y + 0.8 + j * 1.1
    box = rounded_rect(slide, col_x[3], iy, col_w, 0.85, fill=ICE, line=SKY)
    label_shape(slide, box, item, size=Pt(10), color=DARK_TEXT)

# ── Horizontal arrows between columns ──
for row in range(4):
    ry = top_y + 1.2 + row * 1.1
    for ci in range(3):
        arrow(slide, col_x[ci] + col_w, ry, col_x[ci + 1], ry, color=SKY, w=Pt(1.2))


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Pipeline Flow
# ═══════════════════════════════════════════════════════════════════════════════

slide = add_slide()
bg(slide, WHITE)
section_header(slide, "Pipeline Flow",
               "Sequential 3-agent pipeline with rollback on verification failure")

# Flow nodes
nodes = [
    (1.0,  3.0, "C++ Source\nCode", ICE,  ROYAL),
    (3.0,  3.0, "Analysis\nAgent",  ICE,  ROYAL),
    (5.25, 3.0, "Optimization\nAgent", ICE, NAVY),
    (7.5,  3.0, "Verification\nAgent", ICE, ROYAL),
    (9.9,  3.0, "Verified\nOutput", ICE, ROYAL),
]

for (nx, ny, nlabel, nfill, nline) in nodes:
    box = rounded_rect(slide, nx, ny, 1.95, 1.3, fill=nfill, line=nline, line_w=Pt(2))
    label_shape(slide, box, nlabel, size=Pt(13), bold=True, color=NAVY)

# Arrows between nodes
positions = [(1.0, 3.0), (3.0, 3.0), (5.25, 3.0), (7.5, 3.0), (9.9, 3.0)]
for i in range(len(positions) - 1):
    x1 = positions[i][0] + 1.95
    x2 = positions[i + 1][0]
    y  = positions[i][1] + 0.65
    arrow(slide, x1, y, x2, y, color=ROYAL, w=Pt(2))

# Arrow labels
arrow_labels = ["parse &\nparse_meta", "findings\nreport", "optimized\ncode"]
label_x = [2.95, 5.2, 7.45]
for lbl, lx in zip(arrow_labels, label_x):
    txt(slide, lbl, lx, 2.45, 1.0, 0.55, size=Pt(9), color=MID_TEXT, align=PP_ALIGN.CENTER)

# PASS / ROLLBACK decision
dec = rounded_rect(slide, 5.4, 5.0, 2.5, 0.85, fill=ICE, line=NAVY, line_w=Pt(2))
label_shape(slide, dec, "PASS / ROLLBACK?", size=Pt(12), bold=True, color=NAVY)

arrow(slide, 8.475, 4.3, 8.475, 5.05, color=NAVY, w=Pt(1.8))   # Verify → Decision
arrow(slide, 7.9, 5.42, 6.0, 5.42, color=ROYAL, w=Pt(1.5))       # Decision → left

txt(slide, "PASS", 9.9, 4.95, 1.1, 0.4, size=Pt(11), bold=True, color=ROYAL)
arrow(slide, 8.475, 5.85, 8.475, 6.4, color=ROYAL, w=Pt(1.5))
txt(slide, "ROLLBACK\n→ revert to original", 7.7, 6.4, 2.5, 0.7, size=Pt(10), color=NAVY, align=PP_ALIGN.CENTER)

# Sub-steps for each agent
sub = [
    (3.0,  "① Code Parser\n② Rule Checks\n③ LLM Enrichment\n④ CoT Validate"),
    (5.25, "① Rule Fixes\n② LLM Transforms\n③ Diff Generate\n④ Save Output"),
    (7.5,  "L1 Diff Test\nL2 Z3 SMT\nL3 Perf Bench\nL4 LLM Reason"),
]
for (sx, stext) in sub:
    txt(slide, stext, sx, 1.35, 1.95, 1.6,
        size=Pt(9), color=MID_TEXT, align=PP_ALIGN.LEFT)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — Agent Internal Layers
# ═══════════════════════════════════════════════════════════════════════════════

slide = add_slide()
bg(slide, WHITE)
section_header(slide, "Agent Internal Architecture",
               "Common layered structure shared by all three agents")

# Outer container
outer = rounded_rect(slide, 2.0, 1.4, 9.33, 5.5, fill=ICE, line=ROYAL, line_w=Pt(2))
txt(slide, "BaseAgent (Abstract)", 2.1, 1.45, 9.0, 0.4,
    size=Pt(12), bold=True, color=NAVY, align=PP_ALIGN.CENTER)

# Inner layers stacked
layers = [
    ("1  Input Layer",          "Receives source_code, file_path, analysis_report via process()",        ICE, ROYAL),
    ("2  Parsing / Context",    "CodeParser  ·  ContextManager.get()  ·  Shared state retrieval",        ICE, ROYAL),
    ("3  Rule-Based Engine",    "Regex patterns, AST heuristics, deterministic bug detection / fixes",    ICE, NAVY),
    ("4  LLM Reasoning",        "PromptTemplate → LLMClient (Ollama/Gemini) → raw JSON response",        ICE, ROYAL),
    ("5  CoT Validator",        "Parses chain-of-thought JSON: findings, reasoning_steps, confidence",    ICE, ROYAL),
    ("6  Output / Context Set", "Returns result dict  ·  context.set() stores for downstream agents",    ICE, SKY),
]

for i, (ltitle, ldesc, lfill, lline) in enumerate(layers):
    ly = 1.95 + i * 0.77
    box = rounded_rect(slide, 2.2, ly, 9.0, 0.65, fill=lfill, line=lline)
    txt(slide, ltitle, 2.3, ly + 0.03, 2.6, 0.55,
        size=Pt(10), bold=True, color=NAVY, align=PP_ALIGN.LEFT)
    txt(slide, ldesc,  4.95, ly + 0.05, 6.1, 0.55,
        size=Pt(10), color=MID_TEXT, align=PP_ALIGN.LEFT)
    if i < len(layers) - 1:
        arrow(slide, 6.67, ly + 0.65, 6.67, ly + 0.77, color=ROYAL, w=Pt(1.2))


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Analysis Agent
# ═══════════════════════════════════════════════════════════════════════════════

slide = add_slide()
bg(slide, WHITE)
section_header(slide, "Analysis Agent",
               "Hybrid static analysis: deterministic rule engine + LLM semantic enrichment")

# Description box
desc_box = rounded_rect(slide, 0.3, 1.3, 12.73, 0.75, fill=ICE, line=ROYAL)
label_shape(slide, desc_box,
    "Detects bugs, performance issues, and security vulnerabilities in C/C++ code. "
    "Always produces results offline via rule-based checks; LLM enriches when available.",
    size=Pt(11), color=DARK_TEXT)

# Flow diagram — 5 boxes
steps = [
    ("Source\nCode\nInput",   ICE,  ROYAL),
    ("Code\nParser\n(AST)",   ICE,  ROYAL),
    ("Rule-Based\nEngine",    ICE,  NAVY),
    ("LLM\nEnrichment",       ICE,  ROYAL),
    ("Merge &\nCoT Validate", ICE,  ROYAL),
    ("Analysis\nReport",      ICE,  SKY),
]
sx_start = 0.45
swidth   = 1.85
sgap     = 0.3
sy       = 2.35

for i, (slabel, sfill, sline) in enumerate(steps):
    sx = sx_start + i * (swidth + sgap)
    box = rounded_rect(slide, sx, sy, swidth, 1.4, fill=sfill, line=sline, line_w=Pt(2))
    label_shape(slide, box, slabel, size=Pt(11), bold=True, color=NAVY)
    if i < len(steps) - 1:
        arrow(slide, sx + swidth, sy + 0.7, sx + swidth + sgap, sy + 0.7, color=ROYAL, w=Pt(1.8))

# Capabilities table
cap_title = rounded_rect(slide, 0.3, 4.0, 12.73, 0.45, fill=NAVY, line=NAVY)
label_shape(slide, cap_title, "Rule-Based Detection Capabilities", size=Pt(12), bold=True, color=WHITE)

caps = [
    "Uninitialized Variable",
    "Buffer Overflow / Off-by-One",
    "Nested Loop O(n²)",
    "Memory Leak (malloc/free)",
    "Division by Zero",
    "Loop-Invariant Strlen / Sizeof",
    "Dead Code After Return",
    "Empty If / Else Body",
    "Type Mismatch (int = string)",
    "Redundant Constant in Loop",
]
col_count = 5
for i, cap in enumerate(caps):
    cx = 0.35 + (i % col_count) * 2.55
    cy = 4.6 + (i // col_count) * 0.95
    cbox = rounded_rect(slide, cx, cy, 2.45, 0.75, fill=ICE, line=ROYAL)
    label_shape(slide, cbox, cap, size=Pt(9), color=DARK_TEXT)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — Optimization Agent
# ═══════════════════════════════════════════════════════════════════════════════

slide = add_slide()
bg(slide, WHITE)
section_header(slide, "Optimization Agent",
               "Applies deterministic rule fixes then LLM-guided code transformations")

desc_box = rounded_rect(slide, 0.3, 1.3, 12.73, 0.75, fill=ICE, line=ROYAL)
label_shape(slide, desc_box,
    "Receives source code + analysis report. Applies rule-based auto-fixes first, then calls "
    "LLM for deeper transformations. Prefers LLM code if it differs; falls back to rule-based. "
    "Saves result to MicroBenchmarks/Generated_optimisation/.",
    size=Pt(11), color=DARK_TEXT)

# Flow
steps = [
    ("Source Code\n+ Analysis\nReport",    ICE, ROYAL),
    ("Rule-Based\nFixes",                  ICE, NAVY),
    ("LLM Code\nTransform",                ICE, ROYAL),
    ("Select Best\n(LLM > Rule)",          ICE, ROYAL),
    ("Unified\nDiff Gen",                  ICE, ROYAL),
    ("Optimized\nOutput",                  ICE, SKY),
]

sx_start = 0.45
swidth   = 1.85
sgap     = 0.3
sy       = 2.35

for i, (slabel, sfill, sline) in enumerate(steps):
    sx = sx_start + i * (swidth + sgap)
    box = rounded_rect(slide, sx, sy, swidth, 1.4, fill=sfill, line=sline, line_w=Pt(2))
    label_shape(slide, box, slabel, size=Pt(11), bold=True, color=NAVY)
    if i < len(steps) - 1:
        arrow(slide, sx + swidth, sy + 0.7, sx + swidth + sgap, sy + 0.7, color=ROYAL, w=Pt(1.8))

# Rule-based fix list
cap_title = rounded_rect(slide, 0.3, 4.0, 6.15, 0.45, fill=NAVY, line=NAVY)
label_shape(slide, cap_title, "Rule-Based Auto-Fixes", size=Pt(12), bold=True, color=WHITE)

rfixes = [
    "Off-by-one: '<=' → '<' in for-loops",
    "Uninitialized variable: add = 0",
    "Loop bound correction",
    "Pattern-matched safe rewrites",
]
for i, rf in enumerate(rfixes):
    by = 4.6 + i * 0.65
    b  = rounded_rect(slide, 0.35, by, 6.0, 0.55, fill=ICE, line=ROYAL)
    label_shape(slide, b, rf, size=Pt(10), color=DARK_TEXT)

# LLM transform list
llm_title = rounded_rect(slide, 6.85, 4.0, 6.15, 0.45, fill=NAVY, line=NAVY)
label_shape(slide, llm_title, "LLM Code Transformations", size=Pt(12), bold=True, color=WHITE)

ltrans = [
    "Algorithmic complexity improvements",
    "Memory management fixes",
    "Security vulnerability patches",
    "Style & maintainability rewrites",
]
for i, lt in enumerate(ltrans):
    by = 4.6 + i * 0.65
    b  = rounded_rect(slide, 6.9, by, 6.0, 0.55, fill=ICE, line=ROYAL)
    label_shape(slide, b, lt, size=Pt(10), color=DARK_TEXT)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — Verification Agent (4 Layers)
# ═══════════════════════════════════════════════════════════════════════════════

slide = add_slide()
bg(slide, WHITE)
section_header(slide, "Verification Agent — 4-Layer Architecture",
               "Multi-layer safety net ensuring correctness, equivalence, and performance")

# Outer frame
outer = rounded_rect(slide, 0.3, 1.3, 9.5, 5.5, fill=ICE, line=NAVY, line_w=Pt(2.5))

layer_data = [
    ("Layer 1", "Differential Testing",
     "Compile & run original vs optimised code. Compare stdout/exit code. "
     "Skipped if original has UB or uninit-var fixes expected.",
     ROYAL),
    ("Layer 2", "Z3 SMT Verification",
     "Extract arithmetic expressions and verify equivalence using the Z3 theorem prover. "
     "Issues ROLLBACK on counterexample found.",
     NAVY),
    ("Layer 3", "Performance Benchmark",
     "Time both binaries with GCC -O2. Report speedup/slowdown. "
     "Does not block pass — informs human reviewer.",
     ROYAL),
    ("Layer 4", "LLM Reasoning",
     "Send original + optimised code to LLM for semantic review. "
     "Returns SAFE / UNSAFE / UNCERTAIN with chain-of-thought.",
     SKY),
]

for i, (tag, title, desc, lcolor) in enumerate(layer_data):
    ly = 1.5 + i * 1.3
    tag_box = rounded_rect(slide, 0.4, ly, 1.1, 1.05, fill=lcolor, line=lcolor)
    label_shape(slide, tag_box, tag, size=Pt(12), bold=True, color=WHITE)
    title_box = rounded_rect(slide, 1.6, ly, 7.95, 0.42, fill=NAVY, line=NAVY)
    label_shape(slide, title_box, title, size=Pt(12), bold=True, color=WHITE)
    desc_box2  = rounded_rect(slide, 1.6, ly + 0.45, 7.95, 0.58, fill=WHITE, line=lcolor)
    label_shape(slide, desc_box2, desc, size=Pt(10), color=DARK_TEXT)
    if i < 3:
        arrow(slide, 5.075, ly + 1.05, 5.075, ly + 1.3, color=ROYAL, w=Pt(1.5))

# Decision panel
dec_outer = rounded_rect(slide, 10.1, 2.5, 2.9, 3.3, fill=ICE, line=NAVY, line_w=Pt(2))

txt(slide, "Decision", 10.1, 2.55, 2.9, 0.4, size=Pt(12), bold=True,
    color=NAVY, align=PP_ALIGN.CENTER)

pass_box = rounded_rect(slide, 10.25, 3.1, 2.6, 0.75, fill=ROYAL, line=ROYAL)
label_shape(slide, pass_box, "PASS\nOptimized code accepted", size=Pt(10), bold=False, color=WHITE)

roll_box = rounded_rect(slide, 10.25, 4.1, 2.6, 0.75, fill=NAVY, line=NAVY)
label_shape(slide, roll_box, "ROLLBACK\nRevert to original", size=Pt(10), bold=False, color=WHITE)

txt(slide, "Triggers:", 10.25, 5.0, 2.6, 0.3, size=Pt(9), bold=True,
    color=MID_TEXT, align=PP_ALIGN.LEFT)
txt(slide, "· Diff test fails (real failure)\n· Z3 finds counterexample\n· Compile error in optimized",
    10.25, 5.3, 2.6, 0.9, size=Pt(9), color=MID_TEXT, align=PP_ALIGN.LEFT)

arrow(slide, 9.8, 3.55, 10.25, 3.47, color=ROYAL, w=Pt(1.5))
arrow(slide, 9.8, 3.55, 10.25, 4.47, color=NAVY, w=Pt(1.5))


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Agent Framework
# ═══════════════════════════════════════════════════════════════════════════════

slide = add_slide()
bg(slide, WHITE)
section_header(slide, "Agent Framework",
               "Reusable infrastructure: message passing, shared context, lifecycle management")

components = [
    ("BaseAgent\n(Abstract)", 1.0, 2.0, 2.8, 3.4,
     "• Abstract process() & get_capabilities()\n• Priority message queue\n• State machine: INIT→RUN→STOP\n• send_message / receive_message\n• Threaded message processor"),
    ("ContextManager\n(Shared State)", 4.6, 2.0, 2.8, 3.4,
     "• Thread-safe key-value store\n• Snapshot / rollback support\n• Shared across all agents\n• Stores: analysis_results,\n  optimization_suggestions,\n  verification_status"),
    ("AgentRegistry\n(Router)", 8.2, 2.0, 2.8, 3.4,
     "• Registers & discovers agents\n• Routes messages by receiver_id\n• Priority-based dispatch\n• Enables decoupled comms"),
    ("MessageProtocol\n(Contracts)", 1.0, 5.65, 2.8, 1.5,
     "Types: REQUEST · RESPONSE · NOTIFICATION\nPriority: HIGH · MEDIUM · LOW"),
]

for (title, cx, cy, cw, ch, cdesc) in components:
    hdr = rounded_rect(slide, cx, cy, cw, 0.55, fill=NAVY, line=NAVY)
    label_shape(slide, hdr, title, size=Pt(12), bold=True, color=WHITE)
    body = rounded_rect(slide, cx, cy + 0.55, cw, ch - 0.55, fill=ICE, line=ROYAL)
    label_shape(slide, body, cdesc, size=Pt(10), color=DARK_TEXT)

# Arrows: BaseAgent ↔ ContextManager ↔ AgentRegistry
arrow(slide, 3.8, 3.7, 4.6, 3.7, color=ROYAL, w=Pt(1.5))
arrow(slide, 4.6, 3.7, 3.8, 3.7, color=ROYAL, w=Pt(1.5))
arrow(slide, 7.4, 3.7, 8.2, 3.7, color=ROYAL, w=Pt(1.5))
arrow(slide, 8.2, 3.7, 7.4, 3.7, color=ROYAL, w=Pt(1.5))

txt(slide, "read/write", 3.85, 3.4, 0.75, 0.3, size=Pt(8), color=MID_TEXT, align=PP_ALIGN.CENTER)
txt(slide, "register/route", 7.45, 3.4, 0.9, 0.3, size=Pt(8), color=MID_TEXT, align=PP_ALIGN.CENTER)

# Concrete agents row
concrete = [
    ("Analysis\nAgent", 1.5),
    ("Optimization\nAgent", 4.5),
    ("Verification\nAgent", 7.5),
]
for (ag_name, ax) in concrete:
    abox = rounded_rect(slide, ax, 5.65, 2.4, 1.1, fill=ICE, line=ROYAL)
    label_shape(slide, abox, f"extends BaseAgent\n{ag_name}", size=Pt(10), bold=False, color=NAVY)

txt(slide, "← Concrete Agents (extend BaseAgent) →", 1.5, 5.35, 8.4, 0.3,
    size=Pt(10), bold=True, color=MID_TEXT, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — Current Deployment Architecture
# ═══════════════════════════════════════════════════════════════════════════════

slide = add_slide()
bg(slide, WHITE)
section_header(slide, "Deployment Architecture",
               "Local full-stack app exposed publicly via Cloudflare Tunnel")

# Internet / Cloudflare cloud
cf_box = rounded_rect(slide, 4.5, 1.4, 4.33, 1.1, fill=ROYAL, line=NAVY, line_w=Pt(2))
label_shape(slide, cf_box, "Cloudflare Network\nhttps://*.trycloudflare.com",
            size=Pt(13), bold=True, color=WHITE)

# User
user_box = rounded_rect(slide, 0.4, 1.65, 2.1, 0.75, fill=ICE, line=ROYAL)
label_shape(slide, user_box, "User\n(Browser)", size=Pt(12), color=DARK_TEXT)
arrow(slide, 2.5, 2.0, 4.5, 2.0, color=ROYAL, w=Pt(1.8))

# cloudflared daemon
cf_daemon = rounded_rect(slide, 4.5, 2.85, 4.33, 0.75, fill=ICE, line=NAVY)
label_shape(slide, cf_daemon, "cloudflared tunnel (daemon)", size=Pt(11), bold=True, color=NAVY)
arrow(slide, 6.67, 2.5, 6.67, 2.85, color=ROYAL, w=Pt(1.8))

# Flask
flask_box = rounded_rect(slide, 4.5, 3.9, 4.33, 0.85, fill=ICE, line=ROYAL)
label_shape(slide, flask_box, "Flask Backend\nlocalhost:5000  /  localhost:8080", size=Pt(11), bold=True, color=NAVY)
arrow(slide, 6.67, 3.6, 6.67, 3.9, color=ROYAL, w=Pt(1.8))

# React (served by Flask)
react_box = rounded_rect(slide, 2.8, 5.1, 2.5, 0.8, fill=ICE, line=ROYAL)
label_shape(slide, react_box, "React Frontend\n(static /dist build)", size=Pt(11), color=DARK_TEXT)

# Multi-Agent Pipeline
pipeline_box = rounded_rect(slide, 7.7, 5.1, 3.8, 0.8, fill=ICE, line=NAVY)
label_shape(slide, pipeline_box, "Multi-Agent Pipeline\nAnalysis → Opt → Verify", size=Pt(11), color=DARK_TEXT)

# Ollama
ollama_box = rounded_rect(slide, 7.7, 6.2, 1.7, 0.75, fill=ICE, line=SKY)
label_shape(slide, ollama_box, "Ollama\n(local LLM)", size=Pt(10), color=DARK_TEXT)

# Gemini
gemini_box = rounded_rect(slide, 9.7, 6.2, 1.7, 0.75, fill=ICE, line=SKY)
label_shape(slide, gemini_box, "Gemini API\n(cloud LLM)", size=Pt(10), color=DARK_TEXT)

arrow(slide, 4.5, 4.32, 4.05, 4.32, color=ROYAL, w=Pt(1.5))
arrow(slide, 4.05, 4.32, 4.05, 5.1, color=ROYAL, w=Pt(1.5))

arrow(slide, 8.8, 4.75, 8.8, 4.32, color=ROYAL, w=Pt(1.5))
arrow(slide, 8.8, 4.32, 8.8, 5.1, color=ROYAL, w=Pt(1.5))

arrow(slide, 8.55, 5.9,  8.55, 6.2,  color=SKY, w=Pt(1.2))
arrow(slide, 10.5, 5.9, 10.5, 6.2,  color=SKY, w=Pt(1.2))

txt(slide, "HTTP\n/api/*", 3.0, 1.85, 1.5, 0.4, size=Pt(9), color=MID_TEXT, align=PP_ALIGN.CENTER)
txt(slide, "proxies\ntraffic", 5.85, 3.6, 1.6, 0.35, size=Pt(9), color=MID_TEXT, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════════════════════════════════

OUT = r"E:\SEM 4\CD_Refined\Architecture_Diagrams_v2.pptx"
prs.save(OUT)
print(f"Saved: {OUT}")
