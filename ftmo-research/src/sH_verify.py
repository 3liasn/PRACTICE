"""(1) Verificacion independiente (pandas puro desde parquet, sin la rejilla) de la manga MR_L NAS100.
   (2) Tabla de requisito: Sharpe necesario para sostener 5%/mes bajo reglas FTMO (Monte Carlo, colas gordas t-Student)."""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd
from sG_portfolio import ftmo
# ---------- (1)
df = pd.read_parquet("data/NAS100_USD_M1.parquet"); df.index = df.index.tz_convert("America/New_York")
r = df.between_time("09:30", "15:59")
g = r.groupby(r.index.date)
nb_ = g.size(); days = nb_[nb_ >= 200].index
sig = r.between_time("09:30", "15:54"); gs = sig.groupby(sig.index.date)
d = pd.DataFrame({"h": gs.high.max(), "l": gs.low.min(), "cs": gs.close.last(), "c": g.close.last()}).loc[days]
d.index = pd.to_datetime(d.index)
ibs = (d.cs - d.l) / (d.h - d.l)
pos = (ibs < 0.2).astype(float)
nights = pd.Series((d.index[1:] - d.index[:-1]).days, index=d.index[:-1]).reindex(d.index).fillna(1)
pos[nights > 1] = 0
ret = d.c.shift(-1) / d.c - 1
turn = pos.diff().abs().fillna(pos.abs())
p = (pos * ret - turn * 1.5e-4 / 2 - pos * nights * 2e-4).shift(1).fillna(0)
cal = pd.bdate_range("2005-01-03", "2020-05-13"); x = p.reindex(cal).fillna(0)
sh = lambda v: v.mean() / v.std() * np.sqrt(252)
print(f"(1) MR_L NAS100 independiente: Sharpe IS {sh(x[:'2012']):.3f} | OOS {sh(x['2013':]):.3f} | ret medio por operacion OOS {p['2013':][p['2013':] != 0].mean()*1e4:.1f} bps | n ops OOS {(pos['2013':] > 0).sum()}")
S = pd.read_pickle("out/sleeves.pkl")["S"]["MR_L NAS100"].p.reindex(cal).fillna(0)
print(f"    via rejilla (codigo principal): Sharpe IS {sh(S[:'2012']):.3f} | OOS {sh(S['2013':]):.3f} | correlacion diaria entre ambas {np.corrcoef(S, x)[0,1]:.4f}")
# ---------- (2)
rng = np.random.default_rng(11); rows = []
mu_d = 0.05 / 21
for Sh in [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0]:
    sd = mu_d * 252 / Sh / np.sqrt(252)
    z = rng.standard_t(4, 400000) / np.sqrt(2.0)          # t(4) normalizada a var=1
    rr = mu_d + sd * z
    intr = sd * np.abs(rng.standard_normal(400000)) * 0.5   # excursion intradia adicional
    w = np.minimum(rr, 0) - intr
    for kb in (0, 1):
        o = ftmo(rr, w, 20000, 1, 3, 0.04, 24, kb)
        f = o[:, 1] == 1
        rows.append(dict(Sharpe=Sh, vol_anual=sd * np.sqrt(252), colchon=kb, pasa_eval=f.mean(), quiebra_12m=((o[f, 5] > 0) & (o[f, 5] <= 12)).mean(),
                         quiebra_24m=(o[f, 5] > 0).mean(), pago_mes_medio=(o[f, 4] / 24).mean()))
print("\n(2) Estrategia hipotetica con media 5%/mes: probabilidad de perder la cuenta segun su Sharpe real")
with pd.option_context("display.width", 200, "display.float_format", "{:.3f}".format): print(pd.DataFrame(rows).to_string(index=False))
