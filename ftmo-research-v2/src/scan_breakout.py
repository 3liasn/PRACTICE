"""Escaneo de la ruptura con parámetros congelados (k=0,15, rr=2) en todos los activos y periodos, M1."""
import sys, numpy as np, pandas as pd
from breakout import run
from common import show
rows = []
for sym in sys.argv[1:]:
    for per in "DWM":
        p, t = run(sym, per, tf="1min")
        p.to_frame("pnl").to_parquet(f"/home/user/data2/sl_brk_{sym}_{per}.parquet")
        for nm, m in [("IS", t.t < "2022"), ("OOS", t.t >= "2022")]:
            x = t[m]; yrs = max((x.t.max() - x.t.min()).days / 365.25, 0.1)
            rows.append(dict(sym=sym, per=per, part=nm, n=len(x), por_año=len(x) / yrs, R=x.R.mean(), win=(x.R > 0).mean(),
                             t=x.R.mean() / x.R.std() * np.sqrt(len(x)), sh=x.R.mean() / x.R.std() * np.sqrt(len(x) / yrs)))
        print(sym, per, flush=True)
show(rows)
pd.DataFrame(rows).to_csv(f"/home/user/data2/scan_brk_{'_'.join(sys.argv[1:])}.csv", index=False)
