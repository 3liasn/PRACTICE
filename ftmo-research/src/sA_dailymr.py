"""Reversion a la media diaria en indices (IBS / RSI2 / dias bajistas consecutivos). Senal 5 min antes del cierre de contado,
ejecucion al cierre. Incluye coste de spread y swap por noche natural."""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd
from common import stats, show
from grid import build, ffill_flat
SESS = {  # instrumento: (tz, apertura, cierre) en minutos locales
    "SPX500_USD": ("America/New_York", 570, 960), "NAS100_USD": ("America/New_York", 570, 960), "US2000_USD": ("America/New_York", 570, 960),
    "UK100_GBP": ("Europe/London", 480, 990), "FR40_EUR": ("Europe/Paris", 540, 1050), "NL25_EUR": ("Europe/Paris", 540, 1050),
    "JP225_USD": ("Asia/Tokyo", 540, 900), "AU200_AUD": ("Australia/Sydney", 600, 960)}
COST = {"SPX500_USD": 1.5, "NAS100_USD": 1.5, "US2000_USD": 3.0, "UK100_GBP": 2.0, "FR40_EUR": 2.5, "NL25_EUR": 3.0, "JP225_USD": 2.5, "AU200_AUD": 3.0}
SWAP_BPS = 2.0  # por noche natural, posiciones largas en indices (~7%/ano)
def daily(inst):
    tz, s0, s1 = SESS[inst]
    dates, O, H, L, C, V = build(inst, tz)
    Cf = ffill_flat(C)
    ok = (~np.isnan(C[:, s0:s1])).sum(1) >= 120
    sig_end = s1 - 5
    o = np.where(np.isnan(O[:, s0]), Cf[:, s0], O[:, s0])
    h = np.nanmax(np.where(np.isnan(H[:, s0:sig_end]), -np.inf, H[:, s0:sig_end]), axis=1)
    l = np.nanmin(np.where(np.isnan(L[:, s0:sig_end]), np.inf, L[:, s0:sig_end]), axis=1)
    df = pd.DataFrame({"o": o, "h": h, "l": l, "cs": Cf[:, sig_end - 1], "c": Cf[:, s1 - 1]}, index=dates)[ok]
    return df
def rsi(c, n=2):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)
def pnl_from_pos(df, pos, cost_bps, allow_weekend=True):
    """pos_t decidida en el cierre t, mantenida hasta el cierre t+1."""
    pos = pos.astype(float).copy()
    nights = pd.Series((df.index[1:] - df.index[:-1]).days, index=df.index[:-1]).reindex(df.index).fillna(1)
    if not allow_weekend:
        pos[nights > 1] = 0.0   # no mantener en fin de semana/festivo
    ret = df.c.pct_change().shift(-1)            # retorno de cierre t a cierre t+1
    turn = pos.diff().abs().fillna(pos.abs())
    p = pos * ret - turn * cost_bps / 2e4 - pos.abs() * nights * SWAP_BPS / 1e4
    p = p.shift(1).fillna(0.0)                   # se realiza en t+1
    return p
def variants(df):
    cs, c = df.cs, df.c
    ibs = (cs - df.l) / (df.h - df.l).replace(0, np.nan)
    sma200 = cs.rolling(200).mean()
    out = {}
    out["ibs<0.2"] = (ibs < 0.2)
    out["ibs<0.2&>sma200"] = (ibs < 0.2) & (cs > sma200)
    r2 = rsi(cs, 2)
    # RSI2<10 entra; sale cuando cierra sobre SMA5
    sma5 = cs.rolling(5).mean(); st = np.zeros(len(df)); cur = 0
    r2v, csv, s5 = r2.values, cs.values, sma5.values
    for i in range(len(df)):
        if cur == 0 and r2v[i] < 10: cur = 1
        elif cur == 1 and csv[i] > s5[i]: cur = 0
        st[i] = cur
    out["rsi2<10"] = pd.Series(st, index=df.index) > 0
    dn = (cs < c.shift(1)); d3 = dn & dn.shift(1).fillna(False) & dn.shift(2).fillna(False)
    st = np.zeros(len(df)); cur = 0; d3v = d3.values; up = (cs > c.shift(1)).values
    for i in range(len(df)):
        if cur == 0 and d3v[i]: cur = 1
        elif cur == 1 and up[i]: cur = 0
        st[i] = cur
    out["3down"] = pd.Series(st, index=df.index) > 0
    return out
if __name__ == "__main__":
    rows = []; allp = {}
    for inst in SESS:
        df = daily(inst)
        for nm, pos in variants(df).items():
            for wk in [True, False]:
                p = pnl_from_pos(df, pos, COST[inst], allow_weekend=wk)
                allp[(inst, nm, wk)] = p
                for lab, a, b in [("IS", "2005", "2012"), ("OOS", "2013", "2020")]:
                    r = stats(p[a:b], f"{inst[:6]} {nm} wk{int(wk)} {lab}"); r["expo"] = pos[a:b].mean(); rows.append(r)
    R = pd.DataFrame(rows)
    with pd.option_context("display.width", 250, "display.float_format", "{:.3f}".format, "display.max_rows", 500):
        print(R[["name", "ann", "vol", "sharpe", "maxdd", "expo"]].to_string(index=False))
    pd.to_pickle(allp, "out/sA.pkl")
