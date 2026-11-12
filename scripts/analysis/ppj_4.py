#!/usr/bin/env python3
"""
Maize / corn range vs. SUR: quarterly re-analysis (ppj_4).

Self-contained implementation using only numpy + scipy + stdlib (no pandas,
statsmodels, patsy, openpyxl).  It reads the USDA yearbook xlsx sheet directly
via zipfile/ElementTree and the daily range CSV via csv.

Fixed relative to ppj_3 / the old ppj_4:
  * month -> marketing-year mapping: August belongs to the *current* marketing
    year (Q4 = Jun-Jul-Aug), so the cut is m < 9, not m < 8.
  * threshold sup-F bootstrap and the LR confidence-set inversion are redone
    so the test statistic and bootstrap null agree, and the CI uses a
    chi2(1) 95% critical value (Hansen-style inversion), not the bootstrap
    sup-LR quantile (which was zero by construction in ppj_3).
"""

import csv
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime

import numpy as np
from scipy import stats


XLSX = "feed-grains-yearbook-all-years.xlsx"
CSV = "rangedata_commodities_since1877.csv"
SHEET = "FGYearbookTable04"

SEED = 0
HAC_LAG = 4
TRIM = (0.15, 0.85)
N_GRID = 200
BOOT_B = 999
CI_LEVEL = 0.95

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


# --------------------------------------------------------------------------- #
# Minimal xlsx reader (shared strings + numeric cells)
# --------------------------------------------------------------------------- #
def _col_idx(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref)
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx_sheet(path, sheet):
    z = zipfile.ZipFile(path)
    shared = []
    for _, elem in ET.iterparse(z.open("xl/sharedStrings.xml")):
        if elem.tag == _NS + "si":
            shared.append("".join(t.text or "" for t in elem.iter(_NS + "t")))
            elem.clear()

    wb = z.read("xl/workbook.xml").decode("utf-8")
    rid = re.search(
        r'<sheet[^>]*name="' + re.escape(sheet) + r'"[^>]*r:id="([^"]*)"', wb
    ).group(1)
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    target = re.search(
        r'<Relationship[^>]*Id="' + rid + r'"[^>]*Target="([^"]*)"', rels
    ).group(1)
    root = ET.fromstring(z.read("xl/" + target))

    rows = {}
    for row in root.iter(_NS + "row"):
        r = int(row.get("r"))
        cells = {}
        for c in row.findall(_NS + "c"):
            t = c.get("t")
            v = c.find(_NS + "v")
            val = None
            if t == "s" and v is not None:
                val = shared[int(v.text)]
            elif t != "s" and v is not None:
                val = v.text
            if val is not None:
                cells[_col_idx(c.get("r"))] = val
        if cells:
            rows[r] = cells

    if not rows:
        return []
    maxc = max(max(d) for d in rows.values())
    return [[rows[r].get(c, "") for c in range(maxc + 1)] for r in sorted(rows)]


# --------------------------------------------------------------------------- #
# Data assembly: quarterly marketing-year observations
# --------------------------------------------------------------------------- #
def _my_of(dt):
    y, m = dt.year, dt.month
    start = y - (1 if m < 9 else 0)  # marketing year starts in September
    return f"{start}/{str(start + 1)[-2:]}"


def _q_of(m):
    if m in (9, 10, 11):
        return "Q1"
    if m in (12, 1, 2):
        return "Q2"
    if m in (3, 4, 5):
        return "Q3"
    return "Q4"


