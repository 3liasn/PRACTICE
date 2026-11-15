"""Opening Range Breakout con ejecucion M1. Stop en el lado opuesto del rango; salida al cierre de sesion."""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd, numba as nb
from grid import build, ffill_flat

@nb.njit(cache=True)
def orb(O, H, L, Cf, valid, s0, W, s1, mode, tgtR, cost, slip, minrng, maxrng):
    nd = O.shape[0]
    R = np.zeros(nd); ret = np.zeros(nd); risk = np.zeros(nd); mae = np.zeros(nd); traded = np.zeros(nd)
    for t in range(nd):
        if not valid[t]: continue
        op = O[t, s0]
        if np.isnan(op): op = Cf[t, s0]
        hi = -1e18; lo = 1e18
        for i in range(s0, s0 + W):
            h = H[t, i]; l = L[t, i]
            if not np.isnan(h):
                if h > hi: hi = h
                if l < lo: lo = l
        if hi < 0 or not (op > 0) or hi <= lo or not (lo > 0): continue
        rng = (hi - lo) / op
        if rng < minrng or rng > maxrng: continue
        cw = Cf[t, s0 + W - 1]
        pos = 0; entry = 0.0; stop = 0.0; tgt = 0.0
        start = s0 + W
        if mode == 0:
            if cw > op: pos = 1
            elif cw < op: pos = -1
            else: continue
            entry = O[t, start]
            if np.isnan(entry): entry = cw
            if pos == 1: stop = lo
            else: stop = hi
            if (pos == 1 and entry <= stop) or (pos == -1 and entry >= stop) or not (entry > 0): continue
        done = False; pnl = 0.0; worst = 0.0
        for i in range(start, s1):
            h = H[t, i]; l = L[t, i]
            if np.isnan(h): continue
            if pos == 0:
                if mode == 1:
                    up = h > hi; dn = l < lo
                    if up and dn: break            # barra ambigua: no operar
                    ob = O[t, i]
                    if np.isnan(ob) or ob <= 0: ob = Cf[t, i]
                    if up:
                        pos = 1; entry = max(hi, ob) * (1 + slip); stop = lo
                    elif dn:
                        pos = -1; entry = min(lo, ob) * (1 - slip); stop = hi
                    if pos != 0 and not (entry > 0):
                        pos = 0; break
                    if pos != 0:
                        rk = abs(entry - stop) / entry
                        if tgtR > 0: tgt = entry * (1 + pos * tgtR * rk)
                    # la barra de entrada no se revisa para stop (se revisa desde la siguiente)
                    continue
                else:
                    break
            if mode == 0 and i == start and tgtR > 0:
                rk = abs(entry - stop) / entry; tgt = entry * (1 + pos * tgtR * rk)
            # gestion
            if pos == 1:
                fl = l / entry - 1
                if fl < worst: worst = fl
                if l <= stop:
                    px = min(stop, O[t, i]) * (1 - slip); pnl = px / entry - 1; done = True; break
                if tgtR > 0 and h >= tgt:
                    pnl = tgt / entry - 1; done = True; break
            else:
                fl = -(h / entry - 1)
                if fl < worst: worst = fl
                if h >= stop:
                    px = max(stop, O[t, i]) * (1 + slip); pnl = -(px / entry - 1); done = True; break
                if tgtR > 0 and l <= tgt:
                    pnl = -(tgt / entry - 1); done = True; break
        if pos == 0: continue
        if not done:
            pnl = pos * (Cf[t, s1 - 1] / entry - 1)
        pnl -= cost
        rk = abs(entry - stop) / entry
        if rk < 1e-6: continue
        ret[t] = pnl; risk[t] = rk; R[t] = pnl / rk; mae[t] = worst; traded[t] = 1
    return R, ret, risk, mae, traded

CFG = {  # inst: (tz, [(nombre_sesion, s0, s1)], coste_bps)
    "SPX500_USD": ("America/New_York", [("NY", 570, 960)], 1.5), "NAS100_USD": ("America/New_York", [("NY", 570, 960)], 1.5),
    "US2000_USD": ("America/New_York", [("NY", 570, 960)], 3.0),
    "UK100_GBP": ("Europe/London", [("LON", 480, 990)], 2.0), "FR40_EUR": ("Europe/Paris", [("PAR", 540, 1050)], 2.5),
    "XAU_USD": ("America/New_York", [("LON3", 180, 600), ("NY820", 500, 960), ("NY930", 570, 960)], 1.5),
    "WTICO_USD": ("America/New_York", [("NY9", 540, 870)], 5.0),
    "EUR_USD": ("Europe/London", [("LON8", 480, 960)], 1.0), "GBP_USD": ("Europe/London", [("LON8", 480, 960)], 1.2),
    "USB10Y_USD": ("America/New_York", [("NY820", 500, 900)], 2.0)}
def sharpe(x):
    x = x[~np.isnan(x)]
    return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else np.nan
def run_one(inst, sess, W, mode, tgtR=0.0, cost_mult=1.0, minrng=0.0, maxrng=1.0):
    tz, sessions, cost = CFG[inst]
    s0, s1 = [(a, b) for (n, a, b) in sessions if n == sess][0]
    dates, O, H, L, C, V = build(inst, tz)
    Cf = ffill_flat(C)
    valid = (~np.isnan(C[:, s0:s1])).sum(1) >= 0.5 * (s1 - s0)
    R, ret, risk, mae, tr = orb(O, H, L, Cf, valid, s0, W, s1, mode, tgtR, cost * cost_mult / 1e4, 0.25e-4, minrng, maxrng)
    idx = pd.DatetimeIndex(dates)
    return pd.DataFrame({"R": R, "ret": ret, "risk": risk, "mae": mae, "tr": tr}, index=idx)[valid]
if __name__ == "__main__":
    rows = []
    for inst, (tz, sessions, cost) in CFG.items():
        for (sess, s0, s1) in sessions:
            for mode in (0, 1):
                for W in (5, 15, 30, 60):
                    d = run_one(inst, sess, W, mode)
                    a = d[:"2012"]; b = d["2013":]
                    rows.append(dict(inst=inst[:6], sess=sess, mode=mode, W=W, IS_shR=sharpe(a.R.values), OOS_shR=sharpe(b.R.values),
                                     IS_meanR=a.R[a.tr > 0].mean(), OOS_meanR=b.R[b.tr > 0].mean(), IS_shRet=sharpe(a.ret.values), OOS_shRet=sharpe(b.ret.values),
                                     risk_bps=d.risk[d.tr > 0].median() * 1e4, win=(d.R[d.tr > 0] > 0).mean(), n_yr=d.tr.sum() / 15.4))
    df = pd.DataFrame(rows); df.to_csv("out/sB_scan.csv", index=False)
    with pd.option_context("display.width", 250, "display.float_format", "{:.2f}".format, "display.max_rows", 500):
        print(df.to_string(index=False))
