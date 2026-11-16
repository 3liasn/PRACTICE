"""¿El R de cada motor depende del régimen de volatilidad del oro? Terciles fijados con la distribución IS (<2020).
Vol = desviación de 20 días de los retornos diarios (cierre de día de servidor), conocida al cierre del día anterior a la entrada."""
import sys; sys.path.insert(0, "."); sys.path.insert(0, "../v2")
from acct import load, broker_day
import numpy as np, pandas as pd
from common2 import load as L2, tday
a = L2("XAUUSD", "H1", "OANDA"); b = L2("XAUUSD", "H1", "FTMO")
px = pd.concat([a[a.index < b.index[0]], b]).close
c = px.groupby(tday(px.index)).last()
r = np.log(c).diff()
rv = r.rolling(20).std() * np.sqrt(252)
rel = rv / rv.rolling(250).median()
feat = pd.DataFrame({"rv": rv, "rel": rel}).shift(1)      # solo información hasta el día anterior
feat.index = feat.index.values.astype("datetime64[D]").astype(np.int64)
T = load(); d = T["df"].copy()
d = d.join(feat, on="ed")
d["per"] = np.where(d.ed < np.datetime64("2020-01-01", "D").astype(np.int64), "IS", "OOS")
d["fam"] = d.strategy.map({"ACompression": "A", "N59f": "RANGE", "W_dst": "RANGE", "N141": "RANGE", "N30GapFade": "N30"})
for var in ("rv", "rel"):
    q = d[d.per == "IS"][var].quantile([1/3, 2/3]).values
    d[f"t_{var}"] = np.digitize(d[var], q)
    print(f"\n=== {var}: cortes IS {np.round(q, 3)} (0=bajo, 2=alto) — mean R (n, t)")
    g = d.dropna(subset=[var]).groupby(["fam", "per", f"t_{var}"]).r.agg(["count", "mean", "std"])
    g["t"] = g["mean"] / g["std"] * np.sqrt(g["count"])
    print(g[["count", "mean", "t"]].unstack(f"t_{var}").round(3).to_string())
    # diferencia alto - bajo
    for fam in ("A", "RANGE", "N30"):
        for per in ("IS", "OOS"):
            x = d[(d.fam == fam) & (d.per == per)]
            hi = x[x[f"t_{var}"] == 2].r; lo = x[x[f"t_{var}"] == 0].r
            if len(hi) > 20 and len(lo) > 20:
                diff = hi.mean() - lo.mean(); se = np.sqrt(hi.var() / len(hi) + lo.var() / len(lo))
                print(f"   {fam:5s} {per}: alto−bajo = {diff:+.3f} R (t {diff/se:+.2f})")
print("\nreparto de días OOS por tercil de rv (cortes IS):", d[d.per == "OOS"].t_rv.value_counts(normalize=True).sort_index().round(2).to_dict())
