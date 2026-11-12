#!/usr/bin/env python3
"""
Generate the research workflow diagram as a vector PDF (+ PNG preview).

Requires only numpy-free matplotlib and the system Noto Sans CJK SC font.
The diagram is deliberately drawn by hand so the layout, color coding and
node wording stay under our control (Graphviz / D2 are not installed here).
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


HERE = os.path.dirname(os.path.abspath(__file__))

NOTO_SANS = os.path.join(HERE, "fonts", "NotoSansCJKsc-Regular.otf")
NOTO_SANS_BOLD = os.path.join(HERE, "fonts", "NotoSansCJKsc-Bold.otf")

for path in (NOTO_SANS, NOTO_SANS_BOLD):
    font_manager.fontManager.addfont(path)

FONT = "Noto Sans CJK SC"

MAIN = "#1F4E79"    # deep blue
ACCENT = "#2A9D8F"  # teal / data processing
WARN = "#C1663A"    # orange / diagnostics & judgment
GRAY = "#5A6472"
MAIN_LIGHT = "#E9EFF6"
ACCENT_LIGHT = "#EAF5F3"
WARN_LIGHT = "#F9EEE8"

plt.rcParams.update({
    "font.family": FONT,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


PAD_Y = 0.10
TITLE_GAP = 0.08
DETAIL_LINE_GAP = 0.10


def text_extent(ax, text, fontsize, fontweight="normal", linespacing="normal"):
    t = ax.text(0, 0, text, fontsize=fontsize, fontweight=fontweight,
                linespacing=linespacing)
    renderer = ax.figure.canvas.get_renderer()
    bb = t.get_window_extent(renderer=renderer)
    inv = ax.transData.inverted()
    (x0, y0), (x1, y1) = inv.transform([(bb.x0, bb.y0), (bb.x1, bb.y1)])
    t.remove()
    return x1 - x0, y1 - y0


def detail_metrics(ax, detail, detail_size):
    lines = detail.split("\n") if detail else []
    heights = [text_extent(ax, line, detail_size, "normal")[1]
               for line in lines]
    total = sum(heights) + DETAIL_LINE_GAP * max(0, len(lines) - 1)
    return lines, heights, total


def node_metrics(ax, title, detail, title_size, detail_size):
    _, title_h = text_extent(ax, title, title_size, "bold")
    _, _, detail_h = detail_metrics(ax, detail, detail_size)
    if detail:
        h = title_h + TITLE_GAP + detail_h + 2.0 * PAD_Y
    else:
        h = title_h + 2.0 * PAD_Y
    return title_h, detail_h, h


def draw_node(ax, cx, y_top, w, h, title, detail, edge, fill="white",
              title_size=10.0, detail_size=8.6, lw=1.15, ls="-", title_color=None):
    title_h, detail_h, auto_h = node_metrics(ax, title, detail, title_size,
                                             detail_size)
    if h is None:
        h = auto_h
    x0, y0 = cx - w / 2.0, y_top - h
    box = FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.10",
        linewidth=lw, edgecolor=edge, facecolor=fill, linestyle=ls, zorder=3,
    )
    ax.add_patch(box)
    tc = title_color if title_color is not None else edge
    content_h = title_h + (TITLE_GAP + detail_h if detail else 0.0)
    top_pad = (h - content_h) / 2.0
    if detail:
        lines, heights, _ = detail_metrics(ax, detail, detail_size)
        title_top = y_top - top_pad
        title_y = title_top - title_h / 2.0
        ax.text(cx, title_y, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold", color=tc, zorder=4)
        line_top = title_top - title_h - TITLE_GAP
        for line, line_h in zip(lines, heights):
            ax.text(cx, line_top - line_h / 2.0, line, ha="center", va="center",
                    fontsize=detail_size, color=GRAY, linespacing="normal", zorder=4)
            line_top -= line_h + DETAIL_LINE_GAP
    else:
        ax.text(cx, y_top - h / 2.0, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold", color=tc, zorder=4)
    return (x0, y0, x0 + w, y0 + h)


def arrow(ax, p0, p1, color, lw=1.05, ls="-", style="-|>", ms=9):
    a = FancyArrowPatch(
        p0, p1, arrowstyle=style, mutation_scale=ms,
        linewidth=lw, color=color, linestyle=ls, zorder=2,
        shrinkA=1.0, shrinkB=1.0,
    )
    ax.add_patch(a)


def main():
    fig = plt.figure(figsize=(6.6, 6.3))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 11.0)
    ax.set_ylim(0, 10.5)
    ax.axis("off")

    xA, xB, xS = 1.85, 5.5, 9.15
    col_w = 3.15
    row_gap = 0.45

    a_rows = [
        ("USDA 季度供需平衡表", "玉米 · Feed Grains Yearbook 表4"),
        ("提取季度观测", "EndingStocks · TotalUse"),
        ("营销年度汇总", "$AnnualUse_t = \\sum^4_{j=1} TotalUse_{t,j}$\n营销年度自 9 月开始"),
        ("构造库存变量", "$SUR_t = \\frac{Endingstocks_t}{AnnualUse_t}$\n滞后一期 SUR$_{t-1}$"),
    ]

    b_rows = [
        ("CME 连续合约", "日度结算价"),
        ("对数收益率", "$r_{d,t}=ln P_{d,t}-ln P_{d-1,t}$"),
        ("换月异常识别与处理", "异常收益置零"),
        ("季度已实现波动率", "$RV_t =\\sqrt{\\sum_{d \\in t} r_d^2}$\n有效季度筛选"),
    ]

    row_h = []
    for a, b in zip(a_rows, b_rows):
        _, _, ha = node_metrics(ax, a[0], a[1], 10.0, 8.6)
        _, _, hb = node_metrics(ax, b[0], b[1], 10.0, 8.6)
        row_h.append(max(ha, hb))

    row_top = [10.0]
    for i in range(3):
        row_top.append(row_top[-1] - row_h[i] - row_gap)

    rect_a = []
    rect_b = []
    for i in range(4):
        ra = draw_node(ax, xA, row_top[i], col_w, row_h[i],
                       a_rows[i][0], a_rows[i][1], ACCENT)
        rb = draw_node(ax, xB, row_top[i], col_w, row_h[i],
                       b_rows[i][0], b_rows[i][1], ACCENT)
        rect_a.append(ra)
        rect_b.append(rb)
    for i in range(3):
        arrow(ax, (xA, rect_a[i][1]), (xA, rect_a[i + 1][3]), ACCENT)
        arrow(ax, (xB, rect_b[i][1]), (xB, rect_b[i + 1][3]), ACCENT)

    note_top = rect_b[3][1] - row_gap
    note_rect = draw_node(ax, xB, note_top, 3.72, None,
                          "RV 管道已回归 · 各设定不显著", None,
                          WARN, fill=WARN_LIGHT, title_size=8.8, lw=1.0,
                          ls=(0, (4, 2)), title_color=WARN)
    arrow(ax, (xB, rect_b[3][1]), (xB, note_rect[3]), ACCENT,
          ls=(0, (4, 2)))

    s_rect = draw_node(ax, xS, row_top[1], col_w, None,
                       "日度价格区间（替代口径）",
                       "Range_C_F1 · Range_C_F2\n季度均值\n仅保留完整三个月季度",
                       ACCENT, title_size=9.4, detail_size=8.4)

    c_w = 5.7
    c_top = note_rect[1] - row_gap
    c_rect = draw_node(ax, xB, c_top, c_w, None,
                       "营销年度 × 季度匹配",
                       "季度实证数据集：SUR 与季度波动率按 (营销年度, 季度) 对齐\n（含已构造 RV；分析使用日度区间口径）",
                       MAIN, fill=MAIN_LIGHT, title_size=10.0, detail_size=8.4)
    arrow(ax, (xA, rect_a[3][1]), (xB - c_w * 0.30, c_rect[3]), MAIN)
    arrow(ax, (xB, note_rect[1]), (xB, c_rect[3]), MAIN)
    arrow(ax, (xS, s_rect[1]), (xB + c_w * 0.32, c_rect[3]), MAIN)

    d_w = 5.15
    d_x = 2.925
    d_top = c_rect[1] - row_gap
    d_rect = draw_node(ax, d_x, d_top, d_w, None,
                       "计量分析（日度区间口径）",
                       "OLS + HAC 推断 · 季度固定效应\n线性趋势 · 滞后因变量\n二次项 / 样条 · 阈值检验\n结构断点 · 时序诊断 · 反向回归",
                       MAIN, fill=MAIN_LIGHT, title_size=9.6, detail_size=8.3)
    arrow(ax, (xB, c_rect[1]), (d_x + d_w * 0.20, d_rect[3]), MAIN)

    e_w = 3.18
    e_x = 7.59
    e_rect = draw_node(ax, e_x, d_top, e_w, None,
                       "诊断与研究判断",
                       "季节性与持续性\n设定敏感性\n反向关系\n测量与识别局限",
                       WARN, fill=WARN_LIGHT, title_size=9.6, detail_size=8.3,
                       title_color=WARN)
    mid_y = (d_rect[1] + d_rect[3]) / 2.0
    arrow(ax, (d_rect[2], mid_y), (e_rect[0], mid_y), WARN)

    pdf = os.path.join(HERE, "workflow_diagram.pdf")
    png = os.path.join(HERE, "workflow_diagram.png")
    svg = os.path.join(HERE, "workflow_diagram.svg")
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(png, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(svg, bbox_inches="tight", pad_inches=0.02)
    print("saved:", pdf)
    print("saved:", png)
    print("saved:", svg)


if __name__ == "__main__":
    main()
