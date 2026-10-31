"""
Generate the project pitch PPT for DeepCompile.
Run: python make_ppt.py
Output: AI_Compiler_Optimization_Pitch.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import copy

# ── Colour palette ──────────────────────────────────────────────────────────
BG_DARK      = RGBColor(0x0D, 0x1B, 0x2A)   # deep navy
ACCENT_CYAN  = RGBColor(0x00, 0xD4, 0xFF)   # electric cyan
ACCENT_GREEN = RGBColor(0x39, 0xFF, 0x14)   # neon green
ACCENT_RED   = RGBColor(0xFF, 0x45, 0x5E)   # alert red
WHITE        = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY   = RGBColor(0xCC, 0xD6, 0xE0)
MID_GREY     = RGBColor(0x55, 0x66, 0x77)
CARD_BG      = RGBColor(0x14, 0x2A, 0x3E)   # slightly lighter navy for cards

# ── Slide dimensions (16:9 widescreen) ──────────────────────────────────────
SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)


def hex2rgb(h):
    h = h.lstrip('#')
    return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))


# ── Helpers ──────────────────────────────────────────────────────────────────

def set_slide_bg(slide, color: RGBColor):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, x, y, w, h, fill_color, line_color=None, line_width=None):
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        x, y, w, h
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if line_color:
        shape.line.color.rgb = line_color
        if line_width:
            shape.line.width = line_width
    else:
        shape.line.fill.background()
    return shape


def add_text_box(slide, text, x, y, w, h,
                 font_size=18, bold=False, color=WHITE,
                 align=PP_ALIGN.LEFT, italic=False, wrap=True):
    txBox = slide.shapes.add_textbox(x, y, w, h)
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return txBox


def add_paragraph(tf, text, font_size=16, bold=False,
                  color=WHITE, align=PP_ALIGN.LEFT, italic=False,
                  space_before=None):
    p = tf.add_paragraph()
    p.alignment = align
    if space_before:
        p.space_before = space_before
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return p


def add_accent_bar(slide, x, y, w=Inches(0.06), h=Inches(0.55), color=ACCENT_CYAN):
    add_rect(slide, x, y, w, h, color)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def slide_title(prs):
    """Slide 1 — Title / Hero"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    set_slide_bg(slide, BG_DARK)

    # Top cyan bar
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), ACCENT_CYAN)

    # Bottom cyan bar
    add_rect(slide, Inches(0), Inches(7.42), SLIDE_W, Inches(0.08), ACCENT_CYAN)

    # Big title
    tb = slide.shapes.add_textbox(Inches(0.6), Inches(1.5), Inches(12.1), Inches(2.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = "DeepCompile"
    r.font.size = Pt(40)
    r.font.bold = True
    r.font.color.rgb = WHITE

    # Subtitle
    add_text_box(slide,
                 "A Multi-Agent Pipeline for Safe, Verified C/C++ Code Optimization",
                 Inches(1.2), Inches(3.5), Inches(11.0), Inches(0.8),
                 font_size=20, color=ACCENT_CYAN, align=PP_ALIGN.CENTER)

    # Tag line
    add_text_box(slide,
                 "Compiler Design  |  AI  |  Formal Verification  |  Security",
                 Inches(1.2), Inches(4.4), Inches(11.0), Inches(0.5),
                 font_size=14, color=LIGHT_GREY, align=PP_ALIGN.CENTER, italic=True)

    # Decorative left accent
    add_rect(slide, Inches(0.3), Inches(1.4), Inches(0.06), Inches(3.6), ACCENT_CYAN)

    # Bottom label
    add_text_box(slide, "Semester 4  |  March 2026",
                 Inches(0), Inches(6.9), SLIDE_W, Inches(0.45),
                 font_size=12, color=MID_GREY, align=PP_ALIGN.CENTER)

    return slide


def slide_problem(prs):
    """Slide 2 — The Problem"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), ACCENT_RED)

    add_text_box(slide, "THE PROBLEM", Inches(0.5), Inches(0.25),
                 Inches(4), Inches(0.5), font_size=11, bold=True,
                 color=ACCENT_RED)

    add_text_box(slide,
                 "Compilers optimize for speed. They can't optimize for safety.",
                 Inches(0.5), Inches(0.7), Inches(12), Inches(1.0),
                 font_size=30, bold=True, color=WHITE)

    problems = [
        ("01", "Compilers cannot detect semantic intent — they miss bugs hidden in logic."),
        ("02", "Optimized code can silently introduce new memory vulnerabilities."),
        ("03", "No existing tool combines optimization + correctness verification + security audit in one pass."),
        ("04", "LLM-based code fixers exist — but none can prove the fix didn't break something."),
    ]

    for i, (num, text) in enumerate(problems):
        y = Inches(1.8) + i * Inches(1.18)
        add_rect(slide, Inches(0.5), y, Inches(0.7), Inches(0.75), ACCENT_RED)
        add_text_box(slide, num, Inches(0.5), y + Inches(0.05),
                     Inches(0.7), Inches(0.65), font_size=18, bold=True,
                     color=WHITE, align=PP_ALIGN.CENTER)
        add_rect(slide, Inches(1.3), y, Inches(11.5), Inches(0.75), CARD_BG)
        add_text_box(slide, text, Inches(1.45), y + Inches(0.1),
                     Inches(11.2), Inches(0.6), font_size=16, color=LIGHT_GREY)

    return slide


def slide_what_is_it(prs):
    """Slide 3 — What Is It?"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), ACCENT_CYAN)

    add_text_box(slide, "WHAT IS IT?", Inches(0.5), Inches(0.25),
                 Inches(4), Inches(0.5), font_size=11, bold=True, color=ACCENT_CYAN)

    add_text_box(slide,
                 "A 4-Stage Intelligent Pipeline for C/C++ Code",
                 Inches(0.5), Inches(0.7), Inches(12.3), Inches(0.9),
                 font_size=28, bold=True, color=WHITE)

    # Pipeline boxes
    agents = [
        ("ANALYSIS\nAGENT",    "Find bugs\n& smells",      ACCENT_CYAN),
        ("OPTIMIZATION\nAGENT","Fix the\ncode",             ACCENT_GREEN),
        ("VERIFICATION\nAGENT","Did the fix\nbreak it?",    hex2rgb("FFAA00")),
        ("SECURITY\nAGENT",    "Did the fix\ncreate vulns?",ACCENT_RED),
    ]

    box_w  = Inches(2.7)
    box_h  = Inches(2.0)
    gap    = Inches(0.3)
    start_x = Inches(0.5)
    y_box  = Inches(1.9)

    arrow_points = []

    for i, (name, desc, color) in enumerate(agents):
        x = start_x + i * (box_w + gap)
        # Outer glow rect
        add_rect(slide, x - Inches(0.04), y_box - Inches(0.04),
                 box_w + Inches(0.08), box_h + Inches(0.08), color)
        # Inner box
        add_rect(slide, x, y_box, box_w, box_h, CARD_BG)
        # Agent number
        add_text_box(slide, f"0{i+1}", x + Inches(0.1), y_box + Inches(0.08),
                     Inches(0.5), Inches(0.35), font_size=11, bold=True, color=color)
        # Name
        add_text_box(slide, name, x, y_box + Inches(0.1),
                     box_w, Inches(0.85), font_size=14, bold=True,
                     color=WHITE, align=PP_ALIGN.CENTER)
        # Desc
        add_text_box(slide, desc, x, y_box + Inches(1.0),
                     box_w, Inches(0.9), font_size=13, color=LIGHT_GREY,
                     align=PP_ALIGN.CENTER)

        arrow_points.append(x + box_w)

    # Arrows between boxes
    for ax in arrow_points[:-1]:
        add_text_box(slide, ">>", ax, y_box + Inches(0.75),
                     gap, Inches(0.5), font_size=16, bold=True,
                     color=ACCENT_CYAN, align=PP_ALIGN.CENTER)

    # Source label
    add_text_box(slide, "INPUT: C++ Source Code",
                 Inches(0.5), Inches(1.55), Inches(4), Inches(0.35),
                 font_size=12, color=ACCENT_CYAN, italic=True)

    # Output label
    add_text_box(slide,
                 "OUTPUT: Verified, Secure, Optimized Code  -OR-  Rollback + Explanation",
                 Inches(0.5), Inches(4.15), Inches(12.3), Inches(0.45),
                 font_size=13, color=ACCENT_GREEN, bold=True)

    # Shared Context bar
    add_rect(slide, Inches(0.5), Inches(4.75), Inches(12.3), Inches(0.55), CARD_BG,
             line_color=ACCENT_CYAN, line_width=Pt(1.2))
    add_text_box(slide,
                 "  Shared ContextManager  |  Versioned State  |  Rollback Support  |  Thread-Safe",
                 Inches(0.5), Inches(4.77), Inches(12.3), Inches(0.5),
                 font_size=12, color=ACCENT_CYAN, align=PP_ALIGN.CENTER)

    # Message bus bar
    add_rect(slide, Inches(0.5), Inches(5.45), Inches(12.3), Inches(0.55), CARD_BG,
             line_color=hex2rgb("FFAA00"), line_width=Pt(1.2))
    add_text_box(slide,
                 "  Message Bus  |  Priority Queues (HIGH / MED / LOW)  |  Agent Registry  |  JSON Protocol",
                 Inches(0.5), Inches(5.47), Inches(12.3), Inches(0.5),
                 font_size=12, color=hex2rgb("FFAA00"), align=PP_ALIGN.CENTER)

    # LLM bar
    add_rect(slide, Inches(0.5), Inches(6.15), Inches(12.3), Inches(0.55), CARD_BG,
             line_color=ACCENT_GREEN, line_width=Pt(1.2))
    add_text_box(slide,
                 "  LLM Backend: Qwen 2.5 Coder  |  Chain-of-Thought (CoT) Validated  |  Offline-Capable Fallback",
                 Inches(0.5), Inches(6.17), Inches(12.3), Inches(0.5),
                 font_size=12, color=ACCENT_GREEN, align=PP_ALIGN.CENTER)

    return slide


def slide_architecture(prs):
    """Slide 4 — Architecture: Framework"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), ACCENT_CYAN)

    add_text_box(slide, "ARCHITECTURE", Inches(0.5), Inches(0.25),
                 Inches(5), Inches(0.5), font_size=11, bold=True, color=ACCENT_CYAN)
    add_text_box(slide, "Multi-Agent Framework — Three Core Pillars",
                 Inches(0.5), Inches(0.7), Inches(12), Inches(0.8),
                 font_size=26, bold=True, color=WHITE)

    pillars = [
        {
            "title": "Message Protocol",
            "color": ACCENT_CYAN,
            "items": [
                "JSON-based typed messages",
                "Types: REQUEST / RESPONSE / NOTIFICATION",
                "Priority queues: HIGH / MED / LOW",
                "Correlation IDs for request tracking",
                "Agents never call each other directly",
            ]
        },
        {
            "title": "ContextManager",
            "color": ACCENT_GREEN,
            "items": [
                "Thread-safe shared blackboard",
                "Versioned state with full history",
                "Rollback to any prior version",
                "Dot-notation nested key access",
                "ctx.set() / ctx.get() / ctx.rollback()",
            ]
        },
        {
            "title": "AgentRegistry",
            "color": hex2rgb("FFAA00"),
            "items": [
                "Central agent discovery & routing",
                "Agents self-register on creation",
                "start_all() / stop_all() lifecycle",
                "Per-agent statistics & health",
                "Extensible: add new agents easily",
            ]
        },
    ]

    col_w = Inches(3.9)
    gap   = Inches(0.28)
    sx    = Inches(0.5)
    sy    = Inches(1.7)

    for i, pillar in enumerate(pillars):
        x = sx + i * (col_w + gap)
        color = pillar["color"]

        # Header bar
        add_rect(slide, x, sy, col_w, Inches(0.55), color)
        add_text_box(slide, pillar["title"], x, sy + Inches(0.06),
                     col_w, Inches(0.45), font_size=15, bold=True,
                     color=BG_DARK, align=PP_ALIGN.CENTER)

        # Body
        add_rect(slide, x, sy + Inches(0.55), col_w, Inches(4.65), CARD_BG,
                 line_color=color, line_width=Pt(1.0))

        for j, item in enumerate(pillar["items"]):
            iy = sy + Inches(0.7) + j * Inches(0.82)
            # bullet dot
            add_rect(slide, x + Inches(0.15), iy + Inches(0.12),
                     Inches(0.1), Inches(0.1), color)
            add_text_box(slide, item, x + Inches(0.35), iy,
                         col_w - Inches(0.45), Inches(0.75),
                         font_size=13.5, color=LIGHT_GREY)

    # Message flow diagram at the bottom
    add_rect(slide, Inches(0.5), Inches(6.5), Inches(12.3), Inches(0.72), CARD_BG)
    add_text_box(slide,
                 "Agent A  --send_message()-->  Registry  --route_message()-->  Agent B  --process()-->  Response",
                 Inches(0.5), Inches(6.55), Inches(12.3), Inches(0.55),
                 font_size=13, color=ACCENT_CYAN, align=PP_ALIGN.CENTER, italic=True)

    return slide


def slide_analysis(prs):
    """Slide 5 — Analysis Agent"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), ACCENT_CYAN)

    add_text_box(slide, "AGENT 01 — ANALYSIS", Inches(0.5), Inches(0.25),
                 Inches(6), Inches(0.45), font_size=11, bold=True, color=ACCENT_CYAN)
    add_text_box(slide, "Hybrid Bug Detection: Rules + LLM",
                 Inches(0.5), Inches(0.65), Inches(12), Inches(0.85),
                 font_size=26, bold=True, color=WHITE)

    # Two columns
    # Left: Rule-based
    add_rect(slide, Inches(0.5), Inches(1.6), Inches(5.9), Inches(5.5), CARD_BG,
             line_color=ACCENT_CYAN, line_width=Pt(1.2))
    add_text_box(slide, "LAYER 1 — Rule-Based (Always Active)",
                 Inches(0.6), Inches(1.65), Inches(5.7), Inches(0.5),
                 font_size=14, bold=True, color=ACCENT_CYAN)

    rules = [
        "Uninitialized variable detection",
        "Buffer overflow — variable index in arrays",
        "Off-by-one: loop uses <= instead of <",
        "Nested O(n^2) loop complexity",
        "Memory leak: malloc > free count",
        "Division-by-zero risk (var assigned 0 as divisor)",
    ]
    for i, r in enumerate(rules):
        y = Inches(2.25) + i * Inches(0.75)
        add_rect(slide, Inches(0.65), y + Inches(0.15),
                 Inches(0.08), Inches(0.08), ACCENT_CYAN)
        add_text_box(slide, r, Inches(0.85), y,
                     Inches(5.4), Inches(0.7), font_size=13, color=LIGHT_GREY)

    # Right: LLM + CoT
    add_rect(slide, Inches(6.6), Inches(1.6), Inches(6.2), Inches(2.4), CARD_BG,
             line_color=ACCENT_GREEN, line_width=Pt(1.2))
    add_text_box(slide, "LAYER 2 — LLM Enrichment (Qwen 2.5 Coder)",
                 Inches(6.7), Inches(1.65), Inches(6.0), Inches(0.5),
                 font_size=14, bold=True, color=ACCENT_GREEN)
    llm_items = [
        "Structured Chain-of-Thought prompt",
        "CoT Validator parses LLM output",
        "Findings merged & deduplicated",
        "Graceful fallback if LLM offline",
    ]
    for i, item in enumerate(llm_items):
        y = Inches(2.25) + i * Inches(0.42)
        add_rect(slide, Inches(6.75), y + Inches(0.12),
                 Inches(0.08), Inches(0.08), ACCENT_GREEN)
        add_text_box(slide, item, Inches(6.95), y,
                     Inches(5.7), Inches(0.4), font_size=13, color=LIGHT_GREY)

    # CoT Validator box
    add_rect(slide, Inches(6.6), Inches(4.15), Inches(6.2), Inches(2.95), CARD_BG,
             line_color=hex2rgb("FFAA00"), line_width=Pt(1.2))
    add_text_box(slide, "CoT Validator — LLM Trust Layer",
                 Inches(6.7), Inches(4.2), Inches(6.0), Inches(0.5),
                 font_size=14, bold=True, color=hex2rgb("FFAA00"))
    cot_items = [
        "Parses structured JSON from LLM response",
        "Validates: findings, reasoning_steps, conclusion",
        "Extracts confidence score (0.0 – 1.0)",
        "Rejects malformed or hallucinated output",
        "LLM findings NEVER bypass rule layer",
    ]
    for i, item in enumerate(cot_items):
        y = Inches(4.75) + i * Inches(0.44)
        add_rect(slide, Inches(6.75), y + Inches(0.12),
                 Inches(0.08), Inches(0.08), hex2rgb("FFAA00"))
        add_text_box(slide, item, Inches(6.95), y,
                     Inches(5.7), Inches(0.42), font_size=13, color=LIGHT_GREY)

    return slide


def slide_verification(prs):
    """Slide 6 — Verification Agent"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), hex2rgb("FFAA00"))

    add_text_box(slide, "AGENT 03 — VERIFICATION", Inches(0.5), Inches(0.25),
                 Inches(6), Inches(0.45), font_size=11, bold=True, color=hex2rgb("FFAA00"))
    add_text_box(slide, "4-Layer Correctness Guarantee",
                 Inches(0.5), Inches(0.65), Inches(12), Inches(0.85),
                 font_size=26, bold=True, color=WHITE)

    layers = [
        {
            "num": "L1",
            "title": "Differential Testing",
            "color": ACCENT_CYAN,
            "desc": "Compiles both original & optimized code with g++. Runs both with identical inputs. Compares stdout byte-for-byte. Timeout: 10s per run.",
        },
        {
            "num": "L2",
            "title": "Z3 SMT Solver (Formal Proof)",
            "color": ACCENT_GREEN,
            "desc": "Extracts return expressions. Declares symbolic Z3 integer variables. Checks: is there ANY input where results differ? PROVEN EQUIVALENT or COUNTEREXAMPLE.",
        },
        {
            "num": "L3",
            "title": "Performance Benchmark",
            "color": hex2rgb("FFAA00"),
            "desc": "Compiles with -O2 & timing wrappers. Runs 5 iterations each. Reports speedup ratio. Fails if optimized is significantly slower.",
        },
        {
            "num": "L4",
            "title": "LLM Semantic Reasoning",
            "color": hex2rgb("AA66FF"),
            "desc": "Asks Qwen to compare original vs. optimized. Checks semantic intent is preserved. Validated through CoT validator before verdict.",
        },
    ]

    for i, layer in enumerate(layers):
        col = i % 2
        row = i // 2
        x = Inches(0.5) + col * Inches(6.5)
        y = Inches(1.65) + row * Inches(2.65)
        w = Inches(6.2)
        h = Inches(2.45)
        color = layer["color"]

        add_rect(slide, x, y, w, h, CARD_BG, line_color=color, line_width=Pt(1.5))
        # num badge
        add_rect(slide, x, y, Inches(0.65), Inches(0.5), color)
        add_text_box(slide, layer["num"], x, y + Inches(0.03),
                     Inches(0.65), Inches(0.45), font_size=13, bold=True,
                     color=BG_DARK, align=PP_ALIGN.CENTER)
        add_text_box(slide, layer["title"], x + Inches(0.7), y + Inches(0.06),
                     w - Inches(0.8), Inches(0.45), font_size=14, bold=True, color=color)
        add_text_box(slide, layer["desc"], x + Inches(0.15), y + Inches(0.6),
                     w - Inches(0.3), Inches(1.75), font_size=13, color=LIGHT_GREY)

    # Rollback footer
    add_rect(slide, Inches(0.5), Inches(7.0), Inches(12.3), Inches(0.38), ACCENT_RED)
    add_text_box(slide,
                 "   If ANY layer fails  ->  ContextManager.rollback()  ->  Original code restored automatically",
                 Inches(0.5), Inches(7.02), Inches(12.3), Inches(0.35),
                 font_size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    return slide


def slide_security(prs):
    """Slide 7 — Security Agent"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), ACCENT_RED)

    add_text_box(slide, "AGENT 04 — SECURITY", Inches(0.5), Inches(0.25),
                 Inches(6), Inches(0.45), font_size=11, bold=True, color=ACCENT_RED)
    add_text_box(slide, "4-Layer Vulnerability Guard",
                 Inches(0.5), Inches(0.65), Inches(12), Inches(0.85),
                 font_size=26, bold=True, color=WHITE)

    # Left column — 4 layers
    layers_left = [
        ("L1  Rule-Based (Confidence 0.90)",   ACCENT_RED,
         "gets(), strcpy(), scanf %s, sprintf(), strcat()\nFormat string bugs (CWE-134)\nUse-after-free: free()/delete + dereference pattern"),
        ("L2  Heuristic Multi-Signal (0.65–0.85)", hex2rgb("FF8C00"),
         "7 heuristics: taint flow, unchecked malloc, signed/unsigned\nmismatch, int-overflow in malloc, buffer loop write,\nrecursive large buffer, race condition"),
    ]

    for i, (title, color, desc) in enumerate(layers_left):
        y = Inches(1.65) + i * Inches(2.35)
        add_rect(slide, Inches(0.5), y, Inches(6.2), Inches(2.15), CARD_BG,
                 line_color=color, line_width=Pt(1.5))
        add_text_box(slide, title, Inches(0.65), y + Inches(0.1),
                     Inches(5.9), Inches(0.45), font_size=13, bold=True, color=color)
        add_text_box(slide, desc, Inches(0.65), y + Inches(0.6),
                     Inches(5.9), Inches(1.45), font_size=12.5, color=LIGHT_GREY)

    layers_right = [
        ("L3  LLM Semantic Scan (Confidence <= 0.70)", hex2rgb("AA66FF"),
         "Qwen 2.5 Coder reviews optimized vs original code.\nCoT validated. LLM CANNOT trigger rollback alone.\nProvides narrative reasoning for audit trail."),
        ("L4  cppcheck Integration (Confidence 0.85)", ACCENT_GREEN,
         "Industry static analysis tool (optional).\nXML output parsed for CWE-mapped findings.\nGracefully skipped if cppcheck not installed."),
    ]

    for i, (title, color, desc) in enumerate(layers_right):
        y = Inches(1.65) + i * Inches(2.35)
        add_rect(slide, Inches(6.9), y, Inches(5.9), Inches(2.15), CARD_BG,
                 line_color=color, line_width=Pt(1.5))
        add_text_box(slide, title, Inches(7.05), y + Inches(0.1),
                     Inches(5.65), Inches(0.45), font_size=13, bold=True, color=color)
        add_text_box(slide, desc, Inches(7.05), y + Inches(0.6),
                     Inches(5.65), Inches(1.45), font_size=12.5, color=LIGHT_GREY)

    # Key innovation footer
    add_rect(slide, Inches(0.5), Inches(6.35), Inches(12.3), Inches(0.75), CARD_BG,
             line_color=ACCENT_RED, line_width=Pt(1.5))
    add_text_box(slide,
                 "KEY INNOVATION:  Only NEW high-severity findings (introduced by optimization) trigger rollback.\n"
                 "Rollback threshold: Layer 1 or Layer 2 finding with severity=HIGH and confidence >= 0.80",
                 Inches(0.65), Inches(6.4), Inches(12.0), Inches(0.65),
                 font_size=12.5, color=ACCENT_RED, bold=True)

    return slide


def slide_novelty(prs):
    """Slide 8 — Novelty"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), ACCENT_GREEN)

    add_text_box(slide, "NOVELTY", Inches(0.5), Inches(0.25),
                 Inches(4), Inches(0.45), font_size=11, bold=True, color=ACCENT_GREEN)
    add_text_box(slide, "What Makes This System Different",
                 Inches(0.5), Inches(0.65), Inches(12), Inches(0.85),
                 font_size=26, bold=True, color=WHITE)

    novelties = [
        (ACCENT_CYAN,   "Rollback-Capable Shared Context",
                        "Most pipelines fail silently. Ours tracks versioned state and explicitly reverts to the last safe checkpoint if any stage fails."),
        (ACCENT_GREEN,  "New-Vulnerability Differential Analysis",
                        "We don't just scan for bugs — we compare pre/post optimization and only flag vulnerabilities the optimizer *introduced*."),
        (hex2rgb("FFAA00"), "Offline-First Hybrid Intelligence",
                        "Rule-based layer works with zero LLM. When Qwen is available, it enriches results. The system is never blocked by connectivity."),
        (hex2rgb("AA66FF"), "CoT-Validated LLM Trust",
                        "LLM output is structurally parsed by a CoT Validator before being trusted. Hallucinated or malformed output is silently discarded."),
        (ACCENT_RED,    "Formal Z3 Equivalence Proof",
                        "Beyond testing — Z3 SMT solver mathematically proves expressions are equivalent for ALL possible inputs, not just sampled ones."),
        (hex2rgb("00FFCC"), "Layered Rollback Trust Hierarchy",
                        "LLM can inform but never trigger rollback alone. Only deterministic layers (rules, heuristics) can revert code. Safety-critical design."),
    ]

    for i, (color, title, desc) in enumerate(novelties):
        col = i % 2
        row = i // 2
        x = Inches(0.5) + col * Inches(6.5)
        y = Inches(1.65) + row * Inches(1.8)
        w = Inches(6.2)
        h = Inches(1.62)

        add_rect(slide, x, y, Inches(0.08), h, color)
        add_rect(slide, x + Inches(0.08), y, w - Inches(0.08), h, CARD_BG)
        add_text_box(slide, title, x + Inches(0.2), y + Inches(0.1),
                     w - Inches(0.3), Inches(0.45), font_size=14, bold=True, color=color)
        add_text_box(slide, desc, x + Inches(0.2), y + Inches(0.55),
                     w - Inches(0.3), Inches(1.0), font_size=12.5, color=LIGHT_GREY)

    return slide


def slide_proposed_arch(prs):
    """Slide 9 — Proposed Architecture (Future)"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), hex2rgb("AA66FF"))

    add_text_box(slide, "PROPOSED ARCHITECTURE", Inches(0.5), Inches(0.25),
                 Inches(6), Inches(0.45), font_size=11, bold=True, color=hex2rgb("AA66FF"))
    add_text_box(slide, "From Pipeline to Closed-Loop Learning System",
                 Inches(0.5), Inches(0.65), Inches(12), Inches(0.85),
                 font_size=24, bold=True, color=WHITE)

    # Current state (left)
    add_rect(slide, Inches(0.5), Inches(1.6), Inches(4.5), Inches(5.4), CARD_BG,
             line_color=ACCENT_CYAN, line_width=Pt(1.5))
    add_text_box(slide, "CURRENT (Experimental)",
                 Inches(0.6), Inches(1.65), Inches(4.3), Inches(0.45),
                 font_size=13, bold=True, color=ACCENT_CYAN)

    current_items = [
        "Linear 4-stage pipeline",
        "Fixed agent execution order",
        "Single-shot optimization attempt",
        "Rollback on failure (no retry)",
        "No cross-file learning",
        "LLM called once per agent per file",
    ]
    for i, item in enumerate(current_items):
        y = Inches(2.2) + i * Inches(0.72)
        add_rect(slide, Inches(0.7), y + Inches(0.14), Inches(0.08), Inches(0.08), ACCENT_CYAN)
        add_text_box(slide, item, Inches(0.9), y,
                     Inches(3.9), Inches(0.65), font_size=13, color=LIGHT_GREY)

    # Arrow
    add_text_box(slide, ">>", Inches(5.1), Inches(4.0),
                 Inches(0.8), Inches(0.8), font_size=28, bold=True,
                 color=hex2rgb("AA66FF"), align=PP_ALIGN.CENTER)

    # Proposed (right)
    add_rect(slide, Inches(6.1), Inches(1.6), Inches(6.7), Inches(5.4), CARD_BG,
             line_color=hex2rgb("AA66FF"), line_width=Pt(1.5))
    add_text_box(slide, "PROPOSED (Next Phase)",
                 Inches(6.2), Inches(1.65), Inches(6.5), Inches(0.45),
                 font_size=13, bold=True, color=hex2rgb("AA66FF"))

    proposed = [
        (hex2rgb("AA66FF"), "Orchestrator Agent",
         "Dynamically schedules agents based on file type, risk profile, and confidence scores."),
        (ACCENT_GREEN,      "Self-Refinement Loop",
         "On verification failure, the failure reason is fed back to the optimizer for a second attempt before rollback."),
        (hex2rgb("FFAA00"), "Feedback Memory",
         "Tracks which transformation types reliably pass verification across files, adjusting confidence thresholds over time."),
        (ACCENT_CYAN,       "Parallel Agent Execution",
         "Verification and Security agents run in parallel on separate threads for faster throughput."),
    ]

    for i, (color, title, desc) in enumerate(proposed):
        y = Inches(2.2) + i * Inches(1.15)
        add_rect(slide, Inches(6.2), y, Inches(0.07), Inches(0.95), color)
        add_text_box(slide, title, Inches(6.4), y + Inches(0.03),
                     Inches(6.2), Inches(0.38), font_size=13, bold=True, color=color)
        add_text_box(slide, desc, Inches(6.4), y + Inches(0.42),
                     Inches(6.2), Inches(0.55), font_size=12, color=LIGHT_GREY)

    return slide


def slide_pros_cons(prs):
    """Slide 10 — Pros & Cons"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), WHITE)

    add_text_box(slide, "EVALUATION", Inches(0.5), Inches(0.25),
                 Inches(4), Inches(0.45), font_size=11, bold=True, color=LIGHT_GREY)
    add_text_box(slide, "Strengths & Limitations",
                 Inches(0.5), Inches(0.65), Inches(12), Inches(0.85),
                 font_size=26, bold=True, color=WHITE)

    pros = [
        ("Safe by Design",        "Rollback is the default response to uncertainty — not failure."),
        ("Modular",               "Adding a new agent = one class + one registration call."),
        ("Offline-Capable",       "Rule-based fallback ensures output even without LLM."),
        ("Auditable",             "Every finding tagged: rule / heuristic / llm / cppcheck."),
        ("Formally Grounded",     "Z3 provides mathematical rigor no pure-LLM tool can match."),
        ("Security-Aware",        "Optimization and security audits are coupled, not separate."),
    ]

    cons = [
        ("LLM Latency",           "Each pipeline run adds seconds when Qwen is online."),
        ("33% Pass Rate (Phase 2)","Verification bar is high — optimizer needs smarter transforms."),
        ("Z3 Scope Limited",      "SMT verifier handles only simple arithmetic, not pointer logic."),
        ("C/C++ Only",            "Rule-based and parser layers are language-specific."),
        ("Heuristic Noise",       "Taint flow & signed/unsigned heuristics can produce false positives."),
        ("No Cross-File Memory",  "Current system has no feedback loop between files (proposed fix)."),
    ]

    # Pros column
    add_rect(slide, Inches(0.5), Inches(1.55), Inches(6.1), Inches(0.5), ACCENT_GREEN)
    add_text_box(slide, "  STRENGTHS", Inches(0.5), Inches(1.6),
                 Inches(6.1), Inches(0.42), font_size=14, bold=True,
                 color=BG_DARK)

    for i, (title, desc) in enumerate(pros):
        y = Inches(2.15) + i * Inches(0.84)
        add_rect(slide, Inches(0.5), y, Inches(6.1), Inches(0.75), CARD_BG,
                 line_color=ACCENT_GREEN, line_width=Pt(0.75))
        add_rect(slide, Inches(0.5), y, Inches(0.06), Inches(0.75), ACCENT_GREEN)
        add_text_box(slide, title, Inches(0.65), y + Inches(0.02),
                     Inches(5.8), Inches(0.3), font_size=13, bold=True, color=ACCENT_GREEN)
        add_text_box(slide, desc, Inches(0.65), y + Inches(0.34),
                     Inches(5.8), Inches(0.35), font_size=11.5, color=LIGHT_GREY)

    # Cons column
    add_rect(slide, Inches(6.9), Inches(1.55), Inches(5.9), Inches(0.5), ACCENT_RED)
    add_text_box(slide, "  LIMITATIONS", Inches(6.9), Inches(1.6),
                 Inches(5.9), Inches(0.42), font_size=14, bold=True,
                 color=WHITE)

    for i, (title, desc) in enumerate(cons):
        y = Inches(2.15) + i * Inches(0.84)
        add_rect(slide, Inches(6.9), y, Inches(5.9), Inches(0.75), CARD_BG,
                 line_color=ACCENT_RED, line_width=Pt(0.75))
        add_rect(slide, Inches(6.9), y, Inches(0.06), Inches(0.75), ACCENT_RED)
        add_text_box(slide, title, Inches(7.05), y + Inches(0.02),
                     Inches(5.65), Inches(0.3), font_size=13, bold=True, color=ACCENT_RED)
        add_text_box(slide, desc, Inches(7.05), y + Inches(0.34),
                     Inches(5.65), Inches(0.35), font_size=11.5, color=LIGHT_GREY)

    return slide


def slide_results(prs):
    """Slide 11 — Phase 2 Results"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), hex2rgb("FFAA00"))

    add_text_box(slide, "RESULTS — PHASE 2", Inches(0.5), Inches(0.25),
                 Inches(6), Inches(0.45), font_size=11, bold=True, color=hex2rgb("FFAA00"))
    add_text_box(slide, "4-Stage Pipeline Benchmark Run",
                 Inches(0.5), Inches(0.65), Inches(12), Inches(0.85),
                 font_size=26, bold=True, color=WHITE)

    # Metric cards row
    metrics = [
        ("3",    "Files Processed",          ACCENT_CYAN),
        ("33%",  "Pass Rate",                ACCENT_GREEN),
        ("2",    "Rollbacks (Safety Net)",    hex2rgb("FFAA00")),
        ("0",    "New Vulns Introduced",      ACCENT_RED),
    ]

    for i, (val, label, color) in enumerate(metrics):
        x = Inches(0.5) + i * Inches(3.22)
        add_rect(slide, x, Inches(1.65), Inches(3.0), Inches(1.5), CARD_BG,
                 line_color=color, line_width=Pt(2))
        add_text_box(slide, val, x, Inches(1.7),
                     Inches(3.0), Inches(0.9), font_size=36, bold=True,
                     color=color, align=PP_ALIGN.CENTER)
        add_text_box(slide, label, x, Inches(2.55),
                     Inches(3.0), Inches(0.55), font_size=12,
                     color=LIGHT_GREY, align=PP_ALIGN.CENTER)

    # Per-file table
    add_rect(slide, Inches(0.5), Inches(3.35), Inches(12.3), Inches(0.45), CARD_BG,
             line_color=ACCENT_CYAN, line_width=Pt(1))
    headers = ["File", "Category", "Status", "Findings", "Sec Risk", "Time"]
    col_xs  = [Inches(0.6), Inches(2.6), Inches(6.3), Inches(8.3), Inches(10.0), Inches(11.5)]
    col_ws  = [Inches(2.0), Inches(3.7), Inches(2.0), Inches(1.7),  Inches(1.5),  Inches(1.2)]
    for j, (h, cx, cw) in enumerate(zip(headers, col_xs, col_ws)):
        add_text_box(slide, h, cx, Inches(3.38), cw, Inches(0.38),
                     font_size=12, bold=True, color=ACCENT_CYAN)

    rows = [
        ("TC01_uninit.cpp",    "Uninitialized variable",  "ROLLBACK", "1 (H:1)", "none", "5.9s"),
        ("TC11_bufferof.cpp",  "Buffer overflow — loop",  "SUCCESS",  "2 (H:2)", "none", "1.8s"),
        ("TC16_uaf.cpp",       "Use-after-free",          "ROLLBACK", "0 (H:0)", "high", "1.8s"),
    ]

    row_colors = {
        "SUCCESS": ACCENT_GREEN,
        "ROLLBACK": hex2rgb("FFAA00"),
    }

    for k, row in enumerate(rows):
        y = Inches(3.9) + k * Inches(0.85)
        bg = CARD_BG if k % 2 == 0 else BG_DARK
        add_rect(slide, Inches(0.5), y, Inches(12.3), Inches(0.75), bg)
        for j, (cell, cx, cw) in enumerate(zip(row, col_xs, col_ws)):
            color = LIGHT_GREY
            if j == 2:
                color = row_colors.get(cell, LIGHT_GREY)
            add_text_box(slide, cell, cx, y + Inches(0.08), cw, Inches(0.6),
                         font_size=12, color=color)

    # Interpretation note
    add_rect(slide, Inches(0.5), Inches(6.55), Inches(12.3), Inches(0.65), CARD_BG,
             line_color=hex2rgb("FFAA00"), line_width=Pt(1))
    add_text_box(slide,
                 "   Rollbacks are a FEATURE, not a failure — they prove the safety net works. "
                 "0 new vulns introduced confirms the security guard is effective.",
                 Inches(0.6), Inches(6.6), Inches(12.0), Inches(0.58),
                 font_size=12, color=hex2rgb("FFAA00"), italic=True)

    return slide


def slide_closing(prs):
    """Slide 12 — Closing"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    # Full-width cyan top bar
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.12), ACCENT_CYAN)
    add_rect(slide, Inches(0), Inches(7.38), SLIDE_W, Inches(0.12), ACCENT_CYAN)

    add_text_box(slide,
                 "Traditional compilers optimize for speed.\nSecurity scanners scan in isolation.\n"
                 "LLMs generate code but can't prove it's correct.\n\n"
                 "This system is the first to combine all three —\noptimizing code, formally verifying it didn't break,\n"
                 "and ensuring the optimization introduced no new exploit.",
                 Inches(1.0), Inches(0.7), Inches(11.3), Inches(4.5),
                 font_size=22, color=WHITE, align=PP_ALIGN.CENTER)

    add_rect(slide, Inches(2.5), Inches(4.8), Inches(8.3), Inches(1.2), CARD_BG,
             line_color=ACCENT_CYAN, line_width=Pt(2))
    add_text_box(slide,
                 "The foundation for AI that doesn't just write code faster —\nit writes code safely.",
                 Inches(2.5), Inches(4.85), Inches(8.3), Inches(1.1),
                 font_size=18, bold=True, color=ACCENT_CYAN, align=PP_ALIGN.CENTER)

    add_text_box(slide, "DeepCompile  |  Semester 4  |  2026",
                 Inches(0), Inches(6.9), SLIDE_W, Inches(0.4),
                 font_size=12, color=MID_GREY, align=PP_ALIGN.CENTER)

    return slide


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H

    slide_title(prs)
    slide_problem(prs)
    slide_what_is_it(prs)
    slide_architecture(prs)
    slide_analysis(prs)
    slide_verification(prs)
    slide_security(prs)
    slide_novelty(prs)
    slide_proposed_arch(prs)
    slide_pros_cons(prs)
    slide_results(prs)
    slide_closing(prs)

    out = "E:/SEM 4/CD_Refined/AI_Compiler_Optimization_Pitch.pptx"
    prs.save(out)
    print(f"Saved: {out}  ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
