"""Cartera con regla fijada en IS (2016–2021, cripto 2018–2021): entra toda manga con Sharpe IS >= 0,3;
pesos de igual volatilidad en IS; cartera normalizada a 10 % de vol anual en IS. OOS = 2022 – oct 2026."""
import numpy as np, pandas as pd
from common import daily, stats, show
from breakout import run
import sleeves as S
CUT = "2022-01-01"
w = pd.read_csv("/home/user/data2/scan_k.csv")
best = w.sort_values("IS", ascending=False).groupby(["sym", "per"]).head(1)
cands = {}
for r in best.itertuples():
    cands[f"brk_{r.sym}_{r.per}_k{r.k}_rr{r.rr}"] = lambda r=r: run(r.sym, r.per, k=r.k, rr=r.rr, tf="1min")[0]
for s in ["XAUUSD", "NSXUSD", "BTCUSDT", "ETHUSDT", "SPXUSD", "GRXEUR", "XAGUSD", "EURUSD"]:
    cands[f"tsmom_{s}"] = lambda s=s: S.tsmom(s)
    cands[f"tsmomL_{s}"] = lambda s=s: S.tsmom(s, long_only=True)
for s in ["SPXUSD", "NSXUSD", "GRXEUR"]:
    cands[f"ibs_{s}"] = lambda s=s: S.ibs(s)
D = {}; rows = []
for nm, f in cands.items():
    d = daily(f()); D[nm] = d
    a, b = d[d.index < CUT], d[d.index >= CUT]
    if "USDT" in nm: a = a[a.index >= "2018-01-01"]
    rows.append(dict(name=nm, sh_IS=stats(a)["sharpe_m"], sh_OOS=stats(b)["sharpe_m"]))
R = pd.DataFrame(rows).sort_values("sh_IS", ascending=False)
# una sola variante de tendencia por activo (la de mejor IS)
R["fam"] = R.name.str.replace("tsmomL_", "tsmom_")
R = R.groupby("fam").head(1)
show(R.to_dict("records"))
sel = R[R.sh_IS >= 0.3].name.tolist()
print("Seleccionadas (solo IS):", sel)
idx = pd.date_range("2016-01-01", "2026-10-31", freq="D")
P = pd.DataFrame({k: D[k].pnl for k in sel}).reindex(idx).fillna(0)
L = pd.DataFrame({k: D[k].low for k in sel}).reindex(idx).fillna(0)
A = pd.DataFrame({k: D[k].act for k in sel}).reindex(idx).fillna(False)
isP = P[P.index < CUT]
volIS = isP.apply(lambda x: x[x != 0].std() * np.sqrt(len(x[x != 0]) / 6) if (x != 0).any() else np.nan)
wts = (1 / volIS); wts = wts / wts.sum()
port = (P * wts).sum(axis=1); low = (L * wts).sum(axis=1)  # suma de peores flotantes: conservador
vol_is = port[port.index < CUT].groupby(port[port.index < CUT].index.to_period("M")).sum().std() * np.sqrt(12)
sc = 0.10 / vol_is
out = pd.DataFrame({"pnl": port * sc, "low": low * sc, "act": A.any(axis=1)})
out = out[out.index.dayofweek < 7]
out.to_parquet("/home/user/data2/port_daily.parquet")
show([stats(out[out.index < CUT], "cartera IS"), stats(out[out.index >= CUT], "cartera OOS")])
print("corr media OOS entre mangas:", round(P[P.index >= CUT].corr().values[np.triu_indices(len(sel), 1)].mean(), 3))
