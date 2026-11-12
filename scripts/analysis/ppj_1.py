import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pyfixest as pf

plt.rcParams.update({
    'figure.dpi': 150,
    'font.size': 9,
    'font.family': 'serif',
    'axes.linewidth': 0.8,
    'axes.spines.top': True,
    'axes.spines.right': True,
    'axes.grid': True,
    'grid.linestyle': '--',
    'grid.linewidth': 0.5,
    'grid.alpha': 0.25,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.major.size': 4,
    'ytick.major.size': 4,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'grid.alpha': 0.3,
    'grid.linestyle': '--',
    'legend.fontsize': 8,
    'lines.linewidth': 1.2,
})

df = pd.read_excel(
    "feed-grains-yearbook-all-years.xlsx",
    sheet_name="FGYearbookTable04",
    skiprows=1
)

df = df.iloc[:, :13]

inv = (
    df[["Marketing year", "Quarter 1/", "Total use 2/", "Ending stocks"]]
    .rename(columns={
        "Marketing year": "marketing_year",
        "Quarter 1/": "quarter",
        "Total use 2/": "Total_use",
        "Ending stocks": "Ending_stocks"
    })
)

inv["marketing_year"] = inv["marketing_year"].ffill()

inv = inv[inv["quarter"].str.match(r"^Q[1-4]", na=False)].copy()

inv["quarter"] = inv["quarter"].str.extract(r"(Q[1-4])")[0]

inv["Total_use"] = pd.to_numeric(inv["Total_use"], errors="coerce")
inv["Ending_stocks"] = pd.to_numeric(inv["Ending_stocks"], errors="coerce")

inv = inv.dropna(
    subset=["marketing_year", "quarter", "Total_use", "Ending_stocks"]
)

inv["quarter_num"] = inv["quarter"].str.extract(r"(\d)").astype(int)

annual_use = (
    inv.groupby("marketing_year", as_index=False)["Total_use"]
    .sum()
    .rename(columns={"Total_use": "Annual_use"})
)

inv = inv.merge(
    annual_use,
    on="marketing_year",
    how="left",
    validate="many_to_one"
)

inv["SUR"] = (
    inv["Ending_stocks"] / inv["Annual_use"]
)

inv["Time"] = (
    inv["marketing_year"]
    + inv["quarter"]
)

inv = (
    inv[
        [
            "Time",
            "marketing_year",
            "quarter",
            "Total_use",
            "Annual_use",
            "Ending_stocks",
            "SUR"
        ]
    ]
    .sort_values(["marketing_year", "quarter"])
    .reset_index(drop=True)
)
inv["SUR_lag1"] = inv["SUR"].shift(1)

bis = pd.read_csv("Grain_Basis_20261020.csv")
bis = bis[bis["Commodity"]=="Corn"]
bis["Date"] = pd.to_datetime(bis["Date"], format="%m/%d/%Y", errors="coerce")
bis["Commodity"] = bis["Commodity"].astype(str).str.strip()

bis["_start_month"] = 9
bis["_month"] = bis["Date"].dt.month.fillna(pd.to_numeric(bis["Month"], errors="coerce")).astype(int)
bis["_year"] = bis["Date"].dt.year.fillna(pd.to_numeric(bis["Year"], errors="coerce")).astype(int)

bis["_my_start"] = bis["_year"].where(
    bis["_month"] >= bis["_start_month"],
    bis["_year"] - 1
).astype(int)

bis["marketing_year"] = (
    bis["_my_start"].astype(str)
    + "/"
    + ((bis["_my_start"] + 1) % 100).astype(str).str.zfill(2)
)

