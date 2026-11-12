import numpy as np
import pandas as pd
import matplotlib as plt

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

price = pd.read_csv("CHRIS-CME_C1.csv")
price["Date"] = pd.to_datetime(price["Date"])
price = price.sort_values("Date").reset_index(drop=True)

price["log_ret"] = np.log(price["Settle"]).diff()

price["month"] = price["Date"].dt.month
price["day"] = price["Date"].dt.day


in_window = price["month"].isin([3, 5, 7, 9, 12]) & price["day"].between(15, 25)
thr_in  = 0.020
thr_out = 0.060
thr = np.where(in_window, thr_in, thr_out)
price["is_roll"] = price["log_ret"].abs() > thr
price["is_roll"] = price["is_roll"] & in_window


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
    (year - 1).astype(str) + "/" + (year % 100).astype(str).str.zfill(2)
)

quarter_map = {
    9: "Q1", 10: "Q1", 11: "Q1",
    12: "Q2", 1: "Q2", 2: "Q2",
    3: "Q3", 4: "Q3", 5: "Q3",
    6: "Q4", 7: "Q4", 8: "Q4"
}
price["quarter"] = price["Date"].dt.month.map(quarter_map)

rv = (
    price.groupby(["marketing_year", "quarter"])
    .agg(
        RV=("log_ret_adj", lambda x: np.sqrt(np.sum(x.dropna() ** 2))),
        n_days=("log_ret_adj", "count"),
        n_rolls=("is_roll", "sum")
    )
    .reset_index()
)

rv["is_valid"] = rv["n_days"] >= 55
rv = rv[rv["is_valid"]].copy()

data = rv.merge(
    inv[["Time", "marketing_year", "quarter",
         "Annual_use", "Ending_stocks", "SUR"]],
    on=["marketing_year", "quarter"],
    how="inner"
)

data = data.sort_values(["marketing_year", "quarter"]).reset_index(drop=True)

data["SUR_lag1"] = data["SUR"].shift(1)
data["RV_lag1"] = data["RV"].shift(1)

import statsmodels.formula.api as smf
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller
from statsmodels.stats.diagnostic import het_arch
#from arch import arch_model

supply_demand = ['Annual_use', 'Ending_stocks']

data = data[data['is_valid'].astype(str).str.lower().isin(['true', '1', 'yes', 'y'])].copy()

data['marketing_year_num'] = pd.to_numeric(
    data['marketing_year'].astype(str).str.extract(r'(\d+)')[0],
    errors='coerce'
)
data['quarter_num'] = pd.to_numeric(
    data['quarter'].astype(str).str.extract(r'(\d)')[0],
    errors='coerce'
)
data['time_id'] = data['marketing_year_num'] * 4 + data['quarter_num']
data = data.sort_values('time_id').set_index('time_id')
full_index = pd.Index(range(int(data.index.min()), int(data.index.max()) + 1), name='time_id')
data = data.reindex(full_index).reset_index()
data['quarter_num'] = ((data['time_id'] - 1) % 4) + 1
data['quarter'] = data['quarter_num'].astype(int).astype(str)

data['SUR_lag1'] = data['SUR'].shift(1)




def load_cc(path, name):
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={'Date':'date','Price':'close','Open':'open',
                            'High':'high','Low':'low','Vol.':'volume','Change %':'chg'})
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date','close']).sort_values('date').drop_duplicates('date').set_index('date')
    df = df[['open','high','low','close','volume']].apply(pd.to_numeric, errors='coerce')
    df = df[~df['close'].isna() & (df['close'] > 0)]
    df.columns = [f'{name}_{c}' for c in df.columns]
    return df

c1 = load_cc('Cc1.csv','c1')
c2 = load_cc('Cc2.csv','c2')
c3 = load_cc('Cc3.csv','c3')
panel = pd.concat([c1,c2,c3], axis=1).sort_index()

for c in ['c1','c2','c3']:
    panel[f'r_{c}'] = np.log(panel[f'{c}_close']).diff()

def roll_flag(close, vol, k=5, win=21):
    r = np.log(close).diff().abs()
    med = r.rolling(win, min_periods=10).median()
    voljump = vol.pct_change().abs()
    volmed = voljump.rolling(win, min_periods=10).median()
    flag = ((r > k * med) & med.notna()) | ((voljump > k * volmed) & volmed.notna())
    return flag.fillna(False)

panel['roll_c1'] = roll_flag(panel['c1_close'], panel['c1_volume'])
panel['roll_c2'] = roll_flag(panel['c2_close'], panel['c2_volume'])
panel['roll_c3'] = roll_flag(panel['c3_close'], panel['c3_volume'])

