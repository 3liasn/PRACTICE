"""Ruptura del máximo/mínimo del periodo anterior (día, semana o mes) con stop corto en ATR diario.
Generaliza el Engine B de bot-definitivo (k=0,15, rr=2 congelados en IS 2009–2017 sobre oro).
Simula operación por operación sobre barras M5 y devuelve P&L por barra marcado a mercado (riesgo fijo por op)."""
import numpy as np, pandas as pd, numba
from common import load, COST, SWAP, cost_frac
@numba.njit(cache=True)
def _sim(o, h, l, c, pid, lvl_hi, lvl_lo, atr, valid, nopen, k, rr, risk, costv, sw_l, sw_s, newday, legs_long, legs_short, both_ok, be):
    n = len(c); pnl = np.zeros(n); trades = []
    # para cada pata: estado por periodo
    for side in (1, -1):
        if side == 1 and not legs_long: continue
        if side == -1 and not legs_short: continue
        cur = -1; spent = False; inpos = False; extra = 0.0
        entry = 0.0; stop = 0.0; tgt = 0.0; units = 0.0; last = 0.0; ei = 0; armed = False
        for i in range(n):
            if pid[i] != cur:
                if inpos:  # cierre al final del periodo anterior (close de la última barra)
                    trades.append((ei, i - 1, side * (last - entry) * units + extra)); inpos = False
                cur = pid[i]; spent = False
            if inpos:
                if newday[i]:
                    sw = units * entry * (sw_l if side == 1 else sw_s) / 360.0
                    pnl[i] += sw; extra += sw
                hit_s = (l[i] <= stop) if side == 1 else (h[i] >= stop)
                hit_t = (h[i] >= tgt) if side == 1 else (l[i] <= tgt)
                if hit_s:
                    px = min(o[i], stop) if side == 1 else max(o[i], stop)
                    pnl[i] += side * (px - last) * units; trades.append((ei, i, side * (px - entry) * units + extra)); inpos = False; continue
                if hit_t:
                    px = max(o[i], tgt) if side == 1 else min(o[i], tgt)
                    pnl[i] += side * (px - last) * units; trades.append((ei, i, side * (px - entry) * units + extra)); inpos = False; continue
                if be > 0 and not armed and side * (c[i] - entry) >= be * (abs(entry - stop)):
                    stop = entry; armed = True
                pnl[i] += side * (c[i] - last) * units; last = c[i]
                if i + 1 < n and pid[i + 1] != cur:
                    trades.append((ei, i, side * (c[i] - entry) * units + extra)); inpos = False
                continue
            if spent or not valid[i] or nopen[i] or atr[i] <= 0: continue
            lv = lvl_hi[i] if side == 1 else lvl_lo[i]
            touch = (h[i] >= lv) if side == 1 else (l[i] <= lv)
            if not touch: continue
            spent = True
            entry = max(lv, o[i]) if side == 1 else min(lv, o[i])
            d = k * atr[i]; stop = entry - side * d; tgt = entry + side * rr * d
            units = risk / d  # unidades de precio por 1 de capital: perder d = perder `risk`
            extra = -units * entry * costv[i]  # coste ida y vuelta cargado al entrar
            pnl[i] += extra
            ei = i; inpos = True; armed = False
            # misma barra: conservador, si el rango toca el stop se pierde; el objetivo no se cuenta en la barra de entrada
            hit_s = (l[i] <= stop) if side == 1 else (h[i] >= stop)
            if hit_s:
                pnl[i] += -risk; trades.append((ei, i, -risk + extra)); inpos = False; continue
            pnl[i] += side * (c[i] - entry) * units; last = c[i]
    return pnl, trades
def run(sym, period="W", k=0.15, rr=2.0, risk=0.01, legs=(1, -1), be=0.0, tf="5min", min_frac=0.4):
    df = load(sym, tf)
    s = sym.replace("_FTMO", "")
    ny = df.index.tz_convert("America/New_York")
    mday = (ny.tz_localize(None) + pd.Timedelta(hours=6)).normalize()  # día de mercado: empieza a las 18:00 NY
    if period == "D": key = mday
    elif period == "W": key = mday - pd.to_timedelta(mday.dayofweek, unit="D")
    else: key = mday.to_period("M").to_timestamp()
    g = pd.DataFrame({"h": df.high.values, "l": df.low.values, "o": df.open.values, "k": key, "d": mday})
    per = g.groupby("k").agg(hi=("h", "max"), lo=("l", "min"), op=("o", "first"), nb=("h", "size"))
    per["phi"] = per.hi.shift(); per["plo"] = per.lo.shift(); per["pnb"] = per.nb.shift()
    dd = g.groupby("d").agg(hi=("h", "max"), lo=("l", "min"))
    atr = (dd.hi - dd.lo).rolling(14).mean().shift()  # ATR de días estrictamente anteriores
    pk = per.reindex(key)
    typical = per.nb.median()
    valid = ((pk.phi.values > pk.op.values) & (pk.op.values > pk.plo.values) & (pk.pnb.values >= min_frac * typical))
    a = atr.reindex(mday).values
    # no abrir en la ventana del rollover 17:00–18:15 NY ni la última hora antes del cierre del viernes
    mins = ny.hour * 60 + ny.minute
    nopen = ((mins >= 17 * 60) & (mins < 18 * 60 + 15)) | ((ny.dayofweek == 4) & (mins >= 15 * 60))
    newday = np.r_[False, mday[1:] != mday[:-1]]
    pid = pd.factorize(key)[0].astype(np.int64)
    sl, ss = SWAP[s]
    pnl, tr = _sim(df.open.values, df.high.values, df.low.values, df.close.values, pid, pk.phi.values, pk.plo.values,
                   np.nan_to_num(a), valid, np.asarray(nopen), k, rr, risk, np.asarray(cost_frac(s, df.close.values), dtype=np.float64), sl, ss, np.asarray(newday),
                   1 in legs, -1 in legs, True, be)
    trades = pd.DataFrame(tr, columns=["ei", "xi", "pnl"])
    if len(trades):
        trades["t"] = df.index[trades.ei.values]; trades["R"] = trades.pnl / risk
    return pd.Series(pnl, index=df.index), trades