def load_data():
    rows = read_xlsx_sheet(XLSX, SHEET)
    quarterly = []
    prev_my = ""
    for row in rows[2:]:  # rows[0] = title, rows[1] = header
        myv = str(row[0]).strip()
        if myv:
            prev_my = myv
        qv = str(row[1]).strip()
        if not re.match(r"^Q[1-4]", qv):
            continue
        try:
            total_use = float(row[11])
            ending = float(row[12])
        except (ValueError, TypeError, IndexError):
            continue
        quarterly.append((prev_my, qv[:2], total_use, ending))

    annual = {}
    for myv, q, total_use, ending in quarterly:
        annual[myv] = annual.get(myv, 0.0) + total_use
    sur = {}
    for myv, q, total_use, ending in quarterly:
        sur[(myv, q)] = ending / annual[myv]

    agg = {}
    with open(CSV, newline="") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if not row or not row[0]:
                continue
            dt = datetime.strptime(row[0], "%d-%m-%Y")
            myv, q = _my_of(dt), _q_of(dt.month)
            key = (myv, q)
            if key not in sur:
                continue
            try:
                f1 = float(row[3])
                f2 = float(row[4])
            except (ValueError, IndexError):
                continue
            if not (np.isfinite(f1) and np.isfinite(f2)):
                continue
            a = agg.get(key)
            if a is None:
                agg[key] = {"date": dt, "s1": f1, "s2": f2, "n": 1,
                            "months": {dt.month}}
            else:
                if dt < a["date"]:
                    a["date"] = dt
                a["s1"] += f1
                a["s2"] += f2
                a["n"] += 1
                a["months"].add(dt.month)

    items = sorted(
        (kv for kv in agg.items() if len(kv[1]["months"]) == 3),
        key=lambda kv: kv[1]["date"],
    )
    n = len(items)
    out = {}
    out["time"] = [myv + q for (myv, q), _ in items]
    out["my"] = [myv for (myv, q), _ in items]
    out["my_start"] = np.array([int(myv.split("/")[0]) for (myv, q), _ in items])
    out["qnum"] = np.array([int(q[1]) for (myv, q), _ in items])
    out["season"] = out["qnum"] - 1  # 0..3
    out["date"] = [a["date"] for (myv, q), a in items]
    out["f1"] = np.array([a["s1"] / a["n"] for _, a in items])
    out["f2"] = np.array([a["s2"] / a["n"] for _, a in items])
    out["sur"] = np.array([sur[(myv, q)] for (myv, q), _ in items])
    out["sur_c"] = out["sur"] - out["sur"].mean()
    out["n"] = n
    return out


# --------------------------------------------------------------------------- #
# Design matrices and OLS / HAC inference
# --------------------------------------------------------------------------- #
def _season_cols(season):
    return [(season == s).astype(float) for s in (1, 2, 3)]


def design_linear(x, season):
    return np.column_stack([np.ones(len(x)), x] + _season_cols(season))


def design_quad(x, season):
    return np.column_stack([np.ones(len(x)), x, x ** 2] + _season_cols(season))


def design_threshold(x, g, season):
    d = (x > g).astype(float)
    return np.column_stack([np.ones(len(x)), x, d, x * d] + _season_cols(season))


def spline_basis(x, knots):
    cols = [x, x ** 2, x ** 3]
    for k in knots:
        cols.append(np.maximum(x - k, 0.0) ** 3)
    return np.column_stack(cols)


def design_spline(x, season, knots):
    return np.column_stack(
        [np.ones(len(x)), spline_basis(x, knots)] + _season_cols(season)
    )


def ols_coef(y, X):
    try:
        return np.linalg.solve(X.T @ X, X.T @ y)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(X, y, rcond=None)[0]


def ols_ssr(y, X):
    beta = ols_coef(y, X)
    e = y - X @ beta
    return float(e @ e), beta


