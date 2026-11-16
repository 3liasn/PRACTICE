import sys, numpy as np, pandas as pd
from breakout import run
from common import show
from concurrent.futures import ProcessPoolExecutor
def one(a):
    sym, per, k, rr = a
    p, t = run(sym, per, k=k, rr=rr, tf="1min")
    out = []
    for nm, m in [("IS", t.t < "2022"), ("OOS", t.t >= "2022")]:
        x = t[m]; yrs = max((x.t.max() - x.t.min()).days / 365.25, 0.1)
        out.append(dict(sym=sym, per=per, k=k, rr=rr, part=nm, n=len(x), R=x.R.mean(),
                        sh=x.R.mean() / x.R.std() * np.sqrt(len(x) / yrs)))
    return out
jobs = [(s, p, k, rr) for s in sys.argv[1:] for p in "DW" for k in (0.3, 0.6, 1.0) for rr in (1.0, 2.0, 4.0)]
rows = []
with ProcessPoolExecutor(4) as ex:
    for o in ex.map(one, jobs): rows += o
df = pd.DataFrame(rows)
w = df.pivot_table(index=["sym", "per", "k", "rr"], columns="part", values="sh").reset_index()
w.to_csv("/home/user/data2/scan_k.csv", index=False)
best = w.sort_values("IS", ascending=False).groupby(["sym", "per"]).head(1)
print("Mejor configuración elegida SOLO por IS, y su OOS:"); show(best.to_dict("records"))
print("Mediana del OOS de las 9 configuraciones por activo/periodo:"); print(w.groupby(["sym", "per"]).OOS.median().round(2).to_string())
