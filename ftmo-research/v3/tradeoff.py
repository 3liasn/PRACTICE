"""Intercambio robustez vs rendimiento: cuota de volatilidad s de la fuente no-oro (0..50 %), pesos fijados antes.
Sharpe en el régimen actual (2021-02 -> 2026-10) y en el régimen anterior (2009-03 -> 2019-12)."""
import sys, pickle; sys.path.insert(0, "../v2"); sys.path.insert(0, ".")
from common2 import *
from marginal import gold_daily
G, _ = gold_daily()
ports = pickle.load(open(f"{SCR}/ports.pkl", "rb")); S = pickle.load(open(f"{SCR}/sleeves_v2.pkl", "rb"))
MR = ports["MR_indices"].pnl
B = S["F2_BTC_L"].pnl; wd = B.index.weekday
B = B.groupby(B.index + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")).sum()
P1 = ("2009-03-16", "2020-01-01"); P2 = ("2021-02-01", str(OOS_END.date()))
def sh(x, a, b):
    x = x[(x.index >= a) & (x.index < b)]
    return x.mean() / x.std() * np.sqrt(252), x.groupby([x.index.year, x.index.month]).sum().mean()
rows = []
for name, X in [("MR_indices", MR), ("BTC_tend", B)]:
    for s in (0.0, 0.1, 0.2, 0.3, 0.5):
        idx = G.index.union(X.index)
        g = G.pnl.reindex(idx).fillna(0); x = X.reindex(idx).fillna(0)
        # normalizar cada fuente a vol 1 con su vol de TODO el histórico disponible (no optimiza Sharpe)
        c = g / g.std() * (1 - s) + x / x[x != 0].std() * s * np.sqrt((x != 0).mean())
        r = {"fuente": name, "cuota_vol": s}
        for lab, (a, b) in [("2009-19", P1), ("2021-26", P2)]:
            shp, m = sh(c, a, b); r[f"sharpe_{lab}"] = shp
        # %/mes 2021-26 a la misma vol que la cartera oro sola
        c2 = c[(c.index >= P2[0]) & (c.index < P2[1])]; g2 = g[(g.index >= P2[0]) & (g.index < P2[1])]
        c2 = c2 / c2.std() * g2.std()
        r["mes_2021_26_misma_vol"] = c2.groupby([c2.index.year, c2.index.month]).sum().mean()
        c1 = c[(c.index >= P1[0]) & (c.index < P1[1])]; g1 = g[(g.index >= P1[0]) & (g.index < P1[1])]
        c1 = c1 / c1.std() * g2.std()
        r["mes_2009_19_misma_vol"] = c1.groupby([c1.index.year, c1.index.month]).sum().mean()
        rows.append(r)
show(rows, "{:.3f}").to_csv("out_tradeoff.csv", index=False)
print("solo MR en 2009-19:", [round(v, 3) for v in sh(MR, *P1)], " solo BTC 2015-19:", [round(v, 3) for v in sh(B, "2015-01-01", P1[1])])
