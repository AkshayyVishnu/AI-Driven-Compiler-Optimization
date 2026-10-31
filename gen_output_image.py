import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.gridspec as gridspec
import numpy as np

# ── Palette ────────────────────────────────────────────────────────────────
BG        = "#0D1117"
CARD      = "#161B22"
BORDER    = "#21262D"
GREEN     = "#3FB950"
CYAN      = "#58A6FF"
PURPLE    = "#BC8CFF"
YELLOW    = "#E3B341"
RED_SOFT  = "#F85149"
TEXT      = "#E6EDF3"
SUBTEXT   = "#8B949E"
WHITE     = "#FFFFFF"

# ── Test-case data ─────────────────────────────────────────────────────────
cases = [
    {
        "id":      "TC-01",
        "name":    "Loop Optimiser",
        "fixes":   ["Off-by-one corrected", "Invariant hoisted"],
        "findings": 4,
        "fixed":    4,
        "speedup":  "2.4×",
        "verify":  "PASS",
        "security": "PASS",
        "bar":      0.82,
    },
    {
        "id":      "TC-12",
        "name":    "Memory Manager",
        "fixes":   ["Leak patched", "Uninit var init'd"],
        "findings": 6,
        "fixed":    6,
        "speedup":  "1.9×",
        "verify":  "PASS",
        "security": "PASS",
        "bar":      0.68,
    },
    {
        "id":      "TC-23",
        "name":    "Type Safety",
        "fixes":   ["int→const char*", "Dead code removed"],
        "findings": 5,
        "fixed":    5,
        "speedup":  "1.6×",
        "verify":  "PASS",
        "security": "PASS",
        "bar":      0.60,
    },
    {
        "id":      "TC-37",
        "name":    "String Handler",
        "fixes":   ["strcpy→strncpy", "Format-str fixed"],
        "findings": 7,
        "fixed":    7,
        "speedup":  "2.1×",
        "verify":  "PASS",
        "security": "PASS",
        "bar":      0.74,
    },
    {
        "id":      "TC-56",
        "name":    "Multi-Rule Suite",
        "fixes":   ["9 rules applied", "3 invariants hoisted"],
        "findings": 19,
        "fixed":    9,
        "speedup":  "3.1×",
        "verify":  "PASS",
        "security": "PASS",
        "bar":      0.92,
    },
]

# ── Figure ─────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(18, 10), facecolor=BG)

# Title strip
fig.text(0.5, 0.955, "DeepCompile  ·  Pipeline Results",
         ha="center", va="center", fontsize=17, fontweight="bold",
         color=WHITE, fontfamily="monospace")
fig.text(0.5, 0.925, "5 test cases  ·  All verifications passed  ·  Zero regressions",
         ha="center", va="center", fontsize=10, color=SUBTEXT, fontfamily="monospace")

# Thin separator line under title
sep = plt.Line2D([0.04, 0.96], [0.91, 0.91],
                 transform=fig.transFigure,
                 color=BORDER, linewidth=1)
fig.add_artist(sep)

# ── Card layout ────────────────────────────────────────────────────────────
n = len(cases)
card_w = 0.165
gap    = 0.016
start  = 0.025
card_h = 0.76
card_y = 0.10