def ols_hac(y, X, lag=HAC_LAG):
    n, k = X.shape
    XtX = X.T @ X
    beta = ols_coef(y, X)
    try:
        XtXi = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        XtXi = np.linalg.pinv(XtX)
    e = y - X @ beta

    S = np.zeros((k, k))
    for t in range(n):
        xt = X[t]
        S += (e[t] * e[t]) * np.outer(xt, xt)
    for l in range(1, lag + 1):
        w = 1.0 - l / (lag + 1.0)
        for t in range(l, n):
            xt, xtl = X[t], X[t - l]
            M = np.outer(xt, xtl) + np.outer(xtl, xt)
            S += w * (e[t] * e[t - l]) * M
    cov = XtXi @ S @ XtXi
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    tstat = np.divide(beta, se, out=np.zeros_like(beta), where=se > 0)
    pval = 2.0 * stats.t.sf(np.abs(tstat), df=n - k)
    ssr = float(e @ e)
    sst = float((y - y.mean()) @ (y - y.mean()))
    r2 = 1.0 - ssr / sst if sst > 0 else 0.0
    aic = n * np.log(ssr / n) + 2.0 * k if ssr > 0 else np.inf
    return dict(
        beta=beta, se=se, t=tstat, p=pval, cov=cov, resid=e,
        fitted=X @ beta, ssr=ssr, r2=r2, aic=aic, n=n, k=k,
    )


def wald(R, beta, cov):
    Rb = R @ beta
    RV = R @ cov @ R.T
    W = float(Rb @ np.linalg.pinv(RV) @ Rb)
    p = float(stats.chi2.sf(W, R.shape[0]))
    return W, p


def intervals_from_mask(grid, mask):
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return []
    out = []
    start = prev = idx[0]
    for i in idx[1:]:
        if i == prev + 1:
            prev = i
        else:
            out.append((grid[start], grid[prev]))
            start = prev = i
    out.append((grid[start], grid[prev]))
    return out


# --------------------------------------------------------------------------- #
# Experiment 1: threshold inference (sup-F bootstrap + LR confidence set)
# --------------------------------------------------------------------------- #
def precompute_threshold(x, season, grid):
    Xs, Gs = [], []
    for g in grid:
        X = design_threshold(x, g, season)
        Xs.append(X)
        Gs.append(np.linalg.pinv(X.T @ X))
    return Xs, Gs


def ssr_grid_pre(y, Xs, Gs):
    yty = float(y @ y)
    out = np.empty(len(Xs))
    for i, (X, G) in enumerate(zip(Xs, Gs)):
        z = X.T @ y
        out[i] = yty - float(z @ (G @ z))
    return np.maximum(out, 1e-12)


def threshold_test(y, x, season, B=BOOT_B, n_grid=N_GRID, trim=TRIM, seed=SEED):
    n = len(y)
    lo, hi = np.quantile(x, [trim[0], trim[1]])
    grid = np.linspace(lo, hi, n_grid)

    X0 = design_linear(x, season)
    G0 = np.linalg.pinv(X0.T @ X0)
    ssr0, b0 = ols_ssr(y, X0)

    Xs, Gs = precompute_threshold(x, season, grid)
    ssr_g = ssr_grid_pre(y, Xs, Gs)
    i_hat = int(np.argmin(ssr_g))
    g_hat = float(grid[i_hat])
    ssr1 = float(ssr_g[i_hat])
    supF = n * (ssr0 - ssr1) / ssr1

    rng = np.random.default_rng(seed)
    fit0 = X0 @ b0
    resid0 = y - fit0
    Fb = np.empty(B)
    for b in range(B):
        yb = fit0 + rng.choice(resid0, size=n, replace=True)
        yty = float(yb @ yb)
        z0 = X0.T @ yb
        ssr0b = yty - float(z0 @ (G0 @ z0))
        ssrb = ssr_grid_pre(yb, Xs, Gs)
        Fb[b] = n * (ssr0b - ssrb.min()) / ssrb.min()
    pval = float(np.mean(Fb >= supF))

    LR = n * (ssr_g - ssr1) / ssr1
    crit = stats.chi2.ppf(CI_LEVEL, 1)
    ci = intervals_from_mask(grid, LR <= crit)
    return dict(supF=supF, p=pval, gamma=g_hat, grid=grid, LR=LR,
                crit=crit, ci=ci)


