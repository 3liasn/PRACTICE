"""Construye las 'mangas' (sleeves) seleccionadas SOLO con IS (Sharpe IS >= 0.5) y guarda p (P&L diario) y mae (peor flotante) por unidad."""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from grid import build, ffill_flat
import sA_dailymr as A, sB_orb as B, s1_noise as N
S = {}   # nombre -> DataFrame(p, mae), familia
FAM = {}
def add(name, fam, dates, p, mae):
    df = pd.DataFrame({"p": p, "mae": np.minimum(mae, np.minimum(p, 0))}, index=pd.DatetimeIndex(dates)).fillna(0.0)
    S[name] = df[(df.p != 0) | (df.mae != 0)].groupby(level=0).sum(); FAM[name] = fam
# 1) Reversion IBS<0.2 larga, cierre->cierre, sin fin de semana
for inst in ["SPX500_USD", "NAS100_USD", "US2000_USD"]:
    tz, s0, s1 = A.SESS[inst]
    df = A.daily(inst); pos = A.variants(df)["ibs<0.2"]
    p = A.pnl_from_pos(df, pos, A.COST[inst], allow_weekend=False)
    dates, O, H, L, C, V = build(inst, tz); Cf = ffill_flat(C); di = {d: i for i, d in enumerate(dates)}
    mae = pd.Series(0.0, index=df.index)
    idx = df.index
    for k in range(len(idx) - 1):
        if pos.iloc[k] and (idx[k + 1] - idx[k]).days == 1:
            i = di[idx[k]]; j = di[idx[k + 1]]
            path = np.r_[Cf[i, s1:], Cf[j, :s1]] / Cf[i, s1 - 1] - 1
            mae.iloc[k + 1] = np.nanmin(path)
    add(f"MR_L {inst[:6]}", "MR indices", df.index, p.values, mae.values)
# 2) Reversion sobre barras 17:00 NY seleccionadas por IS>=0.5: cortos SPX/UK100/AU200 (ibs>0.8) y largo UK100 (ibs<0.2)
import sE_daily_all as E
for inst, side in [("SPX500_USD", -1), ("UK100_GBP", -1), ("AU200_AUD", -1), ("UK100_GBP", 1)]:
    df = E.dbars(inst); c = E.COST[inst] / 1e4
    ibs = (df.cs - df.l) / (df.h - df.l)
    pos = (-1.0 * (ibs > 0.8).astype(float)) if side < 0 else (ibs < 0.2).astype(float)
    nights = pd.Series((df.index[1:] - df.index[:-1]).days, index=df.index[:-1]).reindex(df.index).fillna(1)
    pos[nights > 1] = 0.0
    ret = df.c.pct_change().shift(-1); turn = pos.diff().abs().fillna(0)
    p = (pos * ret - turn * c / 2 - pos.abs() * nights * 1.5e-4).shift(1).fillna(0)
    dates, O, H, L, C, V = build(inst); Cf = ffill_flat(C); di = {d: i for i, d in enumerate(dates)}
    mae = pd.Series(0.0, index=df.index); idx = df.index
    for k in range(len(idx) - 1):
        if pos.iloc[k] != 0:
            i = di[idx[k]]; j = di[idx[k + 1]]
            path = side * (np.r_[Cf[i, 1015:], Cf[j, :1015]] / Cf[i, 1014] - 1); mae.iloc[k + 1] = np.nanmin(path)
    add(f"MR17_{'S' if side < 0 else 'L'} {inst[:6]}", "MR indices", df.index, p.values, mae.values)
