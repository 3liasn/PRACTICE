import numpy as np, pandas as pd, ftmo
from common import show
d = pd.read_parquet("/home/user/data2/port_daily.parquet")
o = d[d.index >= "2022-01-01"]; o = o[o.index.dayofweek < 5].copy()  # días hábiles (cripto de finde se suma al lunes)
full = d[d.index >= "2022-01-01"]
wk = full.copy(); wk["g"] = np.where(wk.index.dayofweek >= 5, wk.index + pd.to_timedelta(7 - wk.index.dayofweek, "D"), wk.index)
o = wk.groupby("g").agg(pnl=("pnl", "sum"), low=("low", "sum"), act=("act", "max")); o.index = pd.to_datetime(o.index)
mm = o.pnl.groupby(o.index.to_period("M")).sum().mean()
print(f"mes medio OOS a escala 1 (10 % vol IS): {mm*100:.2f} %  -> escala para 5 %/mes: {0.05/mm:.1f}x")
rows = []
for k in [1, 2, 3, 4, 0.05 / mm]:
    for buf in (0.0, 0.05):
        r = ftmo.evaluate(o, k, buffer=buf, horizon_m=12)  # historia real OOS, un arranque por mes
        rb = ftmo.evaluate(o, k, buffer=buf, horizon_m=12, boot=2000, block=20, seed=1)
        rows.append(dict(escala=round(k, 2), colchon=buf, mes_teorico=mm * k * 100,
                         hist_pasa=r["pasa"], hist_pierde_fondeada=r["pierde_fondeada"], hist_pago_mes=r["pago_mes"],
                         boot_pasa=rb["pasa"], boot_pierde_fondeada=rb["pierde_fondeada"], boot_vive_12m=rb["vive"],
                         boot_mes_fondeada=rb["mes_fondeada"], boot_pago_mes=rb["pago_mes"], boot_neto_mes=rb["neto_mes"]))
show(rows)
