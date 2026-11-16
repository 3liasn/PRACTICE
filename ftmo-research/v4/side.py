import sys; sys.path.insert(0, "."); sys.path.insert(0, "../v2")
from acct import load
import numpy as np, pandas as pd
from common2 import load as L2, tday
a = L2("XAUUSD", "H1", "OANDA"); b = L2("XAUUSD", "H1", "FTMO")
c = pd.concat([a[a.index < b.index[0]], b]).close; c = c.groupby(tday(c.index)).last()
tr = np.sign(np.log(c / c.shift(60))).shift(1); tr.index = tr.index.values.astype("datetime64[D]").astype(np.int64)
d = load()["df"].join(tr.rename("trend60"), on="ed")
d["per"] = np.where(d.ed < np.datetime64("2020-01-01", "D").astype(np.int64), "IS", "OOS")
d["fam"] = d.strategy.map({"ACompression": "A", "N59f": "RANGE", "W_dst": "RANGE", "N141": "RANGE", "N30GapFade": "N30"})
d["a_favor"] = np.where(d.side == d.trend60, "a_favor_tendencia60d", "contra")
for k in ("side", "a_favor"):
    g = d.groupby(["fam", "per", k]).r.agg(["count", "mean", "std"]); g["t"] = g["mean"] / g["std"] * np.sqrt(g["count"])
    print(g[["count", "mean", "t"]].unstack(k).round(3).to_string(), "\n")
yr = d.assign(y=pd.to_datetime(d.ed, unit="D").year).groupby(["y", "fam"]).r.sum().unstack().round(1)
print("R total por año y familia:\n", yr.to_string())