bis["_offset"] = ((bis["_month"] - bis["_start_month"]) % 12) + 1
bis["quarter"] = "Q" + (((bis["_offset"] - 1) // 3) + 1).astype(int).astype(str)

bis["marketing_year"] = bis["marketing_year"].astype(str)
bis["quarter"] = bis["quarter"].astype(str)
inv["marketing_year"] = inv["marketing_year"].astype(str)
inv["quarter"] = inv["quarter"].astype(str)

data = bis.merge(
    inv[["Time", "marketing_year", "quarter",
         "SUR", "SUR_lag1"]],
    on=["marketing_year", "quarter"],
    how="inner"
)

data = data.sort_values(["marketing_year", "quarter"]).reset_index(drop=True)
keep = ["Date", "Market Name", "Market Type", "Commodity", "Location", "Latitude", "Longitude",
        "Source", "Bid", "Nearby Futures Month", "Futures Price", "Basis",
        "marketing_year", "quarter", "SUR", "SUR_lag1"]
df = data[keep].copy()
#print(data.head(5).to_latex())
#print(data.columns)
#

df["Date"]      = pd.to_datetime(df["Date"])
df["market_id"] = (df["Market Name"].astype(str).str.strip() + "|"
                 + df["Market Type"].astype(str).str.strip() + "|"
                 + df["Commodity"].astype(str).str.strip()     + "|"
                 + df["Location"].astype(str).str.strip())
df["myq"] = df["marketing_year"].astype(str) + df["quarter"].astype(str)
df["my"]  = df["marketing_year"].astype(str)
df["ym"]  = df["Date"].dt.to_period("M").astype(str)
df["nfm"] = df["Nearby Futures Month"].astype(str).str.strip()

df = df.drop(columns=["Time", "Annual_use", "Ending_stocks"], errors="ignore")

n_q = df.groupby("market_id")["myq"].nunique()
df  = df[df["market_id"].isin(n_q[n_q >= 20].index)].copy()

df["Basis_w"] = df.groupby(["Commodity", "nfm"])["Basis"].transform(
    lambda s: s.clip(s.quantile(0.01), s.quantile(0.99)))

panel = (df.groupby(["market_id", "Market Name", "Market Type", "Commodity",
                     "marketing_year", "quarter", "myq", "my"])
           .agg(Basis   = ("Basis",   "mean"),
                Basis_w = ("Basis_w", "mean"),
                SUR     = ("SUR",     "first"),
                SUR_lag1= ("SUR_lag1","first"),
                n_obs   = ("Basis",   "size"),
                n_days  = ("Date",    "nunique"),
                nfm_main= ("nfm", lambda x: x.mode().iloc[0] if len(x.mode()) else np.nan))
           .reset_index())

panel = panel.dropna(subset=["Basis_w", "SUR_lag1", "market_id", "myq"]).copy()
panel = panel.sort_values(["market_id", "marketing_year", "quarter"]).reset_index(drop=True)

thr_low = panel["SUR_lag1"].quantile(0.20)
panel["SUR_low"]      = (panel["SUR_lag1"] < thr_low).astype(int)
panel["SUR_lag1_low"] = panel["SUR_lag1"] * panel["SUR_low"]
panel["is_30d"]       = panel["Market Type"].str.lower().str.contains("30").astype(int)

#print("panel shape:", panel.shape,
#      "| 市场数:", panel["market_id"].nunique(),
#      "| 季度数:", panel["myq"].nunique())
#print(panel.groupby("myq")["SUR_lag1"].nunique().max())   # 必须为 1
#print(panel.groupby("my")["SUR_lag1"].nunique().describe())
#
#CL = {"CRV1": "market_id + myq"}
#
#m_base     = pf.feols("Basis_w ~ SUR_lag1 | market_id + my",                 data=panel, vcov=CL)
#m_base_nfm = pf.feols("Basis_w ~ SUR_lag1 | market_id + my + nfm_main",       data=panel, vcov=CL)
#m_het      = pf.feols("Basis_w ~ SUR_lag1 + SUR_lag1:is_30d | market_id + my", data=panel, vcov=CL)
#m_nl       = pf.feols("Basis_w ~ SUR_low + SUR_lag1_low | market_id + my",    data=panel, vcov=CL)
#m_qfe      = pf.feols("Basis_w ~ SUR_lag1:is_30d | market_id + myq",          data=panel,
#                      vcov={"CRV1": "market_id"})
#
#print(m_base.summary())
#print(m_base_nfm.summary())
#print(m_het.summary())
#print(m_nl.summary())
#print(m_qfe.summary())
#
#cover = panel.groupby("myq")["market_id"].nunique()
#print(cover.describe())
#
#full_ids = panel.groupby("market_id")["myq"].nunique()
#full_ids = full_ids[full_ids == panel["myq"].nunique()].index
#m_full   = pf.feols("Basis_w ~ SUR_lag1 | market_id + my",
#                    data=panel[panel["market_id"].isin(full_ids)], vcov=CL)
#print("全期连续市场数:", len(full_ids))
#print(m_full.summary())
#
#pf.etable([m_base, m_base_nfm, m_het, m_nl], type="df")
#panel["SUR_w"] = panel["SUR_lag1"] - panel.groupby(["market_id","my"])["SUR_lag1"].transform("mean")
#print("overall sd:", panel["SUR_lag1"].std(), "| within sd:", panel["SUR_w"].std())
#
#for c, sub in panel.groupby("Commodity"):
#    if len(sub) < 300: continue
#    m = pf.feols("Basis_w ~ SUR_lag1 | market_id + my", data=sub, vcov=CL)
#    print(c, len(sub), round(m.coef()["SUR_lag1"],3), round(m.se()["SUR_lag1"],3))
#
#print(pd.crosstab(panel["nfm_main"], panel["quarter"]))
#

#coords = (df.assign(Lat=pd.to_numeric(df["Latitude"], errors="coerce"),
#                    Lon=pd.to_numeric(df["Longitude"], errors="coerce"))
#          .groupby("market_id")[["Lat", "Lon"]].mean().reset_index())
#
#def haversine(lat1, lon1, lat2, lon2):
#    R = 3958.8
#    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
#    dlat, dlon = lat2 - lat1, lon2 - lon1
#    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
#    return 2 * R * np.arcsin(np.sqrt(a))
#
#GULF, CHICAGO, PNW = (29.95, -90.07), (41.88, -87.63), (46.20, -123.90)
#coords["Dist_Gulf"]    = haversine(coords["Lat"], coords["Lon"], *GULF)
#coords["Dist_Chicago"] = haversine(coords["Lat"], coords["Lon"], *CHICAGO)
#coords["Dist_PNW"]     = haversine(coords["Lat"], coords["Lon"], *PNW)
#for c in ["Dist_Gulf", "Dist_Chicago", "Dist_PNW"]:
#    coords[c + "_z"] = (coords[c] - coords[c].mean()) / coords[c].std()
#
#panel = panel.drop(columns=[c for c in ["Lat","Lon","Dist_Gulf","Dist_Chicago","Dist_PNW",
#                                        "Dist_Gulf_z","Dist_Chicago_z","Dist_PNW_z"]
#                            if c in panel.columns])
#panel = panel.merge(coords, on="market_id", how="left")
#
#print("\n[STEP 1] Destinations_i（到 Gulf/Chicago/PNW 距离，已标准化）")
#print(panel[["market_id","Market Type","Dist_Gulf","Dist_Chicago","Dist_PNW"]]
#      .drop_duplicates().to_string(index=False))
#
#CL2 = {"CRV1": "market_id + myq"}
#
#m_main = pf.feols("Basis_w ~ SUR_lag1 | market_id + my", data=panel, vcov=CL2)
#print("\n[STEP 2] 主模型: Basis_w ~ SUR_lag1 | market_id + my  [CRV1: market_id+myq]")
#print(m_main.summary())
#
#print("\n[STEP 3] Wild cluster bootstrap: param=SUR_lag1, cluster=market_id, B=999")
#try:
#    boot_main = pf.boottest(m_main, param="SUR_lag1", B=999, type="wild",
#                            cluster="market_id", seed=42)
#    print(boot_main)
#except Exception as e:
#    print("boottest 不可用:", e)
#
#print("\n[STEP 4] 分 Market Type: Basis_w ~ SUR_lag1 | market_id + my  [CRV1: market_id]")
#for k, sub in panel.groupby("Market Type"):
#    if sub["market_id"].nunique() >= 3 and len(sub) >= 100:
#        mm = pf.feols("Basis_w ~ SUR_lag1 | market_id + my",
#                      data=sub, vcov={"CRV1": "market_id"})
#        print(f"\n--- {k} | 市场数={sub['market_id'].nunique()} | N={len(sub)} ---")
#        print(mm.summary())
#
#print("\n[STEP 5] 第二模型(季度FE): Basis_w ~ SUR_lag1:{dvar} | market_id + myq  [仅交互项可识别]")
#for dvar in ["Dist_Gulf_z", "Dist_Chicago_z", "Dist_PNW_z"]:
#    mm = pf.feols(f"Basis_w ~ SUR_lag1:{dvar} | market_id + myq",
#                  data=panel, vcov={"CRV1": "market_id"})
#    print(f"\n--- Basis_w ~ SUR_lag1:{dvar} | market_id + myq ---")
#    print(mm.summary())
#
#print("\n[STEP 5b] 对照组(年度FE): Basis_w ~ SUR_lag1 + SUR_lag1:{dvar} | market_id + my")
#for dvar in ["Dist_Gulf_z", "Dist_Chicago_z", "Dist_PNW_z"]:
#    mm = pf.feols(f"Basis_w ~ SUR_lag1 + SUR_lag1:{dvar} | market_id + my",
#                  data=panel, vcov=CL2)
#    print(f"\n--- Basis_w ~ SUR_lag1 + SUR_lag1:{dvar} | market_id + my ---")
#    print(mm.summary())
#
#print("\n[STEP 6] 双重异质性: Market Type × 距离")
#for dvar in ["Dist_Gulf_z", "Dist_Chicago_z"]:
#    fml = (f"Basis_w ~ SUR_lag1 + SUR_lag1:is_30d + SUR_lag1:{dvar} "
#           f"+ SUR_lag1:is_30d:{dvar} | market_id + my")
#    try:
#        mm = pf.feols(fml, data=panel, vcov=CL2)
#        print(f"\n--- {fml} ---")
#        print(mm.summary())
#    except Exception as e:
#        print(f"\n--- {fml} 失败: {e}")
#
#full_ids = panel.groupby("market_id")["myq"].nunique()
#full_ids = full_ids[full_ids == panel["myq"].nunique()].index
#sub_full = panel[panel["market_id"].isin(full_ids)]
#print(f"\n[STEP 7] 全期连续子样本 (市场数={len(full_ids)}, N={len(sub_full)})")
#m_full = pf.feols("Basis_w ~ SUR_lag1 | market_id + my", data=sub_full, vcov=CL2)
#print(m_full.summary())
#

from formulaic.errors import FactorEvaluationError

DEST = {"Gulf": (29.95, -90.07), "Chicago": (41.88, -87.63), "PNW": (46.20, -123.90)}

def _hav(lat1, lon1, lat2, lon2):
    R = 3958.8
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def _mid(src):
    if "market_id" in src.columns:
        return src["market_id"].astype(str)
    return (src["Market Name"].astype(str).str.strip() + "|"
          + src["Market Type"].astype(str).str.strip() + "|"
          + src["Commodity"].astype(str).str.strip() + "|"
          + src["Location"].astype(str).str.strip())

def _latlon(src):
    lat = pd.to_numeric(src["Latitude"], errors="coerce") if "Latitude" in src.columns else pd.Series(np.nan, index=src.index)
    lon = pd.to_numeric(src["Longitude"], errors="coerce") if "Longitude" in src.columns else pd.Series(np.nan, index=src.index)
    if "Location" in src.columns:
        m = src["Location"].astype(str).str.extract(r"POINT\s*\(\s*([-\d\.]+)\s+([-\d\.]+)\s*\)")
        lon = lon.fillna(pd.to_numeric(m[0], errors="coerce"))
        lat = lat.fillna(pd.to_numeric(m[1], errors="coerce"))
    return lat, lon

def build_coords():
    for name in ["df", "data", "panel"]:
        src = globals().get(name)
        if not isinstance(src, pd.DataFrame):
            continue
        has_geo = any(c in src.columns for c in ["Latitude", "Longitude", "Location"])
        has_id  = "market_id" in src.columns or all(c in src.columns for c in ["Market Name", "Market Type", "Commodity", "Location"])
        if not (has_geo and has_id):
            continue
        s = src.reset_index(drop=True)
        lat, lon = _latlon(s)
        c = pd.DataFrame({"market_id": _mid(s).values, "Lat": lat.values, "Lon": lon.values})
        c = c.dropna(subset=["Lat", "Lon"]).groupby("market_id")[["Lat", "Lon"]].mean().reset_index()
        if len(c) == 0:
            continue
        for k, (la, lo) in DEST.items():
            c[f"Dist_{k}"] = _hav(c["Lat"], c["Lon"], la, lo)
        for k in DEST:
            c[f"Dist_{k}_z"] = (c[f"Dist_{k}"] - c[f"Dist_{k}"].mean()) / c[f"Dist_{k}"].std()
        print(f"[coords] 来源={name} | 市场数={len(c)}")
        return c
    raise RuntimeError("df/data/panel 均无可用经纬度列，请检查原始数据")

def ensure_dest(d, coords=None):
    need = [f"Dist_{k}{s}" for k in DEST for s in ["", "_z"]]
    if all(c in d.columns for c in need) and not d[need].isna().all().any():
        return d
    if coords is None:
        coords = globals().get("coords")
        if coords is None:
            coords = build_coords()
        globals()["coords"] = coords
    d = d.drop(columns=[c for c in need if c in d.columns], errors="ignore")
    out = d.merge(coords[["market_id"] + need].drop_duplicates("market_id"),
                  on="market_id", how="left")
    miss = set(out.loc[out[need].isna().all(axis=1), "market_id"])
    if miss:
        print("[warn] 未匹配到距离的市场:", miss)
    return out

panel = ensure_dest(panel)
print("\n[STEP 1] 距离列已就绪:")
print(panel[["market_id", "Dist_Gulf", "Dist_Chicago", "Dist_PNW"]].drop_duplicates().to_string(index=False))
print("缺失:", panel[["Dist_Gulf_z", "Dist_Chicago_z", "Dist_PNW_z"]].isna().sum().to_dict())

panel["SUR_PNW"]  = panel["SUR_lag1"] * panel["Dist_PNW_z"]
panel["SUR_CHI"]  = panel["SUR_lag1"] * panel["Dist_Chicago_z"]
panel["SUR_GULF"] = panel["SUR_lag1"] * panel["Dist_Gulf_z"]

def show(name, fml, d, vcov, terms):
    try:
        m = pf.feols(fml, data=d, vcov=vcov)
    except (ValueError, FactorEvaluationError, NameError) as e:
        msg = "被吸收" if "collinear" in str(e).lower() else f"失败:{type(e).__name__}"
        return pd.DataFrame([{"model": name, "term": t, "coef": msg, "p": "—"} for t in terms])
    out = []
    for t in terms:
        if t in m.coef().index:
            c = float(m.coef()[t]); p = float(m.pvalue()[t])
            if not np.isfinite(c) or not np.isfinite(p):
                out.append({"model": name, "term": t, "coef": "共线/不可识别", "p": "—"})
            else:
                out.append({"model": name, "term": t, "coef": round(c, 3), "p": round(p, 3)})
        else:
            out.append({"model": name, "term": t, "coef": "被吸收", "p": "—"})
    return pd.DataFrame(out)

CL  = {"CRV1": "market_id + myq"}
CLm = {"CRV1": "market_id"}
elev = panel[panel["Market Type"] == "Elevator Bid"]
d30  = panel[panel["Market Type"] == "30-Day to Arrive"]

rows = [
    show("M1 基准(年度FE)",        "Basis_w ~ SUR_lag1 | market_id + my",  panel, CL,  ["SUR_lag1"]),
    show("M2 基准(季度FE)",        "Basis_w ~ SUR_lag1 | market_id + myq", panel, CL,  ["SUR_lag1"]),
    show("M3 Elevator",           "Basis_w ~ SUR_lag1 | market_id + my",  elev,  CLm, ["SUR_lag1"]),
    show("M4 30-Day",             "Basis_w ~ SUR_lag1 | market_id + my",  d30,   CLm, ["SUR_lag1"]),
    show("M5 SUR×PNW(季度FE)",     "Basis_w ~ SUR_PNW | market_id + myq",  panel, CLm, ["SUR_PNW"]),
    show("M6 SUR×Chicago(季度FE)", "Basis_w ~ SUR_CHI | market_id + myq",  panel, CLm, ["SUR_CHI"]),
    show("M7 SUR×Gulf(季度FE)",    "Basis_w ~ SUR_GULF | market_id + myq", panel, CLm, ["SUR_GULF"]),
]
res = pd.concat(rows, ignore_index=True)
print("\n[RESULTS]")
print(res.to_string(index=False))

CL2 = {"CRV1": "market_id + myq"}
for dv in ["Dist_PNW_z", "Dist_Chicago_z", "Dist_Gulf_z"]:
    m = pf.feols(f"Basis_w ~ SUR_lag1:{dv} | market_id + myq", data=panel, vcov=CL2)
    print(dv, m.coef()[f"SUR_lag1:{dv}"], m.pvalue()[f"SUR_lag1:{dv}"])

d = panel.copy()
d["SUR_GULF"]  = d["SUR_lag1"] * d["Dist_Gulf_z"]
d["SUR_CHI"]   = d["SUR_lag1"] * d["Dist_Chicago_z"]
d["SUR_PNW"]   = d["SUR_lag1"] * d["Dist_PNW_z"]

print(d[["Dist_Gulf_z","Dist_Chicago_z","Dist_PNW_z"]].corr().round(2))
print(d[["SUR_GULF","SUR_CHI","SUR_PNW"]].corr().round(2))

g = d.groupby("my")["SUR_GULF"].nunique()
print("SUR_GULF 在年度内唯一值数:\n", g.describe())

d = panel.copy()
for dv in ["Dist_PNW_z", "Dist_Chicago_z"]:
    d[f"SUR_{dv}"] = d["SUR_lag1"] * d[dv]
    d[f"SUR_{dv}_dm"] = d[f"SUR_{dv}"] - d.groupby("myq")[f"SUR_{dv}"].transform("mean")
    m = pf.feols(f"Basis_w ~ SUR_{dv}_dm | market_id + myq", data=d, vcov={"CRV1": "market_id"})
    print(dv, m.coef()[f"SUR_{dv}_dm"], m.pvalue()[f"SUR_{dv}_dm"])
CL2 = {"CRV1": "market_id + myq"}
d   = panel.copy()

print("[A] 去掉 Gulf-Louisiana 后 Gulf 交互项")
d_no_gulf = d[~d["market_id"].str.startswith("Gulf - Louisiana")]
for dv in ["Dist_Gulf_z", "Dist_PNW_z", "Dist_Chicago_z"]:
    m = pf.feols(f"Basis_w ~ SUR_lag1:{dv} | market_id + myq", data=d_no_gulf, vcov=CL2)
    print(f"  {dv}: coef={m.coef()[f'SUR_lag1:{dv}']:.4f}, p={m.pvalue()[f'SUR_lag1:{dv}']:.4f}")

print("[B] Gulf 距离换成二元 is_Gulf = Dist_Gulf < 300")
d["is_Gulf"] = (d["Dist_Gulf"] < 300).astype(int)
m = pf.feols("Basis_w ~ SUR_lag1:is_Gulf | market_id + myq", data=d, vcov=CL2)
print(m.summary())

print("[C] 杠杆值 (hat values)，M7 模型")
m7 = pf.feols("Basis_w ~ SUR_lag1:Dist_Gulf_z | market_id + myq", data=d, vcov=CL2)
try:
    lev = m7._data[["market_id", "myq"]].copy()
    lev["hat"] = pd.Series(m7._hat if hasattr(m7, "_hat") else None, index=d.index)
    print(lev.sort_values("hat", ascending=False).head(10).to_latex())
except Exception as e:
    print("  hat 不可直接取，改用 leave-one-market-out:")
    for mid in d["market_id"].unique():
        sub = d[d["market_id"] != mid]
        try:
            mm = pf.feols("Basis_w ~ SUR_lag1:Dist_Gulf_z | market_id + myq", data=sub, vcov=CL2)
            print(f"  drop {mid[:40]:40s} coef={mm.coef()['SUR_lag1:Dist_Gulf_z']:+.4f} "
                  f"p={mm.pvalue()['SUR_lag1:Dist_Gulf_z']:.3f}")
        except Exception:
            pass
