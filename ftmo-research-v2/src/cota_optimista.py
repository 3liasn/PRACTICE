"""Cota optimista (con sesgo a propósito): mangas elegidas MIRANDO el OOS (Sharpe OOS >= 0,5), pesos de igual vol
en OOS y peor flotante = solo el cierre del día si es negativo (ignora el flotante intradía). Sirve como techo."""
import numpy as np, pandas as pd, ftmo
from common import daily, stats, show
from breakout import run
import sleeves as S
picks = {"ibs_NSXUSD": lambda: S.ibs("NSXUSD"), "ibs_SPXUSD": lambda: S.ibs("SPXUSD"),
         "brk_XAU_D": lambda: run("XAUUSD", "D", k=0.6, rr=4.0, tf="1min")[0], "brk_XAU_W": lambda: run("XAUUSD", "W", k=0.3, rr=2.0, tf="1min")[0],
         "tsmom_XAU": lambda: S.tsmom("XAUUSD", long_only=True), "brk_NSX_W": lambda: run("NSXUSD", "W", k=0.6, rr=1.0, tf="1min")[0],
         "brk_XAG_W": lambda: run("XAGUSD", "W", k=1.0, rr=4.0, tf="1min")[0], "tsmom_BTC": lambda: S.tsmom("BTCUSDT", long_only=True)}
idx = pd.date_range("2022-01-01", "2026-10-31", freq="D")
P = pd.DataFrame({k: daily(f()).pnl for k, f in picks.items()}).reindex(idx).fillna(0)
wk = P.copy(); g = np.where(wk.index.dayofweek >= 5, wk.index + pd.to_timedelta(7 - wk.index.dayofweek, "D"), wk.index)
P = wk.groupby(g).sum(); P.index = pd.to_datetime(P.index)
w = 1 / P.std(); w /= w.sum()
port = (P * w).sum(axis=1)
m = port.groupby(port.index.to_period("M")).sum()
port = port * (0.10 / (m.std() * np.sqrt(12)))
d = pd.DataFrame({"pnl": port, "low": port.clip(upper=0), "act": True})
st = stats(d, "techo OOS"); show([st])
print("corr media:", round(P.corr().values[np.triu_indices(len(picks), 1)].mean(), 3))
mm = d.pnl.groupby(d.index.to_period("M")).sum().mean()
rows = []
for k in [1, 2, 3, 0.05 / mm]:
    r = ftmo.evaluate(d, k, horizon_m=12); rb = ftmo.evaluate(d, k, horizon_m=12, boot=3000, block=20, seed=2)
    rb5 = ftmo.evaluate(d, k, horizon_m=12, boot=3000, block=20, seed=2, buffer=0.05)
    rows.append(dict(escala=round(k, 2), mes_teorico=mm * k * 100, hist_pasa=r["pasa"], hist_pago_mes=r["pago_mes"],
                     boot_pasa=rb["pasa"], boot_pierde_fondeada=rb["pierde_fondeada"], boot_vive=rb["vive"],
                     boot_pago_mes=rb["pago_mes"], boot_pago_mes_colchon=rb5["pago_mes"]))
show(rows)
