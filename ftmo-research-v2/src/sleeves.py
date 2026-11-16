"""Mangas candidatas. Cada función devuelve el P&L por barra H1 (fracción del capital) a escala unidad."""
import numpy as np, pandas as pd
from common import load, bar_pnl, daily, stats, show
def _daily_close(h1, hour_utc=21):
    """Cierre diario tomado de la última barra H1 que empieza antes de hour_utc."""
    m = h1.index.hour < hour_utc
    return h1.close[m].groupby(h1.index[m].date).last().pipe(lambda s: s.set_axis(pd.to_datetime(s.index).tz_localize("UTC") + pd.Timedelta(hours=hour_utc)))
def apply_daily_pos(h1, dpos):
    """Lleva una posición decidida a la hora de cada cierre diario a la rejilla H1 (efectiva desde esa barra)."""
    p = dpos.reindex(h1.index.union(dpos.index)).ffill().reindex(h1.index)
    return p.fillna(0)
def tsmom(sym, lbs=(20, 60, 120, 250), tvol=0.10, hour=21, long_only=False, vlb=40, cap=3.0):
    h1 = load(sym, "1h")
    dc = _daily_close(h1, hour)
    r = dc.pct_change()
    sig = sum(np.sign(dc / dc.shift(l) - 1) for l in lbs) / len(lbs)
    if long_only: sig = sig.clip(lower=0)
    ppy = 365 if "USDT" in sym else 260
    vol = r.rolling(vlb).std() * np.sqrt(ppy)
    pos = (sig * tvol / vol).clip(-cap, cap)
    return bar_pnl(h1.close, apply_daily_pos(h1, pos).values, sym)
def donchian(sym, n=20, tvol=0.10, hour=21, vlb=40, cap=3.0, exit_n=None):
    h1 = load(sym, "1h"); dc = _daily_close(h1, hour)
    hi = dc.rolling(n).max(); lo = dc.rolling(n).min()
    en = exit_n or n // 2
    xhi = dc.rolling(en).max(); xlo = dc.rolling(en).min()
    s = np.zeros(len(dc)); st = 0
    for i in range(len(dc)):
        c = dc.iloc[i]
        if st == 0:
            if c >= hi.iloc[i]: st = 1
            elif c <= lo.iloc[i]: st = -1
        elif st == 1 and c <= xlo.iloc[i]: st = -1 if c <= lo.iloc[i] else 0
        elif st == -1 and c >= xhi.iloc[i]: st = 1 if c >= hi.iloc[i] else 0
        s[i] = st
    ppy = 365 if "USDT" in sym else 260
    vol = dc.pct_change().rolling(vlb).std() * np.sqrt(ppy)
    pos = (pd.Series(s, dc.index) * tvol / vol).clip(-cap, cap)
    return bar_pnl(h1.close, apply_daily_pos(h1, pos).values, sym)
def split(p, cut="2022-01-01"):
    d = daily(p)
    return d[d.index < cut], d[d.index >= cut]
def ibs(sym, thr=0.2, notional=1.0, close_min=15 * 60 + 55):
    """Reversión IBS en índices USA: señal con barras M5 hasta las 15:55 NY, se ejecuta al cierre de la barra
    de las 15:55 (16:00, 5 min de retraso); sale al cierre del día siguiente. Tamaño: vol objetivo 10 %."""
    m5 = load(sym, "5min"); ny = m5.index.tz_convert("America/New_York")
    mins = ny.hour * 60 + ny.minute
    rth = (mins >= 9 * 60 + 30) & (mins < close_min)
    g = m5[rth].groupby(ny[rth].date)
    d = pd.DataFrame({"h": g.high.max(), "l": g.low.min(), "c": g.close.last()})
    d["ibs"] = (d.c - d.l) / (d.h - d.l)
    vol = d.c.pct_change().rolling(40).std() * np.sqrt(252)
    st = 0; pos = []
    for i in range(len(d)):
        st = 1 if d.ibs.iloc[i] < thr else 0
        pos.append(st)
    sz = (0.10 / vol).clip(upper=3).fillna(0) * notional
    dp = pd.Series(np.array(pos) * sz.values, index=pd.to_datetime(d.index).tz_localize("America/New_York") + pd.Timedelta(minutes=close_min)).tz_convert("UTC")
    p = dp.reindex(m5.index.union(dp.index)).ffill().reindex(m5.index).fillna(0)
    return bar_pnl(m5.close, p.values, sym)