for c in ['c1','c2','c3']:
    panel[f'r_{c}_clean'] = panel[f'r_{c}'].where(~panel[f'roll_{c}'])

def parkinson(high, low):
    x = (np.log(high / low) ** 2) / (4 * np.log(2))
    return x.where(x > 0).clip(upper=0.02)

def garman_klass(open_, high, low, close):
    x = 0.5 * (np.log(high / low) ** 2) - (2 * np.log(2) - 1) * (np.log(close / open_) ** 2)
    return x.where(x > 0).clip(upper=0.02)

panel['pk_c1'] = parkinson(panel['c1_high'], panel['c1_low'])
panel['gk_c1'] = garman_klass(panel['c1_open'], panel['c1_high'], panel['c1_low'], panel['c1_close'])

def my_q(d):
    m, y = d.month, d.year
    if m in (9, 10, 11): return y, 1
    if m == 12: return y, 2
    if m in (1, 2): return y - 1, 2
    if m in (3, 4, 5): return y - 1, 3
    if m in (6, 7, 8): return y - 1, 4
    return np.nan, np.nan

myq = panel.index.to_series().apply(my_q)
panel['marketing_year'] = [x[0] for x in myq]
panel['quarter'] = [x[1] for x in myq]

agg = panel.groupby(['marketing_year','quarter']).agg(
    RV_c1_close = ('r_c1_clean', lambda x: np.sqrt(np.nansum(x**2))),
    RV_c1_close_var = ('r_c1_clean', lambda x: np.nansum(x**2)),
    RV_c1_pk = ('pk_c1', lambda x: np.nansum(x)),
    RV_c1_gk = ('gk_c1', lambda x: np.nansum(x)),
    n_obs = ('r_c1_clean', 'count'),
    n_roll = ('roll_c1', 'sum'),
).reset_index()

agg['RV_c1_close_var'] = agg['RV_c1_close_var'].where(agg['n_obs'] >= 15)
agg['RV_c1_pk']        = agg['RV_c1_pk'].where(agg['n_obs'] >= 15)
agg['RV_c1_gk']        = agg['RV_c1_gk'].where(agg['n_obs'] >= 15)
agg['RV_c1_close'] = agg['RV_c1_close'].where(agg['n_obs'] >= 15)

print(agg[['RV_c1_close','RV_c1_close_var','RV_c1_pk','RV_c1_gk']].describe().round(6))
print(agg[agg['n_obs'] < 15][['marketing_year','quarter','n_obs','RV_c1_close']])

print(agg.head(12))
print(agg['n_roll'].describe())
print(agg[['RV_c1_close_var','RV_c1_pk','RV_c1_gk']].describe().round(6))

print(agg[['RV_c1_close_var','RV_c1_pk','RV_c1_gk']].corr().round(3))

main = data.copy()
main['marketing_year'] = main['marketing_year'].astype(str).str.extract(r'(\d{4})')[0].astype('Int64')
main['quarter'] = pd.to_numeric(main['quarter'].astype(str).str.extract(r'(\d)')[0], errors='coerce').astype('Int64')
main = main.merge(agg, on=['marketing_year','quarter'], how='left')
print(main[['marketing_year','quarter','RV','RV_c1_close_var','RV_c1_pk','RV_c1_gk','n_obs','n_roll']].head())

zero_roll = agg[agg['n_roll'] == 0][['marketing_year','quarter','n_obs']]
print(zero_roll.head(20))
print('n_obs 分布:', zero_roll['n_obs'].describe())

check = main.dropna(subset=['RV','RV_c1_close_var'])[['RV','RV_c1_close','RV_c1_close_var','RV_c1_pk','RV_c1_gk']]
print(check.corr().round(3))
print(check.describe().round(6))

agg = agg.where(agg['n_obs'] >= 15)

main = data.copy()
main['marketing_year'] = main['marketing_year'].astype(str).str.extract(r'(\d{4})')[0].astype('Int64')
main['quarter'] = pd.to_numeric(main['quarter'].astype(str).str.extract(r'(\d)')[0], errors='coerce').astype('Int64')

main = main.merge(
    agg[['marketing_year','quarter','RV_c1_close','RV_c1_close_var',
         'RV_c1_pk','RV_c1_gk','n_obs','n_roll']],
    on=['marketing_year','quarter'], how='left')

main = main.sort_values(['marketing_year','quarter']).reset_index(drop=True)
print(main[['marketing_year','quarter','RV','RV_c1_close','RV_c1_close_var',
            'RV_c1_pk','RV_c1_gk','n_obs','n_roll']].head(20))
print(main[['RV','RV_c1_close_var','RV_c1_pk','RV_c1_gk']].corr().round(3))
