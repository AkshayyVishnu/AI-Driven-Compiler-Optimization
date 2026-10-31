"""
Architecture-only PPT — DeepCompile
All slides are pure diagrams: boxes, arrows, labels. No bullet slides.
Output: Architecture_Diagrams.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from lxml import etree

# ── Palette ─────────────────────────────────────────────────────────────────
BG        = RGBColor(0x0D, 0x1B, 0x2A)
CYAN      = RGBColor(0x00, 0xD4, 0xFF)
GREEN     = RGBColor(0x39, 0xFF, 0x14)
RED       = RGBColor(0xFF, 0x45, 0x5E)
AMBER     = RGBColor(0xFF, 0xAA, 0x00)
PURPLE    = RGBColor(0xAA, 0x66, 0xFF)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
LGREY     = RGBColor(0xCC, 0xD6, 0xE0)
MGREY     = RGBColor(0x55, 0x66, 0x77)
CARD      = RGBColor(0x14, 0x2A, 0x3E)
DARK2     = RGBColor(0x0A, 0x14, 0x1E)

W = Inches(13.33)
H = Inches(7.5)

# ── Primitive helpers ────────────────────────────────────────────────────────

def bg(slide):
    f = slide.background.fill; f.solid(); f.fore_color.rgb = BG

def rect(slide, x, y, w, h, fill, line=None, lw=Pt(1.2), radius=False):
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    shp = slide.shapes.add_shape(1, x, y, w, h)
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line:
        shp.line.color.rgb = line; shp.line.width = lw
    else:
        shp.line.fill.background()
    return shp

def label(slide, text, x, y, w, h, sz=13, bold=False,
          color=WHITE, align=PP_ALIGN.LEFT, italic=False):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = align
    r = p.add_run(); r.text = text
    r.font.size = Pt(sz); r.font.bold = bold
    r.font.italic = italic; r.font.color.rgb = color
    return tb

def arrow_h(slide, x, y, length, color=CYAN, tip=True):
    """Horizontal right arrow as a thin rect + triangle tip."""
    rect(slide, x, y + Inches(0.06), length - Inches(0.18), Inches(0.06), color)
    if tip:
        # draw a small right-pointing triangle using a textbox "▶"
        label(slide, "▶", x + length - Inches(0.22), y,
              Inches(0.22), Inches(0.18), sz=10, color=color, align=PP_ALIGN.CENTER)

def arrow_v(slide, x, y, length, color=CYAN):
    """Vertical down arrow."""
    rect(slide, x + Inches(0.04), y, Inches(0.06), length - Inches(0.16), color)
    label(slide, "▼", x, y + length - Inches(0.2),
          Inches(0.14), Inches(0.2), sz=10, color=color, align=PP_ALIGN.CENTER)

def box(slide, x, y, w, h, fill, border, text, tsz=13, tbold=False,
        tcolor=WHITE, talign=PP_ALIGN.CENTER, lw=Pt(1.5), sub=None, subcolor=None):
    """Bordered box with centered label and optional sub-label."""
    rect(slide, x, y, w, h, fill, line=border, lw=lw)
    # vertically centre text
    ty = y + (h - Inches(0.3)) / 2 - (Inches(0.15) if sub else 0)
    label(slide, text, x + Inches(0.05), ty, w - Inches(0.1), Inches(0.3),
          sz=tsz, bold=tbold, color=tcolor, align=talign)
    if sub:
        label(slide, sub, x + Inches(0.05), ty + Inches(0.3),
              w - Inches(0.1), Inches(0.25),
              sz=10, color=subcolor or LGREY, align=talign, italic=True)

def header(slide, tag, title, tag_color=CYAN):
    rect(slide, 0, 0, W, Inches(0.07), tag_color)
    label(slide, tag,   Inches(0.4), Inches(0.12), Inches(4), Inches(0.38),
          sz=10, bold=True, color=tag_color)
    label(slide, title, Inches(0.4), Inches(0.44), Inches(12.5), Inches(0.65),
          sz=26, bold=True, color=WHITE)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Title
# ═══════════════════════════════════════════════════════════════════════════
def s_title(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6]); bg(sl)
    rect(sl, 0, 0, W, Inches(0.1), CYAN)
    rect(sl, 0, Inches(7.4), W, Inches(0.1), CYAN)
    rect(sl, Inches(0.35), Inches(1.3), Inches(0.08), Inches(4.5), CYAN)
    label(sl, "DeepCompile",
          Inches(0.6), Inches(1.5), Inches(12.2), Inches(1.1),
          sz=36, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    label(sl, "Architecture & Pipeline Diagrams",
          Inches(0.6), Inches(2.7), Inches(12.2), Inches(0.7),
          sz=24, color=CYAN, align=PP_ALIGN.CENTER)
    label(sl, "System Architecture  |  Agent Layer Diagrams  |  Full Pipeline Flow  |  Rollback Mechanism",
          Inches(0.6), Inches(3.55), Inches(12.2), Inches(0.5),
          sz=14, color=LGREY, align=PP_ALIGN.CENTER, italic=True)

    # mini diagram preview
    colors = [CYAN, GREEN, AMBER, RED]
    names  = ["Analysis", "Optimization", "Verification", "Security"]
    bw = Inches(2.5); gap = Inches(0.35); sx = Inches(1.55); sy = Inches(4.5)
    for i, (c, n) in enumerate(zip(colors, names)):
        bx = sx + i*(bw+gap)
        box(sl, bx, sy, bw, Inches(0.85), CARD, c, n, tsz=14, tbold=True, tcolor=c)
        if i < 3:
            arrow_h(sl, bx+bw, sy+Inches(0.38), gap+Inches(0.02), color=MGREY)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Full 3-Tier System Architecture
# ═══════════════════════════════════════════════════════════════════════════
def s_system_arch(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6]); bg(sl)
    header(sl, "SYSTEM ARCHITECTURE", "Three-Tier Architecture Overview", CYAN)

    # ── Tier 1: Pipeline ─────────────────────────────────
    rect(sl, Inches(0.3), Inches(1.2), Inches(12.73), Inches(1.8), DARK2, line=CYAN, lw=Pt(1.5))
    label(sl, "TIER 1 — PIPELINE LAYER", Inches(0.45), Inches(1.25),
          Inches(3), Inches(0.3), sz=10, bold=True, color=CYAN)

    agents = [("01  ANALYSIS",     CYAN),
              ("02  OPTIMIZATION", GREEN),
              ("03  VERIFICATION", AMBER),
              ("04  SECURITY",     RED)]
    bw = Inches(2.75); gap = Inches(0.3); sx = Inches(0.5)
    for i, (name, c) in enumerate(agents):
        bx = sx + i*(bw+gap)
        box(sl, bx, Inches(1.55), bw, Inches(1.05),
            CARD, c, name, tsz=13, tbold=True, tcolor=c, lw=Pt(2))
        if i < 3:
            arrow_h(sl, bx+bw, Inches(1.99), gap+Inches(0.01), color=MGREY)

    # ── Tier 2: Framework ────────────────────────────────
    rect(sl, Inches(0.3), Inches(3.15), Inches(12.73), Inches(1.8), DARK2, line=PURPLE, lw=Pt(1.5))
    label(sl, "TIER 2 — AGENT FRAMEWORK LAYER",
          Inches(0.45), Inches(3.2), Inches(5), Inches(0.3),
          sz=10, bold=True, color=PURPLE)

    fw_items = [
        ("ContextManager", "Versioned shared blackboard\nThread-safe RLock\nRollback support", PURPLE),
        ("AgentRegistry",  "Agent discovery & routing\nLifecycle management\nstart_all / stop_all", CYAN),
        ("Message Protocol","JSON typed messages\nREQUEST / RESPONSE / NOTIFY\nPriority queues HIGH/MED/LOW", AMBER),
        ("BaseAgent",      "Abstract base class\nPriorityQueue(100)\nLifecycle state machine", GREEN),
    ]
    fw_w = Inches(3.0); fw_gap = Inches(0.18); fsx = Inches(0.5)
    for i, (title, desc, c) in enumerate(fw_items):
        bx = fsx + i*(fw_w+fw_gap)
        rect(sl, bx, Inches(3.55), fw_w, Inches(1.25), CARD, line=c, lw=Pt(1.2))
        label(sl, title, bx+Inches(0.1), Inches(3.6), fw_w-Inches(0.2), Inches(0.32),
              sz=13, bold=True, color=c, align=PP_ALIGN.CENTER)
        label(sl, desc,  bx+Inches(0.1), Inches(3.94), fw_w-Inches(0.2), Inches(0.8),
              sz=10, color=LGREY, align=PP_ALIGN.CENTER)

    # ── Tier 3: LLM ──────────────────────────────────────
    rect(sl, Inches(0.3), Inches(5.1), Inches(12.73), Inches(1.9), DARK2, line=GREEN, lw=Pt(1.5))
    label(sl, "TIER 3 — LLM & REASONING LAYER",
          Inches(0.45), Inches(5.15), Inches(5), Inches(0.3),
          sz=10, bold=True, color=GREEN)

    llm_items = [
        ("LLMClient\n(Ollama / Qwen 2.5 Coder 7B)",
         "localhost:11434\nTemp=0.1  MaxTokens=2048\nOffline stub fallback", CYAN, Inches(3.8)),
        ("GeminiLLMClient\n(Google Gemini 2.5 Flash)",
         "Cloud API backend\nRequires GEMINI_API_KEY\nSame stub fallback", GREEN, Inches(3.8)),
        ("CoT Validator",
         "Extract JSON from LLM output\nValidate: reasoning_steps +\nconclusion + confidence ∈[0,1]", AMBER, Inches(4.3)),
        ("Prompt Templates",
         "AnalysisPrompt\nOptimizationPrompt\nVerificationPrompt / SecurityPrompt", RED, Inches(3.8)),
    ]
    llm_gaps = [Inches(0.0), Inches(4.0), Inches(8.0), Inches(8.0)+Inches(4.5)]
    widths   = [Inches(3.8), Inches(3.8), Inches(4.3), Inches(3.3)]
    sxl = Inches(0.5)
    positions = [Inches(0.5), Inches(4.45), Inches(8.4), Inches(12.73)-Inches(3.3)-Inches(0.2)]
    for i, (title, desc, c, ww) in enumerate(llm_items):
        bx = positions[i]
        ww2 = widths[i]
        rect(sl, bx, Inches(5.5), ww2, Inches(1.35), CARD, line=c, lw=Pt(1.2))
        label(sl, title, bx+Inches(0.1), Inches(5.55), ww2-Inches(0.2), Inches(0.42),
              sz=12, bold=True, color=c, align=PP_ALIGN.CENTER)
        label(sl, desc,  bx+Inches(0.1), Inches(5.97), ww2-Inches(0.2), Inches(0.82),
              sz=9.5, color=LGREY, align=PP_ALIGN.CENTER)

    # vertical connectors between tiers
    for bx_off in [Inches(2.15), Inches(5.2), Inches(8.25), Inches(11.3)]:
        arrow_v(sl, bx_off, Inches(3.0), Inches(0.2), color=MGREY)
        arrow_v(sl, bx_off, Inches(4.95), Inches(0.2), color=MGREY)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 3 — ContextManager: Versioning & Rollback
# ═══════════════════════════════════════════════════════════════════════════
def s_context(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6]); bg(sl)
    header(sl, "AGENT FRAMEWORK", "ContextManager — Versioned State & Rollback", PURPLE)

    # Schema box (left)
    rect(sl, Inches(0.3), Inches(1.25), Inches(3.8), Inches(5.75), CARD, line=PURPLE, lw=Pt(1.5))
    label(sl, "Initial Schema", Inches(0.4), Inches(1.3), Inches(3.6), Inches(0.35),
          sz=12, bold=True, color=PURPLE, align=PP_ALIGN.CENTER)
    schema = [
        ("original_code",          "null"),
        ("source_file",            "null"),
        ("analysis_results",       "{}"),
        ("optimization_suggestions","[]"),
        ("verification_status",    "{}"),
        ("security_findings",      "[]"),
        ("metadata",               "{}"),
    ]
    for i, (k, v) in enumerate(schema):
        y = Inches(1.75) + i * Inches(0.68)
        rect(sl, Inches(0.4), y, Inches(3.6), Inches(0.58), BG, line=PURPLE, lw=Pt(0.6))
        label(sl, k, Inches(0.52), y+Inches(0.05), Inches(2.4), Inches(0.48),
              sz=11, color=CYAN, bold=True)
        label(sl, v, Inches(2.95), y+Inches(0.05), Inches(0.9), Inches(0.48),
              sz=11, color=LGREY)

    # API box (centre-left)
    rect(sl, Inches(4.3), Inches(1.25), Inches(3.2), Inches(5.75), CARD, line=CYAN, lw=Pt(1.5))
    label(sl, "Public API", Inches(4.4), Inches(1.3), Inches(3.0), Inches(0.35),
          sz=12, bold=True, color=CYAN, align=PP_ALIGN.CENTER)
    api_items = [
        ("set(key, value)",       "dot-notation nested write"),
        ("get(key, default)",     "dot-notation read + deepcopy"),
        ("append(key, value)",    "append to list key"),
        ("update(dict)",          "batch set multiple keys"),
        ("rollback(version_id)",  "restore prior snapshot"),
        ("get_version_history()", "list of version timestamps"),
        ("clear()",               "reset to empty schema"),
        ("to_json()",             "export full context"),
    ]
    for i, (method, desc) in enumerate(api_items):
        y = Inches(1.75) + i * Inches(0.625)
        label(sl, method, Inches(4.4), y, Inches(3.0), Inches(0.28),
              sz=11, bold=True, color=GREEN)
        label(sl, desc,   Inches(4.4), y+Inches(0.27), Inches(3.0), Inches(0.28),
              sz=9.5, color=LGREY)

    # Versioning timeline (right)
    rect(sl, Inches(7.7), Inches(1.25), Inches(5.3), Inches(5.75), CARD, line=AMBER, lw=Pt(1.5))
    label(sl, "Versioning & Rollback Flow", Inches(7.8), Inches(1.3),
          Inches(5.1), Inches(0.35), sz=12, bold=True, color=AMBER, align=PP_ALIGN.CENTER)

    versions = [
        ("v0", "initial clear()",          BG, AMBER),
        ("v1", "analysis_results written", BG, CYAN),
        ("v2", "optimization_suggestions", BG, GREEN),
        ("v3", "verification_status",      BG, AMBER),
        ("v4", "security_findings",        BG, RED),
    ]
    vx = Inches(8.0); vw = Inches(4.7); vh = Inches(0.58)
    for i, (vid, desc, fill, c) in enumerate(versions):
        vy = Inches(1.78) + i * (vh + Inches(0.12))
        rect(sl, vx, vy, vw, vh, fill, line=c, lw=Pt(1.5))
        label(sl, vid,  vx+Inches(0.1), vy+Inches(0.05), Inches(0.5), vh-Inches(0.1),
              sz=13, bold=True, color=c, align=PP_ALIGN.CENTER)
        label(sl, desc, vx+Inches(0.65), vy+Inches(0.05), vw-Inches(0.75), vh-Inches(0.1),
              sz=12, color=LGREY)
        if i < len(versions)-1:
            arrow_v(sl, vx + vw/2 - Inches(0.03), vy+vh, Inches(0.12), color=MGREY)

    # rollback arrow
    rect(sl, Inches(12.6), Inches(1.78), Inches(0.12), Inches(3.92), RED)
    label(sl, "rollback()", Inches(12.2), Inches(3.6), Inches(0.9), Inches(0.5),
          sz=10, bold=True, color=RED, align=PP_ALIGN.CENTER)

    # v5 restored
    vy5 = Inches(1.78) + 5 * (vh + Inches(0.12))
    rect(sl, vx, vy5, vw, vh, BG, line=PURPLE, lw=Pt(2))
    label(sl, "v5", vx+Inches(0.1), vy5+Inches(0.05), Inches(0.5), vh-Inches(0.1),
          sz=13, bold=True, color=PURPLE, align=PP_ALIGN.CENTER)
    label(sl, "restored from v3  [new snapshot]",
          vx+Inches(0.65), vy5+Inches(0.05), vw-Inches(0.75), vh-Inches(0.1),
          sz=12, color=PURPLE)
    label(sl, "max_versions=10  (FIFO eviction)",
          vx, vy5+Inches(0.72), vw, Inches(0.3),
          sz=10, color=MGREY, align=PP_ALIGN.CENTER, italic=True)

    # thread safety note
    rect(sl, Inches(7.7), Inches(7.05), Inches(5.3), Inches(0.35), BG, line=PURPLE, lw=Pt(0.8))
    label(sl, "All operations protected by threading.RLock()  |  deepcopy on every version snapshot",
          Inches(7.8), Inches(7.07), Inches(5.1), Inches(0.3),
          sz=10, color=PURPLE, align=PP_ALIGN.CENTER, italic=True)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Message Protocol Flow
# ═══════════════════════════════════════════════════════════════════════════
def s_message(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6]); bg(sl)
    header(sl, "AGENT FRAMEWORK", "Message Protocol — Types, Priority & Routing Flow", CYAN)

    # ── Message anatomy (top-left) ────────────────────────
    rect(sl, Inches(0.3), Inches(1.25), Inches(4.5), Inches(3.5), CARD, line=CYAN, lw=Pt(1.5))
    label(sl, "Message Anatomy", Inches(0.4), Inches(1.3), Inches(4.3), Inches(0.35),
          sz=12, bold=True, color=CYAN, align=PP_ALIGN.CENTER)
    fields = [
        ("message_id",     "UUID4 — unique per message"),
        ("sender_id",      "e.g. 'pipeline', 'analysis_1'"),
        ("receiver_id",    "e.g. 'optimization_1'"),
        ("message_type",   "REQUEST | RESPONSE | NOTIFICATION"),
        ("payload",        "Dict[str, Any] — task data"),
        ("priority",       "HIGH=0  MEDIUM=1  LOW=2"),
        ("timestamp",      "ISO-8601 UTC string"),
        ("correlation_id", "links response to request"),
    ]
    for i, (k, v) in enumerate(fields):
        y = Inches(1.75) + i * Inches(0.355)
        label(sl, k+":", Inches(0.45), y, Inches(1.5), Inches(0.33),
              sz=10.5, bold=True, color=CYAN)
        label(sl, v, Inches(1.98), y, Inches(2.7), Inches(0.33), sz=10.5, color=LGREY)

    # ── Priority Queue ──────────────────────────────────
    rect(sl, Inches(0.3), Inches(4.9), Inches(4.5), Inches(2.1), CARD, line=AMBER, lw=Pt(1.5))
    label(sl, "Priority Queue (per agent)", Inches(0.4), Inches(4.95),
          Inches(4.3), Inches(0.35), sz=12, bold=True, color=AMBER, align=PP_ALIGN.CENTER)
    pq_rows = [
        ("HIGH   = 0", "Security alerts, critical requests",  RED),
        ("MEDIUM = 1", "Standard agent-to-agent requests",    AMBER),
        ("LOW    = 2", "Notifications, non-critical updates", CYAN),
    ]
    for i, (pri, desc, c) in enumerate(pq_rows):
        y = Inches(5.4) + i * Inches(0.5)
        rect(sl, Inches(0.45), y, Inches(4.2), Inches(0.4), BG, line=c, lw=Pt(0.8))
        label(sl, pri,  Inches(0.55), y+Inches(0.05), Inches(1.1), Inches(0.3),
              sz=11, bold=True, color=c)
        label(sl, desc, Inches(1.65), y+Inches(0.05), Inches(2.8), Inches(0.3),
              sz=10, color=LGREY)

    # ── Routing Flow (right) ──────────────────────────────
    rect(sl, Inches(5.1), Inches(1.25), Inches(7.95), Inches(5.75), CARD, line=PURPLE, lw=Pt(1.5))
    label(sl, "Message Routing Flow", Inches(5.2), Inches(1.3),
          Inches(7.75), Inches(0.35), sz=12, bold=True, color=PURPLE, align=PP_ALIGN.CENTER)

    # nodes
    nodes = [
        (Inches(5.35), Inches(1.85), Inches(2.3), Inches(0.65), "Agent A\n(e.g. analysis_1)", CYAN,  CARD),
        (Inches(8.9),  Inches(1.85), Inches(2.3), Inches(0.65), "AgentRegistry\n(router)",    PURPLE,CARD),
        (Inches(5.35), Inches(3.2),  Inches(2.3), Inches(0.65), "Agent B\n(e.g. optimization_1)", GREEN, CARD),
        (Inches(5.35), Inches(4.55), Inches(2.3), Inches(0.65), "PriorityQueue\n(maxsize=100)", AMBER, CARD),
        (Inches(5.35), Inches(5.9),  Inches(2.3), Inches(0.65), "process(payload)\n→ result",  RED,   CARD),
    ]
    for nx, ny, nw, nh, ntxt, nc, nfill in nodes:
        rect(sl, nx, ny, nw, nh, nfill, line=nc, lw=Pt(1.5))
        label(sl, ntxt, nx+Inches(0.05), ny+Inches(0.05), nw-Inches(0.1), nh-Inches(0.1),
              sz=11, bold=True, color=nc, align=PP_ALIGN.CENTER)

    # step labels and arrows
    steps = [
        # (from_x, from_y, direction, length, text, color)
        (Inches(7.65), Inches(2.13), "h", Inches(1.25), "① send_message()", CYAN),
        (Inches(9.05), Inches(2.5),  "v", Inches(0.73), "② route_message()", PURPLE),
        (Inches(7.65), Inches(3.5),  "h_left", Inches(1.25), "③ receive_message()", GREEN),
        (Inches(6.5),  Inches(3.85), "v", Inches(0.72), "④ queue.put(priority,msg)", AMBER),
        (Inches(6.5),  Inches(5.2),  "v", Inches(0.72), "⑤ process(payload)", RED),
        (Inches(7.65), Inches(6.17), "h", Inches(2.55), "⑥ send RESPONSE back", GREEN),
    ]

    arrow_h(sl, Inches(7.65), Inches(2.13), Inches(1.25), color=CYAN)
    label(sl, "① send_message()", Inches(7.7), Inches(1.95), Inches(1.2), Inches(0.22),
          sz=9, color=CYAN, align=PP_ALIGN.CENTER)

    arrow_v(sl, Inches(9.0), Inches(2.5), Inches(0.73), color=PURPLE)
    label(sl, "② route_message()", Inches(9.15), Inches(2.7), Inches(1.5), Inches(0.25),
          sz=9, color=PURPLE)

    # horizontal arrow going left: draw rect + left tip
    rect(sl, Inches(7.65), Inches(3.5), Inches(1.25), Inches(0.06), GREEN)
    label(sl, "◀", Inches(7.6), Inches(3.42), Inches(0.2), Inches(0.2), sz=10, color=GREEN)
    label(sl, "③ receive_message()", Inches(7.68), Inches(3.3), Inches(1.2), Inches(0.22),
          sz=9, color=GREEN, align=PP_ALIGN.CENTER)

    arrow_v(sl, Inches(6.45), Inches(3.85), Inches(0.72), color=AMBER)
    label(sl, "④ queue.put(priority, msg)", Inches(6.6), Inches(4.05), Inches(2.2), Inches(0.25),
          sz=9, color=AMBER)

    arrow_v(sl, Inches(6.45), Inches(5.2), Inches(0.72), color=RED)
    label(sl, "⑤ process(payload)", Inches(6.6), Inches(5.38), Inches(2.0), Inches(0.25),
          sz=9, color=RED)

    arrow_h(sl, Inches(7.65), Inches(6.17), Inches(2.55), color=GREEN)
    label(sl, "⑥ RESPONSE with correlation_id", Inches(7.7), Inches(6.0), Inches(2.5), Inches(0.22),
          sz=9, color=GREEN)

    # note
    rect(sl, Inches(5.1), Inches(7.05), Inches(7.95), Inches(0.35), BG, line=MGREY, lw=Pt(0.6))
    label(sl, "Pipeline mode: process() called directly (no thread queue). Messages logged via MessageLogger (observer only).",
          Inches(5.2), Inches(7.07), Inches(7.75), Inches(0.3),
          sz=9.5, color=MGREY, italic=True, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 5 — Analysis Agent Layers
# ═══════════════════════════════════════════════════════════════════════════
def s_analysis(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6]); bg(sl)
    header(sl, "AGENT 01 — ANALYSIS", "Hybrid Bug Detection: Rule-Based + LLM Layers", CYAN)

    # Input
    box(sl, Inches(0.3), Inches(1.25), Inches(2.0), Inches(0.65),
        CARD, CYAN, "INPUT\nC++ source_code", tsz=11, tbold=True, tcolor=CYAN)
    arrow_h(sl, Inches(2.3), Inches(1.52), Inches(0.5), color=CYAN)

    # CodeParser
    rect(sl, Inches(2.8), Inches(1.25), Inches(3.0), Inches(0.65), CARD, line=CYAN, lw=Pt(1.5))
    label(sl, "CodeParser", Inches(2.85), Inches(1.3), Inches(2.9), Inches(0.3),
          sz=12, bold=True, color=CYAN, align=PP_ALIGN.CENTER)
    label(sl, "parse_string() → ParseResult", Inches(2.85), Inches(1.56), Inches(2.9), Inches(0.28),
          sz=9.5, color=LGREY, align=PP_ALIGN.CENTER)

    # ParseResult outputs
    parse_fields = ["functions[]", "loops[]", "uninitialized_vars[]",
                    "array_accesses[]", "malloc_calls[]", "free_calls[]",
                    "max_loop_depth", "has_nested_loops"]
    rect(sl, Inches(6.0), Inches(1.05), Inches(2.4), Inches(1.3), CARD, line=MGREY, lw=Pt(0.8))
    label(sl, "ParseResult", Inches(6.05), Inches(1.08), Inches(2.3), Inches(0.28),
          sz=10, bold=True, color=MGREY, align=PP_ALIGN.CENTER)
    for i, pf in enumerate(parse_fields):
        col = i // 4; row = i % 4
        label(sl, "• "+pf, Inches(6.1)+col*Inches(1.15), Inches(1.37)+row*Inches(0.22),
              Inches(1.1), Inches(0.22), sz=8.5, color=LGREY)
    arrow_h(sl, Inches(5.8), Inches(1.57), Inches(0.2), color=MGREY)

    arrow_v(sl, Inches(4.25), Inches(1.9), Inches(0.4), color=CYAN)

    # Two main branches side by side
    # Layer 1: Rule-Based
    rect(sl, Inches(0.3), Inches(2.4), Inches(5.8), Inches(3.4), CARD, line=CYAN, lw=Pt(2))
    label(sl, "LAYER 1 — Rule-Based Analysis  (always active, offline-capable)",
          Inches(0.4), Inches(2.45), Inches(5.6), Inches(0.35),
          sz=12, bold=True, color=CYAN, align=PP_ALIGN.CENTER)

    rules = [
        ("Uninit Variable",      "Declared but not assigned before use",   "high",   CYAN),
        ("Buffer Overflow",      "Variable-index array access in loop",     "high",   RED),
        ("Off-by-One",           "for(; i <= N ;) → should be i < N",     "high",   RED),
        ("O(n²) Complexity",     "Nested loops detected",                   "medium", AMBER),
        ("Memory Leak",          "malloc_calls > free_calls count",         "high",   RED),
        ("Division by Zero",     "Divisor variable assigned 0 in scope",   "high",   RED),
    ]
    for i, (name, desc, sev, c) in enumerate(rules):
        ry = Inches(2.87) + i * Inches(0.47)
        rect(sl, Inches(0.4), ry, Inches(5.6), Inches(0.4), BG, line=c, lw=Pt(0.6))
        label(sl, name, Inches(0.5), ry+Inches(0.04), Inches(1.7), Inches(0.32),
              sz=10.5, bold=True, color=c)
        label(sl, desc, Inches(2.2), ry+Inches(0.04), Inches(2.7), Inches(0.32),
              sz=10, color=LGREY)
        sev_c = RED if sev=="high" else AMBER
        label(sl, sev, Inches(5.05), ry+Inches(0.04), Inches(0.8), Inches(0.32),
              sz=9, color=sev_c, bold=True, align=PP_ALIGN.CENTER)

    # Layer 2: LLM
    rect(sl, Inches(6.3), Inches(2.4), Inches(6.7), Inches(3.4), CARD, line=AMBER, lw=Pt(2))
    label(sl, "LAYER 2 — LLM Enrichment  (Qwen 2.5 Coder 7B)",
          Inches(6.4), Inches(2.45), Inches(6.5), Inches(0.35),
          sz=12, bold=True, color=AMBER, align=PP_ALIGN.CENTER)

    # Prompt box
    rect(sl, Inches(6.4), Inches(2.87), Inches(2.9), Inches(1.35), BG, line=AMBER, lw=Pt(0.8))
    label(sl, "AnalysisPromptTemplate.build()", Inches(6.5), Inches(2.9),
          Inches(2.7), Inches(0.28), sz=10, bold=True, color=AMBER)
    prompt_lines = ["• source_code",
                    "• file_path",
                    "• parse_result.to_summary()",
                    "• system: expert C/C++ bug detector"]
    for i, pl in enumerate(prompt_lines):
        label(sl, pl, Inches(6.5), Inches(3.2)+i*Inches(0.24), Inches(2.7), Inches(0.23),
              sz=9.5, color=LGREY)

    arrow_h(sl, Inches(9.3), Inches(3.42), Inches(0.35), color=AMBER)

    # CoT Validator box
    rect(sl, Inches(9.65), Inches(2.87), Inches(3.2), Inches(1.35), BG, line=PURPLE, lw=Pt(0.8))
    label(sl, "CoT Validator", Inches(9.75), Inches(2.9),
          Inches(3.0), Inches(0.28), sz=10, bold=True, color=PURPLE, align=PP_ALIGN.CENTER)
    cot_lines = ["Extract JSON from ```json...```",
                 "Validate: reasoning_steps (list)",
                 "Validate: confidence ∈ [0.0, 1.0]",
                 "On fail → is_valid=False → [] findings"]
    for i, cl in enumerate(cot_lines):
        label(sl, cl, Inches(9.75), Inches(3.2)+i*Inches(0.24), Inches(3.0), Inches(0.23),
              sz=9.5, color=LGREY)

    # fallback
    rect(sl, Inches(6.4), Inches(4.3), Inches(6.5), Inches(0.45), BG, line=MGREY, lw=Pt(0.8))
    label(sl, "If LLM offline → stub returns confidence=0.5, findings=[]  (rule-based only)",
          Inches(6.5), Inches(4.35), Inches(6.3), Inches(0.35),
          sz=10, color=MGREY, italic=True, align=PP_ALIGN.CENTER)

    arrow_v(sl, Inches(4.3), Inches(5.8), Inches(0.28), color=CYAN)
    arrow_v(sl, Inches(9.6), Inches(5.8), Inches(0.28), color=AMBER)

    # Merge box
    rect(sl, Inches(2.5), Inches(6.05), Inches(8.3), Inches(0.7), CARD, line=PURPLE, lw=Pt(2))
    label(sl, "MERGE & DEDUPLICATE  |  Key: (finding_type, line_number)  |  Rule findings take precedence",
          Inches(2.55), Inches(6.2), Inches(8.2), Inches(0.38),
          sz=12, bold=True, color=PURPLE, align=PP_ALIGN.CENTER)

    arrow_h(sl, Inches(10.8), Inches(6.38), Inches(0.5), color=GREEN)
    box(sl, Inches(11.3), Inches(6.05), Inches(1.8), Inches(0.7),
        CARD, GREEN, "OUTPUT\nall_findings[]", tsz=11, tbold=True, tcolor=GREEN)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Optimization Agent Layers
# ═══════════════════════════════════════════════════════════════════════════
def s_optimization(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6]); bg(sl)
    header(sl, "AGENT 02 — OPTIMIZATION", "Rule-Based Fixes + LLM Transformation + Selection Logic", GREEN)

    # Input
    box(sl, Inches(0.3), Inches(1.28), Inches(2.2), Inches(0.75),
        CARD, GREEN, "INPUT\nsource_code\n+ analysis_report", tsz=10, tbold=True, tcolor=GREEN)
    arrow_h(sl, Inches(2.5), Inches(1.62), Inches(0.4), color=GREEN)

    # Layer 1 Rule box
    rect(sl, Inches(2.9), Inches(1.1), Inches(4.5), Inches(3.6), CARD, line=GREEN, lw=Pt(2))
    label(sl, "LAYER 1 — Rule-Based Fixes  (offline-capable)",
          Inches(3.0), Inches(1.15), Inches(4.3), Inches(0.35),
          sz=12, bold=True, color=GREEN, align=PP_ALIGN.CENTER)

    rule_fixes = [
        ("off_by_one_fix",       "for(; i <= N ;)",  "→  for(; i < N ;)",   GREEN),
        ("initialize_variable",  "int x;",           "→  int x = 0;",        CYAN),
        ("loop_bound_correction","Validate bounds",   "Regex pattern replace", AMBER),
    ]
    for i, (name, before, after, c) in enumerate(rule_fixes):
        ry = Inches(1.6) + i * Inches(0.88)
        rect(sl, Inches(3.0), ry, Inches(4.2), Inches(0.75), BG, line=c, lw=Pt(0.8))
        label(sl, name, Inches(3.1), ry+Inches(0.04), Inches(4.0), Inches(0.28),
              sz=11, bold=True, color=c)
        label(sl, before + "  " + after, Inches(3.1), ry+Inches(0.35),
              Inches(4.0), Inches(0.28), sz=10, color=LGREY)

    # process per finding note
    rect(sl, Inches(3.0), Inches(4.3), Inches(4.2), Inches(0.32), BG, line=MGREY, lw=Pt(0.6))
    label(sl, "Iterates over all_findings[] from analysis_report",
          Inches(3.05), Inches(4.33), Inches(4.1), Inches(0.26),
          sz=9, color=MGREY, italic=True, align=PP_ALIGN.CENTER)

    # Layer 2 LLM box
    rect(sl, Inches(7.6), Inches(1.1), Inches(5.45), Inches(3.6), CARD, line=AMBER, lw=Pt(2))
    label(sl, "LAYER 2 — LLM Transformation  (Qwen 2.5 Coder)",
          Inches(7.7), Inches(1.15), Inches(5.25), Inches(0.35),
          sz=12, bold=True, color=AMBER, align=PP_ALIGN.CENTER)

    llm_steps = [
        ("Prompt Build", "OptimizationPromptTemplate.build(src, analysis_report)"),
        ("LLM Call",     "generate() → raw JSON with 'optimized_code' field"),
        ("CoT Validate", "Extracts: optimized_code, reasoning_steps, confidence"),
        ("Fallback",     "If invalid CoT → return None (use rule-based code)"),
    ]
    for i, (step, desc) in enumerate(llm_steps):
        sy = Inches(1.6) + i * Inches(0.82)
        c = [AMBER, GREEN, PURPLE, MGREY][i]
        rect(sl, Inches(7.7), sy, Inches(5.25), Inches(0.7), BG, line=c, lw=Pt(0.8))
        label(sl, step, Inches(7.8), sy+Inches(0.05), Inches(1.3), Inches(0.28),
              sz=11, bold=True, color=c)
        label(sl, desc, Inches(9.15), sy+Inches(0.05), Inches(3.65), Inches(0.28),
              sz=10, color=LGREY)
        if i < 3:
            arrow_v(sl, Inches(10.3), sy+Inches(0.7), Inches(0.12), color=MGREY)

    # Selection Logic
    rect(sl, Inches(2.9), Inches(4.78), Inches(10.15), Inches(1.0), CARD, line=PURPLE, lw=Pt(2))
    label(sl, "SELECTION LOGIC", Inches(3.0), Inches(4.83),
          Inches(10.0), Inches(0.32), sz=12, bold=True, color=PURPLE, align=PP_ALIGN.CENTER)
    label(sl, "if  llm_code is valid  AND  llm_code != original_code  →  final_code = llm_code   |   transforms = rule_transforms + llm_transforms",
          Inches(3.0), Inches(5.15), Inches(9.9), Inches(0.25),
          sz=10, color=GREEN, align=PP_ALIGN.CENTER)
    label(sl, "else  →  final_code = rule_code   |   transforms = rule_transforms only",
          Inches(3.0), Inches(5.42), Inches(9.9), Inches(0.25),
          sz=10, color=LGREY, align=PP_ALIGN.CENTER)

    # Post-processing
    post = [
        (Inches(2.9),  "Generate Unified Diff\ndifflib.unified_diff()", GREEN),
        (Inches(6.05), "Save OPT_*.cpp\nMicroBenchmarks/Generated_optimisation/", CYAN),
        (Inches(9.2),  "Store in Context\nctx.set('optimization_suggestions')", PURPLE),
    ]
    for bx, txt, c in post:
        rect(sl, bx, Inches(5.95), Inches(2.95), Inches(0.85), CARD, line=c, lw=Pt(1.5))
        label(sl, txt, bx+Inches(0.1), Inches(6.0), Inches(2.75), Inches(0.75),
              sz=11, bold=True, color=c, align=PP_ALIGN.CENTER)

    arrow_v(sl, Inches(4.25), Inches(4.63), Inches(0.18), color=PURPLE)
    arrow_v(sl, Inches(10.3), Inches(4.63), Inches(0.18), color=PURPLE)
    arrow_v(sl, Inches(7.5),  Inches(5.78), Inches(0.2),  color=GREEN)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 7 — Verification Agent: 4 Layers
# ═══════════════════════════════════════════════════════════════════════════
def s_verification(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6]); bg(sl)
    header(sl, "AGENT 03 — VERIFICATION", "4-Layer Correctness Guarantee with Rollback", AMBER)

    # Input bar
    rect(sl, Inches(0.3), Inches(1.25), Inches(12.73), Inches(0.52), CARD, line=AMBER, lw=Pt(1.2))
    label(sl, "INPUT:  original_code  +  optimized_code  +  file_path",
          Inches(0.5), Inches(1.32), Inches(12.5), Inches(0.38),
          sz=13, bold=True, color=AMBER, align=PP_ALIGN.CENTER)

    layers = [
        {
            "tag": "L1", "color": CYAN,
            "title": "DifferentialTester",
            "sub": "diff_tester.py",
            "steps": [
                "Compile original.cpp  →  original.exe   (g++ -O0 -w, 10s timeout)",
                "Compile optimized.cpp →  optimized.exe",
                "Run both with empty stdin (10s timeout each)",
                "Compare stdout byte-for-byte",
            ],
            "pass": "stdout_orig == stdout_opt",
            "fail": "ROLLBACK",
        },
        {
            "tag": "L2", "color": GREEN,
            "title": "Z3 SMT Verifier",
            "sub": "z3_verifier.py",
            "steps": [
                "Extract single `return <expr>;` from each version",
                "Find all identifiers → declare as Z3 Int variables",
                "Safe AST eval both expressions in Z3 context",
                "Add constraint: expr1 != expr2  →  Solver.check()",
            ],
            "pass": "UNSAT → PROVEN_EQUIVALENT",
            "fail": "SAT → COUNTEREXAMPLE → ROLLBACK",
        },
        {
            "tag": "L3", "color": AMBER,
            "title": "PerfBenchmarker",
            "sub": "perf_benchmarker.py",
            "steps": [
                "Compile both with -O2 and timing wrappers",
                "Run 5 iterations per version",
                "Compute mean runtime (ms) and speedup ratio",
                "Report: faster / same / slower",
            ],
            "pass": "No significant regression",
            "fail": "FAIL (warn only, no rollback)",
        },
        {
            "tag": "L4", "color": PURPLE,
            "title": "LLM Reasoning",
            "sub": "VerificationPromptTemplate",
            "steps": [
                "Send both code versions to Qwen 2.5 Coder",
                "'Are these semantically equivalent?'",
                "CoT validated → extracts verdict field",
                "Advisory: informs but can also trigger rollback",
            ],
            "pass": "verdict == 'PASS'",
            "fail": "verdict == 'FAIL' → ROLLBACK",
        },
    ]

    lw2 = Inches(3.08); gap2 = Inches(0.14); sy = Inches(1.9)
    for i, L in enumerate(layers):
        lx = Inches(0.3) + i*(lw2+gap2)
        c = L["color"]
        rect(sl, lx, sy, lw2, Inches(4.55), CARD, line=c, lw=Pt(2))
        # Tag badge
        rect(sl, lx, sy, Inches(0.55), Inches(0.48), c)
        label(sl, L["tag"], lx, sy, Inches(0.55), Inches(0.48),
              sz=14, bold=True, color=BG, align=PP_ALIGN.CENTER)
        label(sl, L["title"], lx+Inches(0.6), sy+Inches(0.04),
              lw2-Inches(0.7), Inches(0.28), sz=12, bold=True, color=c)
        label(sl, L["sub"],   lx+Inches(0.6), sy+Inches(0.3),
              lw2-Inches(0.7), Inches(0.2), sz=9, color=MGREY, italic=True)

        for j, step in enumerate(L["steps"]):
            sy2 = sy + Inches(0.62) + j*Inches(0.62)
            rect(sl, lx+Inches(0.1), sy2, lw2-Inches(0.2), Inches(0.52), BG, line=c, lw=Pt(0.5))
            label(sl, step, lx+Inches(0.18), sy2+Inches(0.04),
                  lw2-Inches(0.36), Inches(0.44), sz=9.5, color=LGREY)

        # pass / fail
        py = sy + Inches(3.12)
        rect(sl, lx+Inches(0.1), py, lw2-Inches(0.2), Inches(0.48), BG, line=GREEN, lw=Pt(0.8))
        label(sl, "✓  "+L["pass"], lx+Inches(0.18), py+Inches(0.06),
              lw2-Inches(0.36), Inches(0.38), sz=9, color=GREEN)
        fy = py + Inches(0.56)
        fc = RED if "ROLLBACK" in L["fail"] else AMBER
        rect(sl, lx+Inches(0.1), fy, lw2-Inches(0.2), Inches(0.48), BG, line=fc, lw=Pt(0.8))
        label(sl, "✗  "+L["fail"], lx+Inches(0.18), fy+Inches(0.06),
              lw2-Inches(0.36), Inches(0.38), sz=9, color=fc)

        if i < 3:
            arrow_h(sl, lx+lw2, sy+Inches(2.2), gap2+Inches(0.02), color=MGREY)

    # Verdict bar
    rect(sl, Inches(0.3), Inches(6.6), Inches(12.73), Inches(0.75), CARD, line=RED, lw=Pt(2))
    label(sl, "VERDICT ENGINE:  ",
          Inches(0.5), Inches(6.73), Inches(1.6), Inches(0.38), sz=12, bold=True, color=RED)
    label(sl, "DiffFail OR Z3-Counterexample OR LLM-FAIL  →  context.rollback()  →  status = ROLLBACK     |     All pass  →  status = PASS",
          Inches(2.1), Inches(6.73), Inches(10.8), Inches(0.38),
          sz=12, color=WHITE)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 8 — Security Agent: 4 Layers
# ═══════════════════════════════════════════════════════════════════════════
def s_security(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6]); bg(sl)
    header(sl, "AGENT 04 — SECURITY", "4-Layer Vulnerability Guard + New-Vuln Differential", RED)

    rect(sl, Inches(0.3), Inches(1.25), Inches(12.73), Inches(0.52), CARD, line=RED, lw=Pt(1.2))
    label(sl, "INPUT:  original_code  +  optimized_code  (both scanned independently, then compared)",
          Inches(0.5), Inches(1.32), Inches(12.5), Inches(0.38),
          sz=13, bold=True, color=RED, align=PP_ALIGN.CENTER)

    # L1 Rules
    rect(sl, Inches(0.3), Inches(1.9), Inches(3.25), Inches(3.9), CARD, line=RED, lw=Pt(2))
    rect(sl, Inches(0.3), Inches(1.9), Inches(0.55), Inches(0.48), RED)
    label(sl, "L1", Inches(0.3), Inches(1.9), Inches(0.55), Inches(0.48),
          sz=14, bold=True, color=BG, align=PP_ALIGN.CENTER)
    label(sl, "Rule-Based Scan", Inches(0.9), Inches(1.94),
          Inches(2.55), Inches(0.28), sz=12, bold=True, color=RED)
    label(sl, "confidence = 0.90", Inches(0.9), Inches(2.2),
          Inches(2.55), Inches(0.2), sz=9, color=MGREY, italic=True)
    rules_l1 = [
        ("gets()",      "CWE-242  unconditionally unsafe"),
        ("scanf %s",    "CWE-134  unbounded string read"),
        ("strcpy()",    "CWE-676  unbounded copy"),
        ("strcat()",    "CWE-676  unbounded append"),
        ("sprintf()",   "CWE-676  unbounded format output"),
        ("printf(var)", "CWE-134  format string attack"),
        ("use-after-free","CWE-416  free/delete + dereference"),
    ]
    for i, (fn, cwe) in enumerate(rules_l1):
        ry = Inches(2.45) + i * Inches(0.48)
        rect(sl, Inches(0.4), ry, Inches(3.05), Inches(0.4), BG, line=RED, lw=Pt(0.5))
        label(sl, fn,  Inches(0.5), ry+Inches(0.04), Inches(1.1), Inches(0.32),
              sz=10.5, bold=True, color=RED)
        label(sl, cwe, Inches(1.62), ry+Inches(0.04), Inches(1.7), Inches(0.32),
              sz=9.5, color=LGREY)

    # L2 Heuristics
    rect(sl, Inches(3.7), Inches(1.9), Inches(3.5), Inches(3.9), CARD, line=AMBER, lw=Pt(2))
    rect(sl, Inches(3.7), Inches(1.9), Inches(0.55), Inches(0.48), AMBER)
    label(sl, "L2", Inches(3.7), Inches(1.9), Inches(0.55), Inches(0.48),
          sz=14, bold=True, color=BG, align=PP_ALIGN.CENTER)
    label(sl, "Heuristic Multi-Signal", Inches(4.3), Inches(1.94),
          Inches(2.8), Inches(0.28), sz=12, bold=True, color=AMBER)
    label(sl, "confidence 0.65–0.85  |  7 signals", Inches(4.3), Inches(2.2),
          Inches(2.8), Inches(0.2), sz=9, color=MGREY, italic=True)
    heuristics = [
        ("H1", "Taint Flow",          "0.50", "input→sink without guard  CWE-120"),
        ("H2", "Unchecked malloc",    "0.60", "malloc not NULL-checked   CWE-476"),
        ("H3", "Signed/Unsigned",     "0.60", "int as array index/size   CWE-195"),
        ("H4", "Int Overflow malloc", "0.70", "malloc(a*b) no guard      CWE-190"),
        ("H5", "Buffer Loop Write",   "0.70", "char[N] in var-bound loop CWE-121"),
        ("H6", "Recursive Buffer",    "0.60", "≥1KB local in recursion   CWE-674"),
        ("H7", "Global Thread Write", "0.60", "global var, no mutex      CWE-362"),
    ]
    for i, (hid, name, thr, desc) in enumerate(heuristics):
        hy = Inches(2.45) + i * Inches(0.48)
        rect(sl, Inches(3.8), hy, Inches(3.3), Inches(0.4), BG, line=AMBER, lw=Pt(0.5))
        label(sl, hid, Inches(3.88), hy+Inches(0.04), Inches(0.35), Inches(0.32),
              sz=10, bold=True, color=AMBER)
        label(sl, name, Inches(4.25), hy+Inches(0.04), Inches(1.3), Inches(0.32),
              sz=10, bold=True, color=WHITE)
        label(sl, ">"+thr, Inches(5.58), hy+Inches(0.04), Inches(0.4), Inches(0.32),
              sz=9, color=GREEN, bold=True)
        label(sl, desc, Inches(6.0), hy+Inches(0.04), Inches(0.85), Inches(0.32),
              sz=7.5, color=LGREY)

    # L3 LLM
    rect(sl, Inches(7.35), Inches(1.9), Inches(2.85), Inches(3.9), CARD, line=PURPLE, lw=Pt(2))
    rect(sl, Inches(7.35), Inches(1.9), Inches(0.55), Inches(0.48), PURPLE)
    label(sl, "L3", Inches(7.35), Inches(1.9), Inches(0.55), Inches(0.48),
          sz=14, bold=True, color=BG, align=PP_ALIGN.CENTER)
    label(sl, "LLM Semantic Scan", Inches(7.95), Inches(1.94),
          Inches(2.15), Inches(0.28), sz=12, bold=True, color=PURPLE)
    label(sl, "confidence capped ≤ 0.70", Inches(7.95), Inches(2.2),
          Inches(2.15), Inches(0.2), sz=9, color=MGREY, italic=True)
    l3_items = [
        "SecurityPromptTemplate.build()",
        "Pass: optimized + original + baseline_types",
        "CoT validated response",
        "Findings tagged source='llm'",
        "",
        "CRITICAL RULE:",
        "LLM alone CANNOT trigger rollback",
        "Only informs — never decides",
    ]
    for i, item in enumerate(l3_items):
        c2 = RED if item == "CRITICAL RULE:" else (LGREY if not item.startswith("LLM") else AMBER)
        b = item in ("CRITICAL RULE:",)
        label(sl, item, Inches(7.45), Inches(2.45)+i*Inches(0.42),
              Inches(2.65), Inches(0.38), sz=10, color=c2, bold=b)

    # L4 cppcheck
    rect(sl, Inches(10.35), Inches(1.9), Inches(2.65), Inches(3.9), CARD, line=GREEN, lw=Pt(2))
    rect(sl, Inches(10.35), Inches(1.9), Inches(0.55), Inches(0.48), GREEN)
    label(sl, "L4", Inches(10.35), Inches(1.9), Inches(0.55), Inches(0.48),
          sz=14, bold=True, color=BG, align=PP_ALIGN.CENTER)
    label(sl, "cppcheck", Inches(10.95), Inches(1.94),
          Inches(1.95), Inches(0.28), sz=12, bold=True, color=GREEN)
    label(sl, "confidence = 0.85  |  optional", Inches(10.95), Inches(2.2),
          Inches(1.95), Inches(0.2), sz=9, color=MGREY, italic=True)
    l4_items = [
        "Detect binary: cppcheck --version",
        "Write code to temp .cpp file",
        "Run: --xml --xml-version=2",
        "  --enable=warning,error",
        "Parse XML output",
        "Map severity:",
        "  error   → high",
        "  warning → medium",
        "  style   → low",
        "Skip gracefully if not found",
    ]
    for i, item in enumerate(l4_items):
        label(sl, item, Inches(10.45), Inches(2.45)+i*Inches(0.36),
              Inches(2.45), Inches(0.34), sz=9.5, color=LGREY)

    # New-vuln detection + rollback
    rect(sl, Inches(0.3), Inches(5.95), Inches(12.73), Inches(0.6), CARD, line=RED, lw=Pt(1.5))
    label(sl, "NEW-VULN DETECTION:  orig_types = {f['type'] for f in orig_all}   |   new_vulns = [f for f in opt_all if f['type'] not in orig_types]",
          Inches(0.5), Inches(6.08), Inches(12.5), Inches(0.35),
          sz=11, color=AMBER, align=PP_ALIGN.CENTER)

    rect(sl, Inches(0.3), Inches(6.6), Inches(12.73), Inches(0.77), CARD, line=RED, lw=Pt(2))
    label(sl, "ROLLBACK TRIGGER:  new_vuln.severity == 'high'  AND  source in ('rule','heuristic')  AND  confidence >= 0.80  →  context.rollback()",
          Inches(0.5), Inches(6.73), Inches(12.5), Inches(0.38),
          sz=12, bold=True, color=RED, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Full End-to-End Pipeline Flow
# ═══════════════════════════════════════════════════════════════════════════
def s_pipeline_flow(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6]); bg(sl)
    header(sl, "FULL PIPELINE", "End-to-End Execution Flow with Rollback Branches", WHITE)

    # ── Left column: sequential steps ────────────────────
    sx = Inches(0.3); sw = Inches(4.8)
    steps_left = [
        (Inches(1.25), "READ SOURCE FILE",  "Open .cpp file from disk\nClear ContextManager for new run", CYAN,   "pipeline"),
        (Inches(2.55), "ANALYSIS AGENT",    "Rule scan + LLM enrichment\nCtx ← analysis_results", CYAN,   "analysis_1"),
        (Inches(3.85), "OPTIMIZATION AGENT","Rule fixes + LLM transform\nSelect best code\nSave OPT_*.cpp\nCtx ← optimization_suggestions", GREEN,  "optimization_1"),
        (Inches(5.5),  "VERIFICATION AGENT","L1 DiffTest\nL2 Z3 SMT\nL3 Perf Benchmark\nL4 LLM Reasoning", AMBER, "verification_1"),
        (Inches(7.1),  "SECURITY AGENT",    "L1 Rules\nL2 Heuristics (7 signals)\nL3 LLM\nL4 cppcheck (optional)\nCompare new vs orig vulns", RED,   "security_1"),
    ]

    heights = [Inches(0.9), Inches(0.9), Inches(1.3), Inches(1.3), Inches(1.45)]
    for i, ((sy2, name, desc, c, agent), h) in enumerate(zip(steps_left, heights)):
        rect(sl, sx, sy2, sw, h, CARD, line=c, lw=Pt(2))
        rect(sl, sx, sy2, Inches(0.07), h, c)
        label(sl, f"0{i+1}  {name}", sx+Inches(0.15), sy2+Inches(0.07),
              sw-Inches(0.25), Inches(0.35), sz=13, bold=True, color=c)
        label(sl, desc, sx+Inches(0.15), sy2+Inches(0.42),
              sw-Inches(0.25), h-Inches(0.48), sz=10.5, color=LGREY)
        label(sl, agent, sx+Inches(0.15), sy2+h-Inches(0.25),
              sw-Inches(0.25), Inches(0.22), sz=8.5, color=MGREY, italic=True)
        if i < len(steps_left)-1:
            next_sy = steps_left[i+1][0]
            arrow_v(sl, sx+sw/2-Inches(0.03), sy2+h, next_sy-(sy2+h), color=MGREY)

    # ── Right column: outcome + rollback branches ──────
    rx = Inches(5.4); rw = Inches(7.6)

    # Message log sidebar
    rect(sl, rx, Inches(1.25), rw, Inches(1.25), CARD, line=MGREY, lw=Pt(1))
    label(sl, "MESSAGE LOG  (audit trail — observer only, not on critical path)",
          rx+Inches(0.15), Inches(1.3), rw-Inches(0.3), Inches(0.32),
          sz=11, bold=True, color=MGREY, align=PP_ALIGN.CENTER)
    msg_types = [
        ("REQUEST",      "pipeline → agent         (dispatch work)",       CYAN),
        ("NOTIFICATION", "agent → next agent        (handoff signal)",      AMBER),
        ("RESPONSE",     "agent → pipeline          (results + correlation)",GREEN),
    ]
    for i, (mtype, mdesc, mc) in enumerate(msg_types):
        label(sl, mtype+":", rx+Inches(0.2)+i*Inches(2.45), Inches(1.67),
              Inches(1.2), Inches(0.25), sz=10, bold=True, color=mc)
        label(sl, mdesc, rx+Inches(0.2)+i*Inches(2.45), Inches(1.9),
              Inches(2.4), Inches(0.45), sz=9, color=LGREY)

    # Verification branch
    rect(sl, rx, Inches(2.65), rw, Inches(2.1), CARD, line=AMBER, lw=Pt(1.5))
    label(sl, "VERIFICATION OUTCOME BRANCH", rx+Inches(0.15), Inches(2.7),
          rw-Inches(0.3), Inches(0.32), sz=12, bold=True, color=AMBER, align=PP_ALIGN.CENTER)

    # PASS path
    rect(sl, rx+Inches(0.2), Inches(3.1), Inches(2.8), Inches(1.45), BG, line=GREEN, lw=Pt(1))
    label(sl, "PASS", rx+Inches(0.3), Inches(3.15), Inches(2.6), Inches(0.32),
          sz=13, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
    for j, t in enumerate(["DiffTest: stdout match", "Z3: PROVEN_EQUIV", "Perf: no regression", "LLM: verdict=PASS"]):
        label(sl, "✓ "+t, rx+Inches(0.3), Inches(3.5)+j*Inches(0.25),
              Inches(2.6), Inches(0.24), sz=9.5, color=GREEN)

    # ROLLBACK path (ver)
    rect(sl, rx+Inches(3.2), Inches(3.1), Inches(4.2), Inches(1.45), BG, line=RED, lw=Pt(1))
    label(sl, "ROLLBACK", rx+Inches(3.3), Inches(3.15), Inches(4.0), Inches(0.32),
          sz=13, bold=True, color=RED, align=PP_ALIGN.CENTER)
    for j, t in enumerate(["DiffTest: stdout MISMATCH", "Z3: COUNTEREXAMPLE found", "LLM: verdict=FAIL → rollback"]):
        label(sl, "✗ "+t, rx+Inches(3.3), Inches(3.5)+j*Inches(0.3),
              Inches(4.0), Inches(0.28), sz=9.5, color=RED)
    label(sl, "context.rollback()  →  restore pre-opt snapshot",
          rx+Inches(3.3), Inches(4.35), Inches(4.0), Inches(0.25),
          sz=9, color=AMBER, bold=True)

    label(sl, "→", rx+Inches(3.05), Inches(3.73), Inches(0.2), Inches(0.3),
          sz=14, bold=True, color=MGREY, align=PP_ALIGN.CENTER)

    # Security branch
    rect(sl, rx, Inches(4.9), rw, Inches(1.8), CARD, line=RED, lw=Pt(1.5))
    label(sl, "SECURITY OUTCOME BRANCH", rx+Inches(0.15), Inches(4.95),
          rw-Inches(0.3), Inches(0.32), sz=12, bold=True, color=RED, align=PP_ALIGN.CENTER)

    rect(sl, rx+Inches(0.2), Inches(5.35), Inches(2.8), Inches(1.15), BG, line=GREEN, lw=Pt(1))
    label(sl, "PASS — no new high vulns", rx+Inches(0.3), Inches(5.4),
          Inches(2.6), Inches(0.32), sz=11, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
    label(sl, "new_vulns[] is empty\nOR confidence < 0.80\nOR source == 'llm'",
          rx+Inches(0.3), Inches(5.75), Inches(2.6), Inches(0.68), sz=9.5, color=LGREY)

    rect(sl, rx+Inches(3.2), Inches(5.35), Inches(4.2), Inches(1.15), BG, line=RED, lw=Pt(1))
    label(sl, "ROLLBACK — new high vuln", rx+Inches(3.3), Inches(5.4),
          Inches(4.0), Inches(0.32), sz=11, bold=True, color=RED, align=PP_ALIGN.CENTER)
    label(sl, "severity=high  AND  source in (rule,heuristic)\nAND  confidence >= 0.80\ncontext.rollback()",
          rx+Inches(3.3), Inches(5.75), Inches(4.0), Inches(0.68), sz=9.5, color=RED)
    label(sl, "→", rx+Inches(3.05), Inches(5.86), Inches(0.2), Inches(0.3),
          sz=14, bold=True, color=MGREY, align=PP_ALIGN.CENTER)

    # Final status bar
    rect(sl, rx, Inches(6.85), rw, Inches(0.52), CARD, line=WHITE, lw=Pt(1.5))
    label(sl, "FINAL STATUS:   success  |  rollback  |  partial   →   PipelineResult(status, analysis, optimization, verification, security)",
          rx+Inches(0.15), Inches(6.91), rw-Inches(0.3), Inches(0.38),
          sz=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 10 — Rollback Mechanism Deep Dive
# ═══════════════════════════════════════════════════════════════════════════
def s_rollback(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6]); bg(sl)
    header(sl, "ROLLBACK MECHANISM", "Context Versioning, Trigger Conditions & Recovery Path", RED)

    # Left: trigger table
    rect(sl, Inches(0.3), Inches(1.25), Inches(6.3), Inches(5.9), CARD, line=RED, lw=Pt(1.5))
    label(sl, "Rollback Trigger Conditions", Inches(0.4), Inches(1.3),
          Inches(6.1), Inches(0.38), sz=13, bold=True, color=RED, align=PP_ALIGN.CENTER)

    triggers = [
        ("Verification\nL1 DiffTest",  "stdout_original != stdout_optimized",      RED),
        ("Verification\nL2 Z3",        "Solver.check() == SAT (counterexample)",   RED),
        ("Verification\nL4 LLM",       "CoT verdict == 'FAIL'  (validated)",       RED),
        ("Security\nL1 Rule",          "New HIGH finding, confidence >= 0.90",     RED),
        ("Security\nL2 Heuristic",     "New HIGH finding, confidence >= 0.80",     RED),
        ("Security\nL3 LLM",          "CANNOT trigger rollback  (advisory only)",  MGREY),
        ("Security\nL4 cppcheck",     "NEW high error finding, confidence = 0.85", AMBER),
        ("Verification\nL3 Perf",     "FAIL only — no rollback, performance warn", AMBER),
    ]
    for i, (stage, condition, c) in enumerate(triggers):
        ty = Inches(1.75) + i * Inches(0.61)
        rect(sl, Inches(0.4), ty, Inches(6.1), Inches(0.53), BG, line=c, lw=Pt(0.6))
        label(sl, stage,     Inches(0.5),  ty+Inches(0.04), Inches(1.5), Inches(0.44),
              sz=9.5, bold=True, color=c)
        label(sl, condition, Inches(2.05), ty+Inches(0.04), Inches(4.2), Inches(0.44),
              sz=10, color=LGREY if c != MGREY else MGREY)

    # Right: rollback flow diagram
    rect(sl, Inches(6.8), Inches(1.25), Inches(6.25), Inches(5.9), CARD, line=PURPLE, lw=Pt(1.5))
    label(sl, "Rollback Execution Flow", Inches(6.9), Inches(1.3),
          Inches(6.05), Inches(0.38), sz=13, bold=True, color=PURPLE, align=PP_ALIGN.CENTER)

    flow = [
        (Inches(7.0),  Inches(1.82), "ROLLBACK TRIGGERED",  "Verification or Security agent detects failure", RED,    Inches(5.9), Inches(0.75)),
        (Inches(7.0),  Inches(2.78), "context.rollback()",  "Acquires RLock\nRestores _context from versions[-2]\nSaves restored state as new version (audit trail)", PURPLE, Inches(5.9), Inches(1.05)),
        (Inches(7.0),  Inches(4.03), "final_code reset",    "pipeline uses source_code (original)\nOptimized file remains on disk (OPT_*) for debug", AMBER,  Inches(5.9), Inches(0.85)),
        (Inches(7.0),  Inches(5.08), "PipelineResult",      "status = 'rollback'\nanalysis_report, optimization_report preserved\nverification/security report contains reason", GREEN,  Inches(5.9), Inches(0.9)),
        (Inches(7.0),  Inches(6.18), "SYSTEM READY",        "Context cleared for next file\nNo retry in current design (proposed: self-refinement)", CYAN,   Inches(5.9), Inches(0.65)),
    ]
    for bx, by, title, desc, c, bw2, bh in flow:
        rect(sl, bx, by, bw2, bh, BG, line=c, lw=Pt(1.5))
        rect(sl, bx, by, Inches(0.07), bh, c)
        label(sl, title, bx+Inches(0.15), by+Inches(0.05), bw2-Inches(0.25), Inches(0.32),
              sz=12, bold=True, color=c)
        label(sl, desc, bx+Inches(0.15), by+Inches(0.38), bw2-Inches(0.25), bh-Inches(0.44),
              sz=10, color=LGREY)

    for i in range(len(flow)-1):
        _, by, _, _, _, _, bh = flow[i]
        _, ny, _, _, _, _, _ = flow[i+1]
        arrow_v(sl, Inches(9.9), by+bh, ny-(by+bh), color=MGREY)

    # What rollback does NOT do
    rect(sl, Inches(0.3), Inches(7.2), Inches(12.73), Inches(0.18), RED)
    label(sl, "Rollback does NOT: delete OPT_* file  |  re-run optimization  |  retry with different params  (proposed fix: self-refinement loop)",
          Inches(0.4), Inches(7.21), Inches(12.5), Inches(0.15),
          sz=9, color=WHITE, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 11 — Proposed Final Architecture
# ═══════════════════════════════════════════════════════════════════════════
def s_proposed(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6]); bg(sl)
    header(sl, "PROPOSED FINAL ARCHITECTURE", "Closed-Loop Learning System with Orchestration", PURPLE)

    # Current (left mini)
    rect(sl, Inches(0.3), Inches(1.28), Inches(3.7), Inches(5.85), CARD, line=CYAN, lw=Pt(1.5))
    label(sl, "CURRENT — Linear Pipeline",
          Inches(0.4), Inches(1.33), Inches(3.5), Inches(0.35),
          sz=12, bold=True, color=CYAN, align=PP_ALIGN.CENTER)

    curr_steps = [
        ("Analysis",     CYAN),
        ("Optimization", GREEN),
        ("Verification", AMBER),
        ("Security",     RED),
        ("ROLLBACK ←",   RED),
    ]
    for i, (name, c) in enumerate(curr_steps):
        cy = Inches(1.8) + i * Inches(0.88)
        rect(sl, Inches(0.5), cy, Inches(3.3), Inches(0.68), BG, line=c, lw=Pt(1))
        label(sl, name, Inches(0.55), cy+Inches(0.15), Inches(3.2), Inches(0.35),
              sz=12, bold=True, color=c, align=PP_ALIGN.CENTER)
        if i < 4:
            arrow_v(sl, Inches(2.1), cy+Inches(0.68), Inches(0.22), color=MGREY)

    label(sl, "No retry, no learning,\nfixed order, single shot",
          Inches(0.5), Inches(6.6), Inches(3.3), Inches(0.45),
          sz=9.5, color=MGREY, align=PP_ALIGN.CENTER, italic=True)

    arrow_h(sl, Inches(4.0), Inches(4.2), Inches(0.55), color=PURPLE)
    label(sl, "EVOLVE", Inches(4.02), Inches(4.02), Inches(0.6), Inches(0.25),
          sz=9, color=PURPLE, bold=True, align=PP_ALIGN.CENTER)

    # Proposed (right large)
    rect(sl, Inches(4.7), Inches(1.28), Inches(8.35), Inches(5.85), CARD, line=PURPLE, lw=Pt(2))
    label(sl, "PROPOSED — Closed-Loop Learning System",
          Inches(4.8), Inches(1.33), Inches(8.15), Inches(0.35),
          sz=12, bold=True, color=PURPLE, align=PP_ALIGN.CENTER)

    # Orchestrator
    rect(sl, Inches(6.3), Inches(1.78), Inches(5.2), Inches(0.72), PURPLE, line=None)
    label(sl, "ORCHESTRATOR AGENT", Inches(6.3), Inches(1.82),
          Inches(5.2), Inches(0.32), sz=13, bold=True, color=BG, align=PP_ALIGN.CENTER)
    label(sl, "Classify file  |  Set strategy  |  Select agent order  |  Monitor health",
          Inches(6.3), Inches(2.1), Inches(5.2), Inches(0.32),
          sz=9.5, color=BG, align=PP_ALIGN.CENTER)

    arrow_v(sl, Inches(8.9), Inches(2.5), Inches(0.3), color=PURPLE)

    # Core pipeline row
    core_agents = [
        ("Analysis",  CYAN,  Inches(4.85)),
        ("Optim.",    GREEN, Inches(6.5)),
        ("Verify",    AMBER, Inches(8.15)),
        ("Security",  RED,   Inches(9.8)),
    ]
    for name, c, ax in core_agents:
        rect(sl, ax, Inches(2.9), Inches(1.5), Inches(0.7), CARD, line=c, lw=Pt(1.5))
        label(sl, name, ax+Inches(0.05), Inches(2.95), Inches(1.4), Inches(0.35),
              sz=11, bold=True, color=c, align=PP_ALIGN.CENTER)

    for i in range(3):
        ax = core_agents[i][2]
        arrow_h(sl, ax+Inches(1.5), Inches(3.22), Inches(0.3), color=MGREY)

    # Self-Refinement loop
    rect(sl, Inches(5.7), Inches(3.78), Inches(3.5), Inches(1.12), CARD, line=GREEN, lw=Pt(1.5))
    label(sl, "SELF-REFINEMENT LOOP", Inches(5.8), Inches(3.83),
          Inches(3.3), Inches(0.32), sz=11, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
    label(sl, "Verify FAIL → feed failure reason back to Optimizer\nAttempt #2 with failure-aware prompt\nOn 2nd FAIL → rollback",
          Inches(5.8), Inches(4.15), Inches(3.3), Inches(0.68), sz=9.5, color=LGREY)

    # arrow from verify fail down to refinement
    arrow_v(sl, Inches(8.9), Inches(3.6), Inches(0.22), color=GREEN)
    label(sl, "FAIL", Inches(9.0), Inches(3.62), Inches(0.6), Inches(0.22),
          sz=9, color=RED, bold=True)
    # arrow from refinement back up to optimization
    rect(sl, Inches(6.45), Inches(3.6), Inches(0.6), Inches(0.07), GREEN)
    label(sl, "retry ↑", Inches(5.8), Inches(3.6), Inches(0.7), Inches(0.22),
          sz=9, color=GREEN, bold=True)

    # Feedback Memory
    rect(sl, Inches(4.85), Inches(5.05), Inches(5.6), Inches(0.88), CARD, line=AMBER, lw=Pt(1.5))
    label(sl, "FEEDBACK MEMORY STORE", Inches(4.95), Inches(5.1),
          Inches(5.4), Inches(0.32), sz=11, bold=True, color=AMBER, align=PP_ALIGN.CENTER)
    label(sl, "Track per-transformation: pass_rate, failure_reasons, file_pattern_associations\n→ Orchestrator adjusts strategy  |  Optimizer skips failing patterns",
          Inches(4.95), Inches(5.42), Inches(5.4), Inches(0.45), sz=9.5, color=LGREY)

    # Parallel execution
    rect(sl, Inches(10.55), Inches(2.9), Inches(2.35), Inches(3.0), CARD, line=CYAN, lw=Pt(1.5))
    label(sl, "PARALLEL\nEXECUTION\n(proposed)", Inches(10.6), Inches(2.95),
          Inches(2.25), Inches(0.7), sz=11, bold=True, color=CYAN, align=PP_ALIGN.CENTER)
    label(sl, "Verify + Security\nrun on separate\nthreads sharing\nContextManager\n(already thread-safe)\n\n~30-40%\nspeedup",
          Inches(10.6), Inches(3.7), Inches(2.25), Inches(1.9), sz=9.5, color=LGREY, align=PP_ALIGN.CENTER)

    arrow_v(sl, Inches(8.9), Inches(5.05), Inches(0.55), color=AMBER)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    prs = Presentation()
    prs.slide_width  = W
    prs.slide_height = H

    s_title(prs)
    s_system_arch(prs)
    s_context(prs)
    s_message(prs)
    s_analysis(prs)
    s_optimization(prs)
    s_verification(prs)
    s_security(prs)
    s_pipeline_flow(prs)
    s_rollback(prs)
    s_proposed(prs)

    out = "E:/SEM 4/CD_Refined/Architecture_Diagrams.pptx"
    prs.save(out)
    print(f"Saved: {out}  ({len(prs.slides)} slides)")

if __name__ == "__main__":
    main()