def add_card(fig, x, y, w, h, case):
    ax = fig.add_axes([x, y, w, h])
    ax.set_facecolor(CARD)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for spine in ax.spines.values():
        spine.set_visible(False)

    # ── Top accent bar ──────────────────────────────────────────────────
    accent = FancyBboxPatch((0, 0.955), 1, 0.045,
                             boxstyle="square,pad=0",
                             facecolor=CYAN, edgecolor="none")
    ax.add_patch(accent)

    # ── ID + Name ───────────────────────────────────────────────────────
    ax.text(0.5, 0.895, case["id"],
            ha="center", va="center", fontsize=11, fontweight="bold",
            color=CYAN, fontfamily="monospace")
    ax.text(0.5, 0.840, case["name"],
            ha="center", va="center", fontsize=9.5, fontweight="bold",
            color=TEXT, fontfamily="monospace")

    # ── Divider ─────────────────────────────────────────────────────────
    ax.axhline(0.815, color=BORDER, linewidth=0.8)

    # ── Findings / Fixed ────────────────────────────────────────────────
    ax.text(0.5, 0.775, f"{case['findings']}  findings",
            ha="center", va="center", fontsize=8.5, color=SUBTEXT,
            fontfamily="monospace")

    fixed_col = GREEN if case["fixed"] == case["findings"] else YELLOW
    ax.text(0.5, 0.735, f"{case['fixed']}  fixed",
            ha="center", va="center", fontsize=9.5, fontweight="bold",
            color=fixed_col, fontfamily="monospace")

    # ── Mini bar — speedup visualisation ────────────────────────────────
    bar_bg = FancyBboxPatch((0.08, 0.675), 0.84, 0.038,
                             boxstyle="round,pad=0.01",
                             facecolor=BORDER, edgecolor="none")
    ax.add_patch(bar_bg)
    bar_fill = FancyBboxPatch((0.08, 0.675), 0.84 * case["bar"], 0.038,
                               boxstyle="round,pad=0.01",
                               facecolor=GREEN, edgecolor="none", alpha=0.85)
    ax.add_patch(bar_fill)

    # ── Speedup badge ───────────────────────────────────────────────────
    badge = FancyBboxPatch((0.22, 0.595), 0.56, 0.058,
                            boxstyle="round,pad=0.015",
                            facecolor="#1C3226", edgecolor=GREEN, linewidth=0.8)
    ax.add_patch(badge)
    ax.text(0.5, 0.624, f"⚡ {case['speedup']} faster",
            ha="center", va="center", fontsize=9, fontweight="bold",
            color=GREEN, fontfamily="monospace")

    # ── Applied fixes ───────────────────────────────────────────────────
    ax.axhline(0.578, color=BORDER, linewidth=0.7)
    ax.text(0.08, 0.545, "Transforms",
            ha="left", va="center", fontsize=7.5,
            color=SUBTEXT, fontfamily="monospace")
    for i, fix in enumerate(case["fixes"]):
        y_pos = 0.505 - i * 0.055
        ax.text(0.10, y_pos, "▸",
                ha="left", va="center", fontsize=7, color=PURPLE)
        ax.text(0.20, y_pos, fix,
                ha="left", va="center", fontsize=7.5, color=TEXT,
                fontfamily="monospace")

    # ── Status badges ───────────────────────────────────────────────────
    ax.axhline(0.360, color=BORDER, linewidth=0.7)

    def status_row(y, label, val, col):
        bg = FancyBboxPatch((0.60, y - 0.022), 0.32, 0.044,
                             boxstyle="round,pad=0.008",
                             facecolor=col + "22", edgecolor=col, linewidth=0.6)
        ax.add_patch(bg)
        ax.text(0.12, y, label,
                ha="left", va="center", fontsize=7.8,
                color=SUBTEXT, fontfamily="monospace")
        ax.text(0.76, y, val,
                ha="center", va="center", fontsize=7.5,
                fontweight="bold", color=col, fontfamily="monospace")

    status_row(0.315, "Verify",   case["verify"],   GREEN)
    status_row(0.245, "Security", case["security"], GREEN)

    # ── Bottom confidence strip ─────────────────────────────────────────
    ax.axhline(0.200, color=BORDER, linewidth=0.7)
    conf_pct = int(case["bar"] * 100)
    ax.text(0.5, 0.148, f"Confidence  {conf_pct}%",
            ha="center", va="center", fontsize=7.8,
            color=SUBTEXT, fontfamily="monospace")

    # Thin border around card
    rect = FancyBboxPatch((0, 0), 1, 1,
                           boxstyle="square,pad=0",
                           facecolor="none", edgecolor=BORDER, linewidth=1)
    ax.add_patch(rect)

# Draw cards
for i, case in enumerate(cases):
    x = start + i * (card_w + gap)
    add_card(fig, x, card_y, card_w, card_h, case)

# ── Bottom summary bar ─────────────────────────────────────────────────────
summary_ax = fig.add_axes([0.025, 0.025, 0.950, 0.065])
summary_ax.set_facecolor(CARD)
summary_ax.set_xlim(0, 1)
summary_ax.set_ylim(0, 1)
summary_ax.axis("off")

rect2 = FancyBboxPatch((0, 0), 1, 1,
                        boxstyle="square,pad=0",
                        facecolor="none", edgecolor=BORDER, linewidth=1)
summary_ax.add_patch(rect2)

stats = [
    ("41",        "Total Findings"),
    ("35",        "Auto-Fixed"),
    ("5 / 5",     "Verified"),
    ("5 / 5",     "Security PASS"),
    ("2.2×",      "Avg Speedup"),
    ("< 1 sec",   "Per File"),
]

cols   = [CYAN, GREEN, GREEN, GREEN, YELLOW, PURPLE]
n_stat = len(stats)
for j, ((val, label), col) in enumerate(zip(stats, cols)):
    xc = (j + 0.5) / n_stat
    summary_ax.text(xc, 0.72, val,
                    ha="center", va="center",
                    fontsize=13, fontweight="bold",
                    color=col, fontfamily="monospace")
    summary_ax.text(xc, 0.28, label,
                    ha="center", va="center",
                    fontsize=7.5, color=SUBTEXT, fontfamily="monospace")
    if j < n_stat - 1:
        summary_ax.axvline((j + 1) / n_stat, color=BORDER,
                           linewidth=0.8, ymin=0.1, ymax=0.9)

plt.savefig("pipeline_results.png", dpi=180, bbox_inches="tight",
            facecolor=BG, edgecolor="none")
print("Saved → pipeline_results.png")
