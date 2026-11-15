"""Barras diarias (cierre 17:00 NY, senal 16:50, ejecucion 16:55) para los 25 instrumentos: reversion IBS y tendencia (TSMOM)."""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd, warnings, os
warnings.filterwarnings("ignore")
from grid import build, ffill_flat
from common import stats
ALL = sorted(f[:-11] for f in os.listdir("data") if f.endswith("_M1.parquet"))
COST = {"SPX500_USD": 1.5, "NAS100_USD": 1.5, "US2000_USD": 3, "UK100_GBP": 2, "FR40_EUR": 2.5, "NL25_EUR": 3, "JP225_USD": 2.5, "AU200_AUD": 3, "XAU_USD": 1.5,
        "WTICO_USD": 5, "NATGAS_USD": 15, "EUR_USD": 1, "GBP_USD": 1.2, "AUD_USD": 1.2, "USD_CAD": 1.3, "EUR_JPY": 1.5, "AUD_JPY": 1.8, "USB10Y_USD": 2, "USB02Y_USD": 2,
        "DE10YB_EUR": 2, "UK10YB_GBP": 3, "CORN_USD": 15, "WHEAT_USD": 15, "SOYBN_USD": 12, "SUGAR_USD": 20}
def sh(x):
    x = x.dropna(); return x.mean() / x.std() * np.sqrt(252) if len(x) > 100 and x.std() > 0 else np.nan
def dbars(inst):
    dates, O, H, L, C, V = build(inst); Cf = ffill_flat(C)
    n = len(dates)
    ok = (~np.isnan(C)).sum(1) >= 120
    Hn = np.where(np.isnan(H), -np.inf, H); Ln = np.where(np.isnan(L), np.inf, L)
    h = np.maximum(Hn[:, :1010].max(1), np.r_[-np.inf, Hn[:-1, 1020:].max(1)])
    l = np.minimum(Ln[:, :1010].min(1), np.r_[np.inf, Ln[:-1, 1020:].min(1)])
    df = pd.DataFrame({"h": h, "l": l, "cs": Cf[:, 1009], "c": Cf[:, 1014]}, index=dates)[ok]
    return df[np.isfinite(df.h) & np.isfinite(df.l) & (df.h > df.l)]
if __name__ == "__main__":
    rows = []; MR = {}; TF = {}
    for inst in ALL:
        df = dbars(inst); c = COST[inst] / 1e4
        ret = df.c.pct_change().shift(-1)
        nights = pd.Series((df.index[1:] - df.index[:-1]).days, index=df.index[:-1]).reindex(df.index).fillna(1)
        ibs = (df.cs - df.l) / (df.h - df.l)
        for nm, pos in [("MR largo ibs<0.2", (ibs < 0.2) * 1.0), ("MR corto ibs>0.8", -1.0 * (ibs > 0.8).astype(float))]:
            turn = pos.diff().abs().fillna(0)
            p = (pos * ret - turn * c / 2 - pos.abs() * nights * 1.5e-4).shift(1).fillna(0)
            MR[(inst, nm)] = p
            rows.append(dict(inst=inst, strat=nm, IS=sh(p[:"2012"]), OOS=sh(p["2013":])))
        # tendencia
        sig = sum(np.sign(df.cs / df.cs.shift(Lb) - 1) for Lb in (20, 60, 120, 250)) / 4
        vol = df.c.pct_change().rolling(60).std().shift(1) * np.sqrt(252)
        pos = (sig * 0.10 / vol).clip(-3, 3).fillna(0)
        turn = pos.diff().abs().fillna(0)
        p = (pos * ret - turn * c / 2 - pos.abs() * nights * 1.0e-4).shift(1).fillna(0)
        TF[inst] = p
        rows.append(dict(inst=inst, strat="TSMOM", IS=sh(p[:"2012"]), OOS=sh(p["2013":])))
    df = pd.DataFrame(rows).pivot(index="inst", columns="strat", values=["IS", "OOS"]).round(2)
    print(df.to_string())
    tf = pd.DataFrame(TF).fillna(0).mean(axis=1)
    for lab, a, b in [("IS", "2005", "2012"), ("OOS", "2013", "2020")]:
        s = stats(tf[a:b]); print(f"TSMOM cartera 25 inst {lab}: sharpe {s['sharpe']:.2f} ann {s['ann']:.3f} vol {s['vol']:.3f} maxdd {s['maxdd']:.3f}")
    pd.to_pickle({"MR": MR, "TF": TF}, "out/sE.pkl")