# --------------------------------------------------------------------------- #
# Experiment 3 helper: unknown-break sup-Chow test (formal structural change)
# --------------------------------------------------------------------------- #
def break_test(y, x, season, B=BOOT_B, trim=0.15, seed=SEED):
    n = len(y)
    lo, hi = int(np.floor(n * trim)), int(np.ceil(n * (1 - trim)))
    breaks = list(range(lo, hi))

    X0 = design_linear(x, season)
    G0 = np.linalg.pinv(X0.T @ X0)
    ssr0, b0 = ols_ssr(y, X0)

    pre = []
    for b in breaks:
        Xl = design_linear(x[:b], season[:b])
        Xr = design_linear(x[b:], season[b:])
        pre.append((Xl, np.linalg.pinv(Xl.T @ Xl), Xr, np.linalg.pinv(Xr.T @ Xr)))

    def ssr_break(yv):
        out = np.empty(len(pre))
        for i, (Xl, Gl, Xr, Gr) in enumerate(pre):
            nl = len(Xl)
            yl, yr = yv[:nl], yv[nl:]
            zl, zr = Xl.T @ yl, Xr.T @ yr
            out[i] = (
                float(yl @ yl - zl @ (Gl @ zl))
                + float(yr @ yr - zr @ (Gr @ zr))
            )
        return np.maximum(out, 1e-12)

    ssrs = ssr_break(y)
    i_hat = int(np.argmin(ssrs))
    supF = n * (ssr0 - ssrs[i_hat]) / ssrs[i_hat]
    b_hat = breaks[i_hat]

    rng = np.random.default_rng(seed)
    fit0 = X0 @ b0
    resid0 = y - fit0
    Fb = np.empty(B)
    for b in range(B):
        yb = fit0 + rng.choice(resid0, size=n, replace=True)
        z0 = X0.T @ yb
        ssr0b = float(yb @ yb - z0 @ (G0 @ z0))
        ssrb = ssr_break(yb)
        Fb[b] = n * (ssr0b - ssrb.min()) / ssrb.min()
    pval = float(np.mean(Fb >= supF))
    return dict(supF=supF, p=pval, b_hat=b_hat)


