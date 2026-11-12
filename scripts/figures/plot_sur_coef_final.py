#!/usr/bin/env python3
"""
Final SUR coefficient forest plot for the research-experience document.

All four specifications share one variable definition (SUR lagged one
quarter), one sample (n = 168 quarterly observations), one inference method
(HAC, lag 4) and quarterly fixed effects, so the sign flip across rows is
attributable to the added controls rather than to changes in the regressor.
Outcome is the daily price-range proxy (Range_C_F1 / Range_C_F2); the
CHRIS-CME quarterly RV regression is intentionally NOT plotted because it has
not been run yet.
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

import ppj_4 as p4


HERE = os.path.dirname(os.path.abspath(__file__))

for path in (
    os.path.join(HERE, "fonts", "NotoSansCJKsc-Regular.otf"),
    os.path.join(HERE, "fonts", "NotoSansCJKsc-Bold.otf"),
):
    font_manager.fontManager.addfont(path)

FONT = "Noto Sans CJK SC"
MAIN = "#1F4E79"
ACCENT = "#2A9D8F"
GRAY = "#5A6472"

plt.rcParams.update({
    "font.family": FONT,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.linewidth": 0.8,
    "axes.spines.top": True,
    "axes.spines.right": True,
    "xtick.major.size": 4,
    "ytick.major.size": 4,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
})

SPEC_LABELS = [
    "基准：季度固定效应",
    "＋ 线性趋势",
    "＋ 滞后波动率",
    "＋ 趋势＋滞后波动率",
]


def _season_cols(season):
    return [(season == s).astype(float) for s in (1, 2, 3)]


def _design(sur_lag, season_t, trend_t, lagy=None):
    cols = [np.ones(len(sur_lag)), sur_lag]
    if trend_t is not None:
        cols.append(trend_t)
    cols += _season_cols(season_t)
    if lagy is not None:
        cols.append(lagy)
    return np.column_stack(cols)


def main():
    d = p4.load_data()
    n = d["n"]
    sur, f1, f2 = d["sur"], d["f1"], d["f2"]
    season = d["season"]
    trend = np.arange(n, dtype=float)

    rows = []
    for outcome, y in (("F1", f1), ("F2", f2)):
        yt = y[1:]
        sur_lag = sur[:-1]
        season_t = season[1:]
        trend_t = trend[1:]
        for spec in ("qfe", "qfe_trend", "qfe_lag", "qfe_trend_lag"):
            if spec == "qfe":
                X = _design(sur_lag, season_t, None)
            elif spec == "qfe_trend":
                X = _design(sur_lag, season_t, trend_t)
            elif spec == "qfe_lag":
                X = _design(sur_lag, season_t, None, y[:-1])
            else:
                X = _design(sur_lag, season_t, trend_t, y[:-1])
            m = p4.ols_hac(yt, X, lag=4)
            b = float(m["beta"][1])
            se = float(m["se"][1])
            p = float(m["p"][1])
            rows.append({
                "outcome": outcome, "spec": spec, "coef": b, "se": se, "p": p,
                "lo95": b - 1.96 * se, "hi95": b + 1.96 * se, "n": int(m["n"]),
            })

    with open(os.path.join(HERE, "sur_coef_final_results.csv"), "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["outcome", "spec", "coef", "se", "p", "lo95", "hi95", "n"],
        )
        w.writeheader()
        w.writerows(rows)

    by = {r["outcome"]: {r["spec"]: r for r in rows} for r in rows}

    fig, ax = plt.subplots(figsize=(4.7, 2.45))
    fig.subplots_adjust(left=0.26, right=0.97, top=0.78, bottom=0.20)
    positions = list(range(len(SPEC_LABELS)))
    offset = 0.13

    for i, spec in enumerate(("qfe", "qfe_trend", "qfe_lag", "qfe_trend_lag")):
        for outcome, color, marker, dy in (
            ("F1", MAIN, "o", +offset),
            ("F2", ACCENT, "s", -offset),
        ):
            r = by[outcome][spec]
            significant = (r["lo95"] > 0) or (r["hi95"] < 0)
            ax.errorbar(
                r["coef"], i + dy,
                xerr=[[r["coef"] - r["lo95"]], [r["hi95"] - r["coef"]]],
                fmt=marker,
                markerfacecolor=color if significant else "white",
                markeredgecolor=color,
                markeredgewidth=1.1,
                color=color,
                elinewidth=1.3,
                capsize=3.2,
                capthick=1.0,
                markersize=5.5,
                zorder=3,
            )

    lo = min(r["lo95"] for r in rows)
    hi = max(r["hi95"] for r in rows)
    bound = max(abs(lo), abs(hi))
    ax.set_xlim(-(bound * 1.18), bound * 1.18)
    ax.axvline(0.0, color="#9AA3AD", lw=0.9, ls="--", zorder=1)
    ax.set_yticks(positions)
    ax.set_yticklabels(SPEC_LABELS, fontsize=8.6)
    ax.invert_yaxis()
    ax.set_xlabel("SUR 系数（$\\hat{\\beta}$）", fontsize=8.6)
    ax.tick_params(axis="both", labelsize=8.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color="#D8DEE6", lw=0.7, ls="--", alpha=0.9, zorder=0)
    ax.set_axisbelow(True)

    handles = [
        plt.Line2D([], [], marker="o", linestyle="", markerfacecolor="white",
                   markeredgecolor=MAIN, markersize=6, label="第一近月价格区间"),
        plt.Line2D([], [], marker="s", linestyle="", markerfacecolor="white",
                   markeredgecolor=ACCENT, markersize=6, label="第二近月价格区间"),
    ]
    ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=8.2)
    ax.set_title(
        "SUR 系数随设定变化（95% CI，HAC lag 4）",
        fontsize=10.0, loc="left", color=MAIN, fontweight="bold",
    )

    for ext in ("pdf", "png", "svg"):
        fig.savefig(os.path.join(HERE, f"sur_coef_final.{ext}"))
    print("wrote sur_coef_final.{pdf,png,svg} and sur_coef_final_results.csv")
    for r in rows:
        print(f"{r['outcome']} {r['spec']:14s} {r['coef']:+.5f} "
              f"[{r['lo95']:+.5f}, {r['hi95']:+.5f}] p={r['p']:.4f}")
if __name__ == "__main__":
    main()
