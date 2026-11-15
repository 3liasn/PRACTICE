"""Momentum intradia con 'area de ruido' (Zarattini, Aziz, Barbon 2024) sobre indices USA (CFD)."""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd, numba as nb
from common import stats, show
from grid import build, ffill_flat

@nb.njit(cache=True)
def sim(O, C, V, valid, lookback, step, vm, cost, use_vwap, s0, s1):
    """O,C,V: [dias, 1440] ya ffilled (C) ; sesion [s0, s1) en minutos del dia. Devuelve pnl diario por unidad de nocional,
    peor flotante intradia, n trades."""
    nd = O.shape[0]; n = s1 - s0
    pnl = np.zeros(nd); mae = np.zeros(nd); ntr = np.zeros(nd)
    move = np.full((nd, n), np.nan)
    prev_close = np.nan
    for t in range(nd):
        if not valid[t]:
            continue
        op = O[t, s0]
        if np.isnan(op): op = C[t, s0]
        for i in range(n):
            move[t, i] = abs(C[t, s0 + i] / op - 1.0)
        # sigma: media de los ultimos `lookback` dias validos
        cnt = 0; k = t - 1
        sig = np.zeros(n)
        while k >= 0 and cnt < lookback:
            if valid[k]:
                for i in range(n): sig[i] += move[k, i]
                cnt += 1
            k -= 1
        if cnt < lookback or np.isnan(prev_close):
            prev_close = C[t, s1 - 1]; continue
        for i in range(n): sig[i] /= cnt
        hi = max(op, prev_close); lo = min(op, prev_close)
        pos = 0; entry = 0.0; day = 0.0; worst = 0.0
        pv = 0.0; vv = 0.0
        for i in range(n):
            c = C[t, s0 + i]
            v = V[t, s0 + i]
            if np.isnan(v) or v <= 0: v = 1.0
            pv += c * v; vv += v
            vwap = pv / vv
            # flotante
            if pos != 0:
                fl = day + pos * (c / entry - 1.0)
                if fl < worst: worst = fl
            if (i + 1) % step == 0 and i < n - 1:
                ub = hi * (1 + vm * sig[i]); lb = lo * (1 - vm * sig[i])
                if use_vwap:
                    ub2 = max(ub, vwap); lb2 = min(lb, vwap)
                else:
                    ub2 = ub; lb2 = lb
                want = 0
                if c > ub2: want = 1
                elif c < lb2: want = -1
                if want != pos:
                    px = O[t, s0 + i + 1]
                    if np.isnan(px): px = c
                    if pos != 0:
                        day += pos * (px / entry - 1.0) - cost / 2
                    if want != 0:
                        day -= cost / 2; entry = px; ntr[t] += 1
                    pos = want
        if pos != 0:
            c = C[t, s1 - 1]
            day += pos * (c / entry - 1.0) - cost / 2
        if day < worst: worst = day
        pnl[t] = day; mae[t] = worst
        prev_close = C[t, s1 - 1]
    return pnl, mae, ntr

def run(inst, cost_bps, lookback=14, step=30, vm=1.0, use_vwap=True, tv=0.02, maxlev=4.0, s0=570, s1=960):
    dates, O, H, L, C, V = build(inst)
    Cf = ffill_flat(C)
    valid = (~np.isnan(C[:, s0:s1])).sum(1) >= 200  # dia de sesion real
    Of = np.where(np.isnan(O), Cf, O)
    pnl, mae, ntr = sim(Of, Cf, V, valid, lookback, step, vm, cost_bps / 1e4, use_vwap, s0, s1)
    s = pd.Series(pnl, index=dates)[valid]
    close = pd.Series(Cf[:, s1 - 1], index=dates)[valid]
    dv = close.pct_change().rolling(14).std().shift(1)
    lev = (tv / dv).clip(upper=maxlev)
    return s, (s * lev).dropna(), pd.Series(mae, index=dates)[valid], pd.Series(ntr, index=dates)[valid], lev

if __name__ == "__main__":
    rows = []
    for inst, cost in [("SPX500_USD", 1.5), ("NAS100_USD", 1.5), ("US2000_USD", 3.0)]:
        for (vm, vw, step) in [(1.0, True, 30), (1.0, False, 30), (1.0, True, 15), (1.0, True, 60)]:
            raw, levd, mae, ntr, lev = run(inst, cost, vm=vm, use_vwap=vw, step=step)
            for lab, a, b in [("IS 05-13", "2005", "2013"), ("OOS 14-20", "2014", "2020")]:
                r = stats(levd[a:b], f"{inst} vm{vm} vwap{int(vw)} st{step} {lab}")
                r["trades/d"] = ntr[a:b].mean(); r["lev"] = lev[a:b].mean()
                rows.append(r)
    show(rows)