# 3) LHH dia fuerte, 4) fade gap, 5) noise momentum
for inst, cb in [("SPX500_USD", 1.5), ("NAS100_USD", 1.5), ("US2000_USD", 3.0)]:
    dates, O, H, L, C, V = build(inst); Cf = ffill_flat(C); c = cb / 1e4; s0, s1 = 570, 960
    ok = (~np.isnan(C[:, s0:s1])).sum(1) >= 200
    pc = pd.Series(np.where(ok, Cf[:, s1 - 1], np.nan), index=dates).ffill().shift(1).values
    r_mid = Cf[:, 929] / pc - 1
    big = np.abs(r_mid) > pd.Series(np.abs(r_mid)).rolling(60).quantile(0.7).shift(1).values
    sgn = np.sign(r_mid)[:, None]
    path = sgn * (Cf[:, 930:960] / Cf[:, 930][:, None] - 1)
    tr = ok & ~np.isnan(pc) & big
    add(f"LHH {inst[:6]}", "LHH", dates, np.where(tr, path[:, -1] - c, 0), np.where(tr, path.min(1), 0))
    if inst != "SPX500_USD":
        gap = Cf[:, 569] / pc - 1; gthr = pd.Series(np.abs(gap)).rolling(60).quantile(0.7).shift(1).values
        path = -np.sign(gap)[:, None] * (Cf[:, 570:630] / Cf[:, 570][:, None] - 1)
        tr = ok & (np.abs(gap) > gthr)
        add(f"GAPF {inst[:6]}", "Gap fade", dates, np.where(tr, path[:, -1] - c, 0), np.where(tr, path.min(1), 0))
raw, levd, mae, ntr, lev = N.run("SPX500_USD", 1.5)
add("NOISE SPX500", "Momentum intradia", raw.index, raw.values, mae.values)
# 6) ORB (modo 1) ensemble de ventanas, en unidades de R
for inst, sess in [("EUR_USD", "LON8"), ("GBP_USD", "LON8"), ("XAU_USD", "LON3")]:
    ps = []; ms = []
    for W in (5, 15, 30, 60):
        d = B.run_one(inst, sess, W, 1)
        ps.append(d.R); ms.append((d.mae / d.risk.replace(0, np.nan)).fillna(0).clip(lower=-1.2))
    p = pd.concat(ps, axis=1).fillna(0).mean(1); m = pd.concat(ms, axis=1).fillna(0).mean(1)
    add(f"ORB {inst[:6]}", "ORB FX/oro", p.index, p.values, m.values)
# 7) estacionales
dates, O, H, L, C, V = build("XAU_USD"); Cf = ffill_flat(C); c = 1.5e-4
okx = (~np.isnan(C[:, 0:180])).sum(1) >= 60
prev = np.vstack([np.full((1, 355), np.nan), Cf[:-1, 1085:]])
path = np.hstack([prev, Cf[:, :180]]) / prev[:, :1] - 1
tr = okx & ~np.isnan(path[:, -1]) & (dates.dayofweek.values != 0)
add("XAU asia", "Estacional", dates, np.where(tr, path[:, -1] - c, 0), np.where(tr, np.nanmin(path, axis=1), 0))
dates, O, H, L, C, V = build("EUR_USD"); Cf = ffill_flat(C); c = 1.0e-4
oke = (~np.isnan(C[:, 300:480])).sum(1) >= 60
path = -(Cf[:, 359:420] / Cf[:, 359][:, None] - 1)
add("EUR 6-7", "Estacional", dates, np.where(oke, path[:, -1] - c, 0), np.where(oke, path.min(1), 0))
pd.to_pickle({"S": S, "FAM": FAM}, "out/sleeves.pkl")
def sh(x): return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else np.nan
cal = pd.bdate_range("2005-01-03", "2020-05-13")
rows = []
for k, d in S.items():
    x = d.p.reindex(cal).fillna(0)
    rows.append(dict(sleeve=k, fam=FAM[k], IS=sh(x[:"2012"]), OOS=sh(x["2013":]), vol_IS=x[:"2012"].std() * np.sqrt(252), dias_yr=(d.p != 0).sum() / 15.4))
print(pd.DataFrame(rows).round(3).to_string(index=False))