# --------------------------------------------------------------------------- #
# Small formatting helpers
# --------------------------------------------------------------------------- #
def _f(x, nd=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "nan"
    return f"{x:.{nd}f}"


def _p(x):
    if x is None or not np.isfinite(x):
        return "nan"
    if x < 1e-4:
        return f"{x:.2e}"
    return f"{x:.4f}"


def _ci_str(intervals, mean):
    if not intervals:
        return "empty"
    return " U ".join(f"[{_f(lo + mean)}, {_f(hi + mean)}]" for lo, hi in intervals)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    d = load_data()
    n = d["n"]
    f1, f2 = d["f1"], d["f2"]
    x = d["sur_c"]
    season = d["season"]
    sur = d["sur"]
    print("=" * 78)
    print("Quarterly sample")
    print("=" * 78)
    print(f"n = {n} quarters | {d['time'][0]} .. {d['time'][-1]}")
    print(f"SUR range = [{sur.min():.3f}, {sur.max():.3f}]  "
          f"mean = {sur.mean():.3f}  sd = {sur.std():.3f}")
    print()

    # ------------------------------------------------------------------ #
    print("=" * 78)
    print("Experiment 1: threshold inference (sup-F bootstrap + LR CI)")
    print("=" * 78)
    print(f"model: y ~ 1 + x + 1[x>g] + x*1[x>g] + quarter FE | "
          f"grid {N_GRID} pts in [{TRIM[0]:.2f},{TRIM[1]:.2f}] quantiles | "
          f"B = {BOOT_B}, seed = {SEED} | CI = LR <= chi2(1,0.95)")
    print()
    for label, y in (("Range_C_F1", f1), ("Range_C_F2", f2)):
        r = threshold_test(y, x, season)
        print(f"[{label}]")
        print(f"  gamma(SUR_c) = {_f(r['gamma'])}   "
              f"gamma(SUR) = {_f(r['gamma'] + sur.mean())}")
        print(f"  sup-F = {_f(r['supF'], 3)}   bootstrap p = {_p(r['p'])}")
        print(f"  95% LR confidence set (original SUR) = "
              f"{_ci_str(r['ci'], sur.mean())}")
        if not r["ci"]:
            print("  (LR never falls below the chi2(1) critical value: "
                  "threshold not identified at 95%)")
        elif r["p"] > 0.05:
            print("  (threshold test not significant at 5%; the point estimate "
                  "and CI are not meaningful -- any isolated CI pieces are "
                  "grid artifacts)")
        print()

    # ------------------------------------------------------------------ #
    print("=" * 78)
    print("Experiment 2: unified seasonal controls (linear / quadratic / spline)")
    print("=" * 78)
    print(f"All models include quarter FE (Q1 baseline) and use HAC lag {HAC_LAG}.")
    print("Spline = cubic truncated-power basis, interior knots at 1/3, 2/3 "
          "quantiles of SUR_c.")
    print()
    for label, y in (("Range_C_F1", f1), ("Range_C_F2", f2)):
        print(f"--- {label} ---")
        m_lin = ols_hac(y, design_linear(x, season))
        m_quad = ols_hac(y, design_quad(x, season))
        knots = np.quantile(x, [1 / 3, 2 / 3])
        X_spl = design_spline(x, season, knots)
        m_spl = ols_hac(y, X_spl)

        b_quad = m_quad["beta"][2]
        t_quad = m_quad["t"][2]
        p_quad = m_quad["p"][2]
        R_spl = np.zeros((4, m_spl["k"]))
        for j, col in enumerate(range(2, 6)):
            R_spl[j, col] = 1.0
        W_spl, p_spl = wald(R_spl, m_spl["beta"], m_spl["cov"])

        print(f"  {'model':10s} {'k':>2s} {'R2':>7s} {'AIC':>9s}  "
              f"nonlinear term / joint test")
        print(f"  {'linear':10s} {m_lin['k']:>2d} {m_lin['r2']:>7.4f} "
              f"{m_lin['aic']:>9.2f}  --")
        print(f"  {'quadratic':10s} {m_quad['k']:>2d} {m_quad['r2']:>7.4f} "
              f"{m_quad['aic']:>9.2f}  b(x^2)={_f(b_quad)} "
              f"t={_f(t_quad, 2)} p={_p(p_quad)}")
        print(f"  {'spline':10s} {m_spl['k']:>2d} {m_spl['r2']:>7.4f} "
              f"{m_spl['aic']:>9.2f}  Wald(4 df)={_f(W_spl, 2)} p={_p(p_spl)}")

        print(f"  {'slope at':14s} {'linear':>24s} {'quadratic':>24s} "
              f"{'spline':>24s}")
        for q in (0.20, 0.50, 0.80):
            xq = float(np.quantile(x, q))
            s_lin = m_lin["beta"][1]
            se_lin = m_lin["se"][1]
            g_q = np.array([1.0, 2.0 * xq])
            s_quad = m_quad["beta"][1] + 2.0 * m_quad["beta"][2] * xq
            se_quad_s = float(np.sqrt(g_q @ m_quad["cov"][1:3, 1:3] @ g_q))
            g_spl = np.zeros(m_spl["k"])
            g_spl[1] = 1.0
            g_spl[2] = 2.0 * xq
            g_spl[3] = 3.0 * xq ** 2
            for j, k in enumerate(knots):
                g_spl[4 + j] = 3.0 * max(xq - k, 0.0) ** 2
            s_spl = float(g_spl @ m_spl["beta"])
            se_spl = float(np.sqrt(g_spl @ m_spl["cov"] @ g_spl))
            print(f"  {'p' + str(int(q * 100)) + ' (SUR_c=' + _f(xq) + ')':14s} "
                  f"{s_lin:>8.4f} ({_f(s_lin - 1.96 * se_lin)},{_f(s_lin + 1.96 * se_lin)})   "
                  f"{s_quad:>8.4f} ({_f(s_quad - 1.96 * se_quad_s)},{_f(s_quad + 1.96 * se_quad_s)})   "
                  f"{s_spl:>8.4f} ({_f(s_spl - 1.96 * se_spl)},{_f(s_spl + 1.96 * se_spl)})")
        print()

    # ------------------------------------------------------------------ #
    print("=" * 78)
    print("Experiment 3: historical stability (pre-specified segments + break test)")
    print("=" * 78)
    print("A-priori segments (institutional): <1996 pre-FAIR, 1996-2005 FAIR, "
          ">=2006 ethanol/RFS.")
    print()
    seg = np.where(d["my_start"] < 1996, 0,
                   np.where(d["my_start"] < 2006, 1, 2))
    seg_names = ["pre-FAIR", "FAIR", "ethanol"]

    for label, y in (("Range_C_F1", f1), ("Range_C_F2", f2)):
        print(f"[{label}] per-segment linear and quadratic estimates "
              f"(HAC lag {HAC_LAG}, quarter FE):")
        print(f"  {'segment':10s} {'period':18s} {'n':>3s}  "
              f"{'b_x':>8s} {'t':>6s} {'p':>8s}   "
              f"{'b_x2':>8s} {'t':>6s} {'p':>8s}")
        for s in range(3):
            m = seg == s
            if m.sum() < 20:
                continue
            xs, ss = x[m], season[m]
            ys = y[m]
            per = f"{d['my'][np.where(m)[0][0]]}~{d['my'][np.where(m)[0][-1]]}"
            mlin = ols_hac(ys, design_linear(xs, ss))
            mquad = ols_hac(ys, design_quad(xs, ss))
            b_x, b_x2 = mlin["beta"][1], mquad["beta"][2]
            print(f"  {seg_names[s]:10s} {per:18s} {m.sum():>3d}  "
                  f"{b_x:>8.4f} {mlin['t'][1]:>6.2f} {_p(mlin['p'][1]):>8s}   "
                  f"{b_x2:>8.4f} {mquad['t'][2]:>6.2f} {_p(mquad['p'][2]):>8s}")

        seg1 = (seg == 1).astype(float)
        seg2 = (seg == 2).astype(float)
        X_eq_lin = np.column_stack(
            [np.ones(n), x] + _season_cols(season) +
            [seg1, seg2, seg1 * x, seg2 * x]
        )
        R_lin_eq = np.zeros((2, X_eq_lin.shape[1]))
        R_lin_eq[0, -2] = 1.0
        R_lin_eq[1, -1] = 1.0
        m_lin_eq = ols_hac(y, X_eq_lin)
        W, p = wald(R_lin_eq, m_lin_eq["beta"], m_lin_eq["cov"])
        print(f"[{label}] linear slope equality across 3 segments: "
              f"Wald(2) = {_f(W, 2)}  p = {_p(p)}")

        X_eq_q = np.column_stack(
            [np.ones(n), x, x ** 2] + _season_cols(season) +
            [seg1, seg2, seg1 * x, seg1 * x ** 2, seg2 * x, seg2 * x ** 2]
        )
        R_q_eq = np.zeros((2, X_eq_q.shape[1]))
        R_q_eq[0, 9] = 1.0   # seg1 * x^2
        R_q_eq[1, 11] = 1.0  # seg2 * x^2
        m_q_eq = ols_hac(y, X_eq_q)
        Wq, pq = wald(R_q_eq, m_q_eq["beta"], m_q_eq["cov"])
        print(f"[{label}] quadratic curvature (b_x2) equality across segments: "
              f"Wald(2) = {_f(Wq, 2)}  p = {_p(pq)}")

        br = break_test(y, x, season)
        print(f"[{label}] formal single-break test (linear + quarter FE): "
              f"sup-Chow = {_f(br['supF'], 2)}  bootstrap p = {_p(br['p'])}  "
              f"break at obs {br['b_hat']} ({d['time'][br['b_hat']]})")
    print()

    # ------------------------------------------------------------------ #
    print("=" * 78)
    print("Experiment 4: strict chronological out-of-sample comparison")
    print("=" * 78)
    print("Expanding window: initial train = first 60% of quarters; then add one "
          "quarter and forecast the next. Threshold/spline knots are estimated "
          "inside the training window only (no leakage). Pseudo-OOS uses realized "
          "SUR as a known predictor.")
    print()
    for label, y in (("Range_C_F1", f1), ("Range_C_F2", f2)):
        rmse, win = oos_rmse(y, sur, season)
        base = rmse["linear"]
        print(f"--- {label} ---")
        print(f"  {'model':10s} {'RMSE':>10s}  {'vs linear':>10s}  "
              f"{'win vs linear':>14s}")
        for name in ("linear", "quadratic", "spline", "threshold"):
            rel = (base - rmse[name]) / base * 100.0 if base > 0 else 0.0
            wr = "  --" if name == "linear" else f"{win[name] * 100:>13.0f}%"
            print(f"  {name:10s} {rmse[name]:>10.6f}  {rel:>+9.2f}%  {wr:>14s}")
        print()


def oos_rmse(y, sur, season, init_frac=0.60):
    n = len(y)
    t0 = int(round(n * init_frac))
    errs = {"linear": [], "quadratic": [], "spline": [], "threshold": []}
    for t in range(t0, n):
        ytr, yte = y[:t], y[t]
        sur_tr, sur_te = sur[:t], sur[t]
        season_tr, season_te = season[:t], season[t]
        mu = sur_tr.mean()
        xtr = sur_tr - mu
        xte = sur_te - mu

        # linear
        X = design_linear(xtr, season_tr)
        b = ols_coef(ytr, X)
        Xte = design_linear(np.array([xte]), np.array([season_te]))
        errs["linear"].append((yte - float((Xte @ b)[0])) ** 2)

        # quadratic
        X = design_quad(xtr, season_tr)
        b = ols_coef(ytr, X)
        Xte = design_quad(np.array([xte]), np.array([season_te]))
        errs["quadratic"].append((yte - float((Xte @ b)[0])) ** 2)

        # spline (knots from training data)
        knots = np.quantile(xtr, [1 / 3, 2 / 3])
        X = design_spline(xtr, season_tr, knots)
        b = ols_coef(ytr, X)
        Xte = design_spline(np.array([xte]), np.array([season_te]), knots)
        errs["spline"].append((yte - float((Xte @ b)[0])) ** 2)

        # threshold (gamma estimated in training data)
        lo, hi = np.quantile(xtr, [TRIM[0], TRIM[1]])
        grid = np.linspace(lo, hi, N_GRID)
        Xs, Gs = precompute_threshold(xtr, season_tr, grid)
        ssr_g = ssr_grid_pre(ytr, Xs, Gs)
        g_hat = float(grid[int(np.argmin(ssr_g))])
        X = design_threshold(xtr, g_hat, season_tr)
        b = ols_coef(ytr, X)
        Xte = design_threshold(np.array([xte]), g_hat, np.array([season_te]))
        errs["threshold"].append((yte - float((Xte @ b)[0])) ** 2)

    rmse = {k: float(np.sqrt(np.mean(v))) for k, v in errs.items()}
    win = {
        k: float(np.mean(np.array(errs[k]) < np.array(errs["linear"])))
        for k in errs
        if k != "linear"
    }
    return rmse, win


if __name__ == "__main__":
    main()
