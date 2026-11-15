"""Donde se concentra el retorno tras un cierre debil/fuerte (IBS) en indices USA: tramos horarios hasta el cierre siguiente."""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd
from grid import build, ffill_flat
SEG = [("16:00-18:00", 959, 1079, 0), ("18:00-02:00", 1079, 119, 1), ("02:00-03:00", 119, 179, 2), ("03:00-09:30", 179, 569, 2),
       ("09:30-10:30", 569, 629, 2), ("10:30-16:00", 629, 959, 2)]   # (nombre, min_ini, min_fin, tipo) tipo0: mismo dia; 1: cruza medianoche; 2: dia siguiente
rows = []
for inst in ["SPX500_USD", "NAS100_USD", "US2000_USD"]:
    dates, O, H, L, C, V = build(inst); Cf = ffill_flat(C)
    s0, s1 = 570, 960
    ok = (~np.isnan(C[:, s0:s1])).sum(1) >= 200
    idx = np.where(ok)[0]
    h = np.nanmax(H[:, s0:s1 - 5], axis=1); l = np.nanmin(L[:, s0:s1 - 5], axis=1); cs = Cf[:, s1 - 6]
    ibs = (cs - l) / (h - l)
    nxt = {idx[k]: idx[k + 1] for k in range(len(idx) - 1)}   # siguiente dia de sesion
    yrs = dates.year.values
    for nm, a, b, typ in SEG:
        r = np.full(len(dates), np.nan)
        for t in idx[:-1]:
            n = nxt[t]
            if typ == 0: r[t] = Cf[t, b] / Cf[t, a] - 1
            elif typ == 1: r[t] = Cf[n, b] / Cf[t, a] - 1
            else: r[t] = Cf[n, b] / Cf[n, a] - 1
        for lab, cond in [("ibs<0.2", ibs < 0.2), ("ibs>0.8", ibs > 0.8), ("todos", ibs > -1)]:
            for per, m in [("IS", yrs <= 2012), ("OOS", yrs >= 2013)]:
                x = r[cond & m & ok & ~np.isnan(r)] * 1e4
                rows.append(dict(inst=inst[:6], seg=nm, cond=lab, per=per, bps=x.mean(), t=x.mean() / x.std() * np.sqrt(len(x)), n=len(x)))
df = pd.DataFrame(rows)
pv = df.pivot_table(index=["inst", "cond", "seg"], columns="per", values=["bps", "t"]).round(2)
pv = pv.reindex([s[0] for s in SEG], level=2)
with pd.option_context("display.width", 200, "display.max_rows", 200):
    print(pv.to_string())
