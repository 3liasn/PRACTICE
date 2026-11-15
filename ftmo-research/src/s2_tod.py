"""Mapa de estacionalidad horaria: retorno medio por hora del dia (NY), IS vs OOS."""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd
from grid import build, ffill_flat
INST = ["SPX500_USD","NAS100_USD","US2000_USD","UK100_GBP","FR40_EUR","JP225_USD","AU200_AUD","NL25_EUR","XAU_USD","WTICO_USD","NATGAS_USD",
        "EUR_USD","GBP_USD","AUD_USD","USD_CAD","EUR_JPY","AUD_JPY","USB10Y_USD","DE10YB_EUR","UK10YB_GBP"]
rows = []
for inst in INST:
    dates, O, H, L, C, V = build(inst)
    Cf = ffill_flat(C)
    hasbar = ~np.isnan(C)
    # retorno horario h: de minuto h*60-1 (cierre de la hora previa) a h*60+59
    px = Cf[:, 59::60]           # cierre de cada hora [dias, 24]
    prev = np.concatenate([np.r_[np.nan, Cf[:-1, -1]][:, None], px[:, :-1]], axis=1)
    r = (px / prev - 1) * 1e4
    act = hasbar.reshape(len(dates), 24, 60).sum(2) >= 20   # hora con actividad real
    r[~act] = np.nan
    yrs = dates.year.values
    wd = dates.dayofweek.values
    for h in range(24):
        x = r[:, h]
        a = x[(yrs <= 2012) & ~np.isnan(x)]; b = x[(yrs >= 2013) & ~np.isnan(x)]
        if len(a) < 500 or len(b) < 500: continue
        ta = a.mean() / a.std() * np.sqrt(len(a)); tb = b.mean() / b.std() * np.sqrt(len(b))
        rows.append(dict(inst=inst, hora=h, is_bps=a.mean(), is_t=ta, oos_bps=b.mean(), oos_t=tb, n_is=len(a), n_oos=len(b)))
df = pd.DataFrame(rows)
df.to_csv("out/tod_hourly.csv", index=False)
sel = df[(df.is_t.abs() > 3.0)].sort_values("is_t")
with pd.option_context("display.width", 200, "display.float_format", "{:.2f}".format):
    print("Horas con |t| IS > 3 (seleccion SOLO con IS) y su resultado OOS:")
    print(sel.to_string(index=False))
    same = (np.sign(sel.is_bps) == np.sign(sel.oos_bps)).mean()
    print(f"\nMismo signo en OOS: {same:.0%} de {len(sel)};  |t| OOS > 2 con mismo signo: {((np.sign(sel.is_bps) == np.sign(sel.oos_bps)) & (sel.oos_t.abs() > 2)).mean():.0%}")
