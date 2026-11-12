#!/usr/bin/env python3
"""
Time-series diagnostics (unit root / stationarity / endogenous break) and the
first-difference short-run model.  No threshold search, no break-picking for
significance: each test is run once with a pre-specified specification.

Critical values are the standard asymptotic values (MacKinnon ADF, ERS DF-GLS,
KPSS, Zivot-Andrews); they are approximate for T ~ 170.  Lag order is chosen by
BIC over 0..floor(12*(T/100)**0.25).
"""

import numpy as np

import ppj_4 as p4


def _ols_t(y, X):
    n, k = X.shape
    b = p4.ols_coef(y, X)
    e = y - X @ b
    s2 = float(e @ e) / (n - k)
    cov = s2 * np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    return b, se, e


def _max_lag(T):
    return int(np.floor(12.0 * (T / 100.0) ** 0.25))


def _bic(ssr, n, k):
    return n * np.log(ssr / n) + k * np.log(n)


def adf_stat(y, trend=False):
    T = len(y)
    dy = np.diff(y)
    best = None
    for p in range(_max_lag(T) + 1):
        n = T - 1 - p
        if n <= 12:
            continue
        dep, X = [], []
        for t in range(p + 1, T):
            yi = t - 1
            row = [1.0, y[yi - 1]]
            if trend:
                row.append(float(t))
            for j in range(1, p + 1):
                row.append(dy[yi - j])
            dep.append(dy[yi])
            X.append(row)
        dep, X = np.array(dep), np.array(X)
        b = p4.ols_coef(dep, X)
        ssr = float((dep - X @ b) @ (dep - X @ b))
        bic = _bic(ssr, n, X.shape[1])
        if best is None or bic < best[0]:
            best = (bic, p, dep, X, b)
    _, p, dep, X, b = best
    _, se, _ = _ols_t(dep, X)
    return float(b[1] / se[1]), p, len(dep)


def dfgls(y, trend=False):
    T = len(y)
    cbar = 13.5 if trend else 7.0
    rho = 1.0 - cbar / T
    yq = np.empty(T)
    yq[0] = y[0]
    for t in range(1, T):
        yq[t] = y[t] - rho * y[t - 1]
    if trend:
        cols = [np.ones(T), np.arange(1, T + 1, dtype=float)]
    else:
        cols = [np.ones(T)]
    Zq = []
    for col in cols:
        zq = np.empty(T)
        zq[0] = col[0]
        for t in range(1, T):
            zq[t] = col[t] - rho * col[t - 1]
        Zq.append(zq)
    Zq = np.column_stack(Zq)
    beta = p4.ols_coef(yq, Zq)
    yd = y - Zq @ beta
    dy = np.diff(yd)
    best = None
    for p in range(_max_lag(T) + 1):
        n = T - 1 - p
        if n <= 12:
            continue
        dep, X = [], []
        for t in range(p + 1, T):
            yi = t - 1
            row = [yd[yi - 1]]
            for j in range(1, p + 1):
                row.append(dy[yi - j])
            dep.append(dy[yi])
            X.append(row)
        dep, X = np.array(dep), np.array(X)
        b = p4.ols_coef(dep, X)
        ssr = float((dep - X @ b) @ (dep - X @ b))
        bic = _bic(ssr, n, X.shape[1])
        if best is None or bic < best[0]:
            best = (bic, p, dep, X, b)
    _, p, dep, X, b = best
    _, se, _ = _ols_t(dep, X)
    return float(b[0] / se[0]), p, len(dep)


def kpss(y, trend=False):
    T = len(y)
    l = int(np.floor(4.0 * (T / 100.0) ** 0.25))
    if trend:
        X = np.column_stack([np.ones(T), np.arange(1, T + 1, dtype=float)])
    else:
        X = np.ones((T, 1))
    b = p4.ols_coef(y, X)
    e = y - X @ b
    S = np.cumsum(e)
    s2 = float(e @ e) / T
    for j in range(1, l + 1):
        w = 1.0 - j / (l + 1.0)
        s2 += 2.0 * w * float(e[j:] @ e[:-j]) / T
    stat = float(S @ S) / (T * T * s2)
    return stat, l


