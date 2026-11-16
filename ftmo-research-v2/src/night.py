"""Reversión a la media en la sesión tranquila (estilo 'night scalper'). Parámetros fijados a priori:
M5, media y sigma de 36 barras (3 h); entra si |z|>=ZIN en la ventana 18:30–23:30 NY; sale al volver a la media,
con stop en |z|>=ZSTOP (medido con la media/sigma de la entrada) o a la 01:00 NY. Tamaño: nocional tal que
1 sigma de entrada = RISK_SIG del capital."""
import numpy as np, pandas as pd, numba
from common import load, bar_pnl
@numba.njit(cache=True)
def _pos(c, mu, sd, okin, force, zin, zstop, size):
    n = len(c); p = np.zeros(n); st = 0; m0 = 0.0; s0 = 0.0; u = 0.0
    for i in range(n):
        if st != 0:
            z = (c[i] - m0) / s0
            if force[i] or (st == 1 and (c[i] >= mu[i] or z <= -zstop)) or (st == -1 and (c[i] <= mu[i] or z >= zstop)):
                st = 0
        if st == 0 and okin[i] and sd[i] > 0:
            z = (c[i] - mu[i]) / sd[i]
            if z >= zin: st = -1; m0 = mu[i]; s0 = sd[i]; u = size * c[i] / sd[i]
            elif z <= -zin: st = 1; m0 = mu[i]; s0 = sd[i]; u = size * c[i] / sd[i]
        p[i] = st * u if st != 0 else 0.0
    return p
def night(sym, zin=2.0, zstop=5.0, n=36, risk_sig=0.0025, win=(18 * 60 + 30, 23 * 60 + 30), exit_min=60, tf="5min"):
    df = load(sym, tf); c = df.close
    mu = c.rolling(n).mean(); sd = c.rolling(n).std()
    ny = df.index.tz_convert("America/New_York"); m = ny.hour * 60 + ny.minute
    okin = (m >= win[0]) & (m < win[1]) & (ny.dayofweek != 4)  # sin viernes noche
    force = (m >= exit_min) & (m < win[0])  # de 01:00 a 18:30 NY: plano
    p = _pos(c.values, mu.fillna(0).values, sd.fillna(0).values, np.asarray(okin), np.asarray(force), zin, zstop, risk_sig)
    p = np.minimum(np.abs(p), 30) * np.sign(p)  # tope de nocional 30x (apalancamiento FTMO FX 1:100)
    return bar_pnl(c, p, sym), p
