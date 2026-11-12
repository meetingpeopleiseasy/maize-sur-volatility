#!/usr/bin/env python3
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

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
RV_COLOR = "#B37D10"
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


def _load_rv(d):
    path = os.path.join(HERE, "CHRIS-CME_C1.csv")
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(HERE), "ooo", "CHRIS-CME_C1.csv")
    price = pd.read_csv(path)
    price["Date"] = pd.to_datetime(price["Date"])
    price = price.sort_values("Date").reset_index(drop=True)

    price["log_ret"] = np.log(price["Settle"]).diff()
    price["month"] = price["Date"].dt.month
    price["day"] = price["Date"].dt.day

    in_window = price["month"].isin([3, 5, 7, 9, 12]) & price["day"].between(15, 25)
    thr = np.where(in_window, 0.020, 0.060)
    price["is_roll"] = (price["log_ret"].abs() > thr) & in_window
    price.loc[0, "is_roll"] = False

    roll_dates = price.index[price["is_roll"]].tolist()
    keep = []
    last = None
    year_count = {}
    for i in roll_dates:
        y = price.at[i, "Date"].year
        if year_count.get(y, 0) >= 6:
            continue
        if last is not None and (price.at[i, "Date"] - price.at[last, "Date"]).days < 30:
            continue
        keep.append(i)
        last = i
        year_count[y] = year_count.get(y, 0) + 1

    price["is_roll"] = False
    price.loc[keep, "is_roll"] = True
    price["log_ret_adj"] = price["log_ret"].where(~price["is_roll"], 0.0)

    year = price["Date"].dt.year
    price["marketing_year"] = np.where(
        price["Date"].dt.month >= 9,
        year.astype(str) + "/" + ((year + 1) % 100).astype(str).str.zfill(2),
        (year - 1).astype(str) + "/" + (year % 100).astype(str).str.zfill(2),
    )
    quarter_map = {
        9: "Q1", 10: "Q1", 11: "Q1",
        12: "Q2", 1: "Q2", 2: "Q2",
        3: "Q3", 4: "Q3", 5: "Q3",
        6: "Q4", 7: "Q4", 8: "Q4",
    }
    price["quarter"] = price["Date"].dt.month.map(quarter_map)

    rv = (
        price.groupby(["marketing_year", "quarter"])
        .agg(
            RV=("log_ret_adj", lambda x: np.sqrt(np.sum(x.dropna() ** 2))),
            n_days=("log_ret_adj", "count"),
        )
        .reset_index()
    )
    rv = rv[rv["n_days"] >= 55].copy()
    rv["qnum"] = rv["quarter"].str.extract(r"(\d)").astype(int)
    lookup = {(r.marketing_year, r.qnum): r.RV for r in rv.itertuples()}
    return np.array([lookup.get((my, q), np.nan) for my, q in zip(d["my"], d["qnum"])], dtype=float)


def main():
    d = p4.load_data()
    n = d["n"]
    sur, f1, f2 = d["sur"], d["f1"], d["f2"]
    rv = _load_rv(d)
    season = d["season"]
    trend = np.arange(n, dtype=float)

    rows = []
    for outcome, y in (("F1", f1), ("F2", f2), ("RV", rv)):
        yt_full = y[1:]
        sur_lag_full = sur[:-1]
        season_t_full = season[1:]
        trend_t_full = trend[1:]
        lagy_full = y[:-1]
        for spec in ("qfe", "qfe_trend", "qfe_lag", "qfe_trend_lag"):
            valid = np.isfinite(yt_full)
            if spec in ("qfe_lag", "qfe_trend_lag"):
                valid &= np.isfinite(lagy_full)
            yt = yt_full[valid]
            sur_lag = sur_lag_full[valid]
            season_t = season_t_full[valid]
            trend_t = trend_t_full[valid]
            lagy = lagy_full[valid] if spec in ("qfe_lag", "qfe_trend_lag") else None

            if spec == "qfe":
                X = _design(sur_lag, season_t, None)
            elif spec == "qfe_trend":
                X = _design(sur_lag, season_t, trend_t)
            elif spec == "qfe_lag":
                X = _design(sur_lag, season_t, None, lagy)
            else:
                X = _design(sur_lag, season_t, trend_t, lagy)
            m = p4.ols_hac(yt, X, lag=4)
            b = float(m["beta"][1])
            se = float(m["se"][1])
            p = float(m["p"][1])
            rows.append({
                "outcome": outcome, "spec": spec, "coef": b, "se": se, "p": p,
                "lo95": b - 1.96 * se, "hi95": b + 1.96 * se, "n": int(m["n"]),
            })

    with open(os.path.join(HERE, "sur_coef_final_rv_results.csv"), "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["outcome", "spec", "coef", "se", "p", "lo95", "hi95", "n"],
        )
        w.writeheader()
        w.writerows(rows)

    by = {r["outcome"]: {r["spec"]: r for r in rows} for r in rows}

    fig, ax = plt.subplots(figsize=(4.7, 3.1))
    fig.subplots_adjust(left=0.26, right=0.97, top=0.80, bottom=0.16)
    positions = [i * 1.45 for i in range(len(SPEC_LABELS))]
    offset = 0.20

    for i, spec in enumerate(("qfe", "qfe_trend", "qfe_lag", "qfe_trend_lag")):
        for outcome, color, marker, dy in (
            ("F1", MAIN, "o", +offset),
            ("F2", ACCENT, "s", -offset),
            ("RV", RV_COLOR, "^", 0.0),
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
            ax.annotate(
                f"{r['coef']:+.4f}",
                xy=(r["coef"], i + dy),
                xytext=(4, 0),
                textcoords="offset points",
                fontsize=7.0,
                color=color,
                va="center",
                ha="left",
                zorder=4,
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
        plt.Line2D([], [], marker="^", linestyle="", markerfacecolor="white",
                   markeredgecolor=RV_COLOR, markersize=6, label="CHRIS-CME 已实现波动率 RV"),
    ]
    ax.legend(
        handles=handles,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.01),
        ncol=3,
        frameon=False,
        fontsize=8.2,
        handlelength=1.6,
        columnspacing=1.0,
    )
    ax.set_title(
        "SUR 系数随设定变化（95% CI，HAC lag 4）",
        fontsize=10.0, loc="left", color=MAIN, fontweight="bold",
    )

    for ext in ("pdf", "png", "svg"):
        fig.savefig(os.path.join(HERE, f"sur_coef_final_rv.{ext}"))
    print("wrote sur_coef_final_rv.{pdf,png,svg} and sur_coef_final_rv_results.csv")
    for r in rows:
        print(f"{r['outcome']} {r['spec']:14s} {r['coef']:+.5f} "
              f"[{r['lo95']:+.5f}, {r['hi95']:+.5f}] p={r['p']:.4f}")


if __name__ == "__main__":
    main()