def zivot_andrews(y, p, trim=0.10):
    T = len(y)
    dy = np.diff(y)
    lo, hi = int(np.floor(T * trim)), int(np.ceil(T * (1 - trim)))
    best_t, best_tb = np.inf, None
    for tb in range(lo, hi):
        dep, X = [], []
        for t in range(p + 1, T):
            yi = t - 1
            row = [1.0, float(t), y[yi - 1],
                   1.0 if t > tb else 0.0,
                   float(t - tb) if t > tb else 0.0]
            for j in range(1, p + 1):
                row.append(dy[yi - j])
            dep.append(dy[yi])
            X.append(row)
        dep, X = np.array(dep), np.array(X)
        b = p4.ols_coef(dep, X)
        _, se, _ = _ols_t(dep, X)
        tstat = float(b[2] / se[2])
        if tstat < best_t:
            best_t, best_tb = tstat, tb
    return float(best_t), best_tb


ADF_CV = {"c": (-3.43, -2.86, -2.57), "ct": (-3.96, -3.41, -3.12)}
DFGLS_CV = {"c": (-2.57, -1.94, -1.62), "ct": (-3.48, -2.89, -2.57)}
KPSS_CV = {"mu": (0.739, 0.463, 0.347), "tau": (0.216, 0.146, 0.119)}
ZA_CV = (-5.57, -5.08, -4.82)


def _verdict(stat, cv):
    return "reject H0 @5%" if stat < cv[1] else "not reject @5%"


def _kpss_verdict(stat, cv):
    return "reject H0 @5%" if stat > cv[1] else "not reject @5%"


def main():
    d = p4.load_data()
    series = {
        "SUR": d["sur"],
        "Range_C_F1": d["f1"],
        "Range_C_F2": d["f2"],
    }
    season = d["season"]

    print("=" * 82)
    print("A. First-difference short-run model  dRange_t = a + b*dSUR_t + QFE + e")
    print("=" * 82)
    for name in ("Range_C_F1", "Range_C_F2"):
        y = series[name]
        dy, ds = np.diff(y), np.diff(d["sur"])
        X = np.column_stack([np.ones(len(dy)), ds] + p4._season_cols(season[1:]))
        print(f"  --- {name} ---")
        for lag in (1, 4, 8):
            m = p4.ols_hac(dy, X, lag=lag)
            b, se, t, pv = m["beta"][1], m["se"][1], m["t"][1], m["p"][1]
            print(f"    HAC lag {lag}: b_dSUR={b:+.6f} se={se:.6f} "
                  f"t={t:.2f} p={pv:.4f} R2={m['r2']:.4f} n={m['n']}")
    print()

    print("=" * 82)
    print("B. Unit root / stationarity / endogenous-break diagnostics")
    print("=" * 82)
    print("Critical values are asymptotic; 'not reject' is not proof of a unit")
    print("root, and KPSS 'not reject' is not proof of stationarity.")
    print()

    for name, y in series.items():
        print(f"--- {name} (T={len(y)}) ---")
        a_c, p_c, n_c = adf_stat(y, trend=False)
        a_ct, p_ct, n_ct = adf_stat(y, trend=True)
        g_c, pg_c, _ = dfgls(y, trend=False)
        g_ct, pg_ct, _ = dfgls(y, trend=True)
        k_mu, l_mu = kpss(y, trend=False)
        k_tau, l_tau = kpss(y, trend=True)
        za, za_tb = zivot_andrews(y, p_ct)
        print(f"  ADF (const)       = {a_c:7.3f}  {_verdict(a_c, ADF_CV['c'])}  "
              f"lags={p_c} n={n_c}")
        print(f"  ADF (const+trend) = {a_ct:7.3f}  {_verdict(a_ct, ADF_CV['ct'])}  "
              f"lags={p_ct} n={n_ct}")
        print(f"  DF-GLS (const)    = {g_c:7.3f}  {_verdict(g_c, DFGLS_CV['c'])}  "
              f"lags={pg_c}")
        print(f"  DF-GLS (c+trend)  = {g_ct:7.3f}  {_verdict(g_ct, DFGLS_CV['ct'])}  "
              f"lags={pg_ct}")
        print(f"  KPSS level        = {k_mu:7.3f}  {_kpss_verdict(k_mu, KPSS_CV['mu'])}  "
              f"bandwidth={l_mu}")
        print(f"  KPSS trend        = {k_tau:7.3f}  {_kpss_verdict(k_tau, KPSS_CV['tau'])}  "
              f"bandwidth={l_tau}")
        print(f"  Zivot-Andrews C   = {za:7.3f}  {_verdict(za, ZA_CV)}  "
              f"break at obs {za_tb} ({d['time'][za_tb]})")
        print()

    print("=" * 82)
    print("Integration-order summary (for the cointegration decision)")
    print("=" * 82)
    print("Cointegration is only meaningful if SUR and a Range series are both")
    print("found I(1) under the diagnostics above.  It is not run automatically.")


if __name__ == "__main__":
    main()
