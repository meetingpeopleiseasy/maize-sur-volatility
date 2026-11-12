#!/usr/bin/env python3
"""
Data feasibility audit (freeze models; no new threshold / break / complex model).

Reads the same quarterly panel as ppj_4 and answers, with numbers:
  1. Is SUR, after seasonality, mainly a slow-moving market state?
  2. Is the linear range~SUR relation driven by a few tight-inventory periods?
  3. Is there reverse causality / a common shock?
  4. Does the inventory measure represent trader-real-time information?

No pandas / statsmodels: reuses ppj_4's load_data and OLS/HAC helpers.
"""

import numpy as np

import ppj_4 as p4


def design(x, season, trend, lagy=None):
    cols = [np.ones(len(x)), x, trend] + p4._season_cols(season)
    if lagy is not None:
        cols.append(lagy)
    return np.column_stack(cols)


def rsq(y, X):
    b = p4.ols_coef(y, X)
    e = y - X @ b
    return 1.0 - float(e @ e) / float((y - y.mean()) @ (y - y.mean()))


def main():
    d = p4.load_data()
    n = d["n"]
    sur, f1, f2 = d["sur"], d["f1"], d["f2"]
    season = d["season"]
    trend = np.arange(n, dtype=float)

    print("=" * 78)
    print("0. Data-source facts (vintage / release dates)")
    print("=" * 78)
    rows = p4.read_xlsx_sheet(p4.XLSX, p4.SHEET)
    for r in rows[-5:]:
        txt = " | ".join(str(c).strip() for c in r[:3] if str(c).strip())
        if txt:
            print("  " + txt)
    print("  -> no per-observation release/vintage date is present in the file.")
    print()

    print("=" * 78)
    print("1. Seasonality and persistence")
    print("=" * 78)
    Q = np.column_stack([np.ones(n)] + p4._season_cols(season))
    print(f"  {'var':12s} {'QFE R2':>8s} {'resid AR1':>10s} {'ACF 1-4':>20s} "
          f"{'sd':>8s}")
    for name, y in (("SUR", sur), ("Range_C_F1", f1), ("Range_C_F2", f2)):
        r2q = rsq(y, Q)
        resid = y - Q @ p4.ols_coef(y, Q)
        ar1 = np.corrcoef(resid[:-1], resid[1:])[0, 1]
        acf = [np.corrcoef(resid[:-l], resid[l:])[0, 1] for l in (1, 2, 3, 4)]
        print(f"  {name:12s} {r2q:8.3f} {ar1:10.3f} "
              f"{('[' + ' '.join(f'{a:.2f}' for a in acf) + ']'):20s} {y.std():8.4f}")
    print("  corr(SUR, trend) = %.3f; corr(F1, trend) = %.3f; "
          "corr(F2, trend) = %.3f" % (
              np.corrcoef(sur, trend)[0, 1],
              np.corrcoef(f1, trend)[0, 1],
              np.corrcoef(f2, trend)[0, 1]))
    print()

    print("=" * 78)
    print("2. Lead-lag correlations (quarter-demeaned)")
    print("=" * 78)

    def qdemean(y):
        return y - Q @ p4.ols_coef(y, Q)

    sc, r1, r2 = qdemean(sur), qdemean(f1), qdemean(f2)
    for name, r in (("F1", r1), ("F2", r2)):
        print(f"  {name}: corr(range_t, sur_t)       = "
              f"{np.corrcoef(r, sc)[0, 1]:.3f}")
        print(f"        corr(range_t, sur_lag1)   = "
              f"{np.corrcoef(r[1:], sc[:-1])[0, 1]:.3f}")
        print(f"        corr(range_lag1, sur_t)   = "
              f"{np.corrcoef(r[:-1], sc[1:])[0, 1]:.3f}")
    print()

    print("=" * 78)
    print("3. Does SUR survive trend + seasonality + lagged market state?")
    print("=" * 78)
    for label, y in (("Range_C_F1", f1), ("Range_C_F2", f2)):
        m0 = p4.ols_hac(y, design(sur, season, trend, None), lag=4)
        m1 = p4.ols_hac(y[1:], design(sur[:-1], season[:-1], trend[:-1], y[:-1]),
                        lag=4)
        m2 = p4.ols_hac(y[1:], design(sur[:-1], season[1:], trend[1:], y[:-1]),
                        lag=4)
        sd_y, sd_x = y.std(), sur.std()
        print(f"  --- {label} ---")
        for tag, m in (("SUR_t + QFE + trend", m0),
                       ("SUR_t + QFE + trend + y_lag", m1),
                       ("SUR_{t-1} + QFE + trend + y_lag", m2)):
            b, se, t, pv = m["beta"][1], m["se"][1], m["t"][1], m["p"][1]
            print(f"    {tag:32s} b={b:+.5f} se={se:.5f} t={t:.2f} "
                  f"p={pv:.4f} beta_std={b * sd_x / sd_y:+.3f}")
    print()

    print("=" * 78)
    print("4. Tight-inventory / influence and reverse-direction checks")
    print("=" * 78)
    lo = np.argsort(sur)[:8]
    keep = np.ones(n, bool)
    keep[lo] = False
    for label, y in (("Range_C_F1", f1), ("Range_C_F2", f2)):
        X = np.column_stack([np.ones(n), sur - sur.mean()]
                            + p4._season_cols(season))
        m = p4.ols_hac(y, X, lag=4)
        Xk = np.column_stack([np.ones(keep.sum()), (sur - sur.mean())[keep]]
                             + p4._season_cols(season[keep]))
        mk = p4.ols_hac(y[keep], Xk, lag=4)
        print(f"  {label}: full b={m['beta'][1]:+.5f} (p={m['p'][1]:.4f}) | "
              f"drop 8 lowest-SUR b={mk['beta'][1]:+.5f} (p={mk['p'][1]:.4f})")
    # reverse: does lagged range predict SUR?
    for label, y in (("Range_C_F1", f1), ("Range_C_F2", f2)):
        Xr = design(sur[1:], season[1:], trend[1:], y[:-1])
        mr = p4.ols_hac(sur[1:], Xr, lag=4)
        print(f"  reverse SUR_t ~ trend + QFE + {label}_lag1: "
              f"b={mr['beta'][3]:+.2e} t={mr['t'][3]:.2f} p={mr['p'][3]:.4f}")
    print()

    print("=" * 78)
    print("Stopping criterion")
    print("=" * 78)
    print("  If (a) the file provides no real-time vintage, and (b) SUR does not")
    print("  survive trend + seasonality + lagged state, then the analysis is a")
    print("  historical conditional-correlation study, not a causal or real-time")
    print("  prediction study.")


if __name__ == "__main__":
    main()
