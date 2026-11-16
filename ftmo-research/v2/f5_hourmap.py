"""F5: mapa de retorno medio por hora NY (pb), IS vs OOS, con t-stat. Base para F1 y F5."""
import sys; sys.path.insert(0, '.')
from common2 import *
rows = []
for sym in ALL17 + ["BTCUSD"]:
    src = "MIX" if sym in INDICES + ["USOIL"] else "FTMO"
    if sym in ["GER40", "UKOIL", "US30"]: src = "FTMO"
    df = load(sym, "H1", src)
    r = np.log(df.close).diff() * 1e4
    r = r[(r.abs() < 500)]
    h = r.index.hour
    for per, m in [("IS", r.index < IS_END), ("OOS", (r.index >= IS_END) & (r.index < OOS_END))]:
        x = r[m]; g = x.groupby(x.index.hour)
        mu = g.mean(); se = g.std() / np.sqrt(g.count())
        for hh in mu.index:
            rows.append(dict(sym=sym, per=per, hour=hh, mu=mu[hh], t=mu[hh] / se[hh], n=g.count()[hh]))
M = pd.DataFrame(rows)
M.to_csv("out_f5_hourmap.csv", index=False)
P = M.pivot_table(index=["sym", "hour"], columns="per", values=["mu", "t"])
P.columns = [f"{a}_{b}" for a, b in P.columns]
sig = P[(P.t_IS.abs() >= 3)]
sig = sig.assign(mismo_signo=np.sign(sig.mu_IS) == np.sign(sig.mu_OOS))
with pd.option_context("display.width", 200, "display.max_rows", 200, "display.float_format", "{:.2f}".format):
    print("Horas con |t| IS >= 3:\n", sig)
    print("\nOro y plata por hora:\n", P.loc[["XAUUSD", "XAGUSD"]])
