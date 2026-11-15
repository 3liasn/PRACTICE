"""Varias familias en forma de 'ventana horaria' con senal conocida a la entrada. P&L por unidad de nocional."""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from grid import build, ffill_flat
US = ["SPX500_USD", "NAS100_USD", "US2000_USD"]; COST = {"SPX500_USD": 1.5, "NAS100_USD": 1.5, "US2000_USD": 3.0, "XAU_USD": 1.5, "EUR_USD": 1.0, "GBP_USD": 1.2, "AUD_USD": 1.2, "USD_CAD": 1.3, "EUR_JPY": 1.5, "AUD_JPY": 1.8, "WTICO_USD": 5.0}
def sh(x):
    x = x[~np.isnan(x)]; return x.mean() / x.std() * np.sqrt(252) if len(x) > 50 and x.std() > 0 else np.nan
OUT = {}; rows = []
def rec(name, dates, pnl, traded):
    s = pd.Series(np.where(traded, pnl, 0.0), index=dates); OUT[name] = s
    a, b = s[:"2012"], s["2013":]; ta, tb = traded[dates.year <= 2012], traded[dates.year >= 2013]
    rows.append(dict(name=name, IS_sh=sh(a.values), OOS_sh=sh(b.values), IS_bps=a[ta].mean() * 1e4, OOS_bps=b[tb].mean() * 1e4, n_yr=traded.sum() / 15.4))
for inst in US:
    dates, O, H, L, C, V = build(inst); Cf = ffill_flat(C); c = COST[inst] / 1e4
    s0, s1 = 570, 960
    ok = (~np.isnan(C[:, s0:s1])).sum(1) >= 200
    okn = (~np.isnan(C[:, 120:180])).sum(1) >= 20
    h = np.nanmax(H[:, s0:s1 - 5], axis=1); l = np.nanmin(L[:, s0:s1 - 5], axis=1)
    ibs = (Cf[:, s1 - 6] - l) / (h - l)
    # ibs de la sesion previa (ultimo dia de sesion valido anterior)
    ibs_prev = pd.Series(np.where(ok, ibs, np.nan), index=dates).ffill().shift(1).values
    # 1) deriva 02:00-03:00 NY
    r = Cf[:, 179] / Cf[:, 119] - 1 - c
    rec(f"{inst[:6]} 2-3am todos", dates, r, okn)
    rec(f"{inst[:6]} 2-3am ibs<0.2", dates, r, okn & (ibs_prev < 0.2))
    rec(f"{inst[:6]} 2-3am ibs<0.3", dates, r, okn & (ibs_prev < 0.3))
    r = Cf[:, 239] / Cf[:, 89] - 1 - c
    rec(f"{inst[:6]} 1:30-4am ibs<0.2", dates, r, okn & (ibs_prev < 0.2))
    # 2) 18:00 -> 03:00 tras cierre debil (sin swap: entra despues del rollover de las 17:00). La ventana cruza medianoche: precio 18:00 del dia previo
    p18 = np.r_[np.nan, Cf[:-1, 1080]]
    r = Cf[:, 179] / p18 - 1 - c
    rec(f"{inst[:6]} 18h-3am ibs<0.2", dates, r, okn & (ibs_prev < 0.2) & ~np.isnan(p18))
    # 3) Momentum ultima media hora (Gao et al.): signo del retorno hasta 15:30 (desde cierre previo)
    pc = pd.Series(np.where(ok, Cf[:, s1 - 1], np.nan), index=dates).ffill().shift(1).values
    r_first = Cf[:, 599] / pc - 1; r_mid = Cf[:, 929] / pc - 1
    last = Cf[:, 959] / Cf[:, 930] - 1
    rec(f"{inst[:6]} LHH signo 1a media hora", dates, np.sign(r_first) * last - c, ok & ~np.isnan(pc))
    rec(f"{inst[:6]} LHH signo dia hasta 15:30", dates, np.sign(r_mid) * last - c, ok & ~np.isnan(pc))
    big = np.abs(r_mid) > pd.Series(np.abs(r_mid)).rolling(60).quantile(0.7).shift(1).values
    rec(f"{inst[:6]} LHH dia fuerte (top30%)", dates, np.sign(r_mid) * last - c, ok & ~np.isnan(pc) & big)
    # 4) Gap: fade del gap de apertura hasta las 10:30 / continuacion
    gap = Cf[:, 569] / pc - 1; gthr = pd.Series(np.abs(gap)).rolling(60).quantile(0.7).shift(1).values
    r = -(np.sign(gap)) * (Cf[:, 629] / Cf[:, 570] - 1) - c
    rec(f"{inst[:6]} fade gap grande 9:31-10:30", dates, r, ok & (np.abs(gap) > gthr))
    # 5) cambio de mes: largo desde cierre del ultimo dia habil hasta cierre del 3er dia habil (retorno diario cierre-cierre)
    d = pd.Series(np.where(ok, Cf[:, s1 - 1], np.nan), index=dates).dropna()
    ret = d.pct_change()
    mo = d.index.to_period("M"); pos_in_month = pd.Series(1, index=d.index).groupby(mo).cumsum()
    tom = (pos_in_month <= 3)
    p = (ret - 2e-4 * 1.45).where(tom, 0.0); p[pos_in_month == 1] -= c    # swap ~2bps/noche natural, coste una vez
    s = p.reindex(dates).fillna(0.0); tr = tom.reindex(dates).fillna(False).values
    rec(f"{inst[:6]} cambio de mes (3d)", dates, s.values, tr)
# 6) Oro: sesgo asiatico (largo 18:00 -> 01:00/03:00 NY) y corto manana Londres
dates, O, H, L, C, V = build("XAU_USD"); Cf = ffill_flat(C); c = COST["XAU_USD"] / 1e4
okx = (~np.isnan(C[:, 0:180])).sum(1) >= 60
p18 = np.r_[np.nan, Cf[:-1, 1085]]
for nm, b in [("18:05-21:00", None), ("18:05-01:00", 59), ("18:05-03:00", 179)]:
    if b is None: r = np.r_[np.nan, Cf[:-1, 1259] / Cf[:-1, 1085]] - 1 - c
    else: r = Cf[:, b] / p18 - 1 - c
    rec(f"XAU largo {nm}", dates, r, okx & ~np.isnan(r) & (dates.dayofweek.values != 0))
r = -(Cf[:, 359] / Cf[:, 299] - 1) - c
rec("XAU corto 05-06 NY", dates, r, okx)
r = -(Cf[:, 599] / Cf[:, 239] - 1) - c
rec("XAU corto 04-10 NY", dates, r, okx)
# 7) EURUSD corto 06-07 NY ; largo 21-23
dates, O, H, L, C, V = build("EUR_USD"); Cf = ffill_flat(C); c = COST["EUR_USD"] / 1e4
oke = (~np.isnan(C[:, 300:480])).sum(1) >= 60
rec("EUR corto 06-07 NY", dates, -(Cf[:, 419] / Cf[:, 359] - 1) - c, oke)
rec("EUR corto 03-07 NY", dates, -(Cf[:, 419] / Cf[:, 179] - 1) - c, oke)
df = pd.DataFrame(rows)
with pd.option_context("display.width", 200, "display.float_format", "{:.2f}".format, "display.max_rows", 200):
    print(df.to_string(index=False))
pd.to_pickle(OUT, "out/sD.pkl")
