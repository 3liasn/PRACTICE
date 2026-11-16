"""Ronda 2 post-hoc (ver POSTHOC.md)."""
import sys, pickle; sys.path.insert(0, '.')
from common2 import *
from families import daily_bars, hourly_from_daily
S = {}
# ---------- R1 noticias ----------
cal = pd.read_csv("/home/user/asistente-trading/research/calendario_usd_alto.csv")
ev = pd.to_datetime(cal["cuando"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
cal["t"] = ev
for sym in ["XAUUSD", "EURUSD", "USDJPY", "US500", "US100"]:
    if sym in ("US500", "US100"):
        a = load(sym, "M5", "OANDA"); b = load(sym, "M5", "FTMO"); df = pd.concat([a, b[b.index >= IS_END]])
    else:
        df = load(sym, "M5", "FTMO")
    idx = df.index; c = df.close
    for hold in (12, 36):          # barras M5: 1 h y 3 h
        for mode in ("MOM", "FADE"):
            w = pd.Series(0.0, index=idx)
            for t0 in cal.t:
                pre = idx.searchsorted(t0) - 1          # última barra cerrada antes del dato
                ent = idx.searchsorted(t0 + pd.Timedelta(minutes=15))  # primera barra a +15 min
                if pre < 0 or ent >= len(idx) or idx[ent] - t0 > pd.Timedelta(minutes=30): continue
                mv = c.iloc[ent - 1] / c.iloc[pre] - 1
                if mv == 0: continue
                sgn = np.sign(mv) * (1 if mode == "MOM" else -1)
                w.iloc[ent:ent + hold] = sgn
            S[f"R1_{mode}{hold//12}h_{sym}"] = run(df, w, sym, cost_mult=2.0)
# ---------- R3 cambio de mes ----------
for sym in ["US500", "US100", "US30", "JP225", "UK100", "GER40"]:
    src = "MIX" if sym in ["US500", "US100", "UK100", "JP225"] else "FTMO"
    df = load(sym, "H1", src); D = daily_bars(df)
    ym = D.index.to_period("M"); pos = pd.Series(0.0, index=D.index)
    grp = pd.Series(range(len(D)), index=D.index).groupby(ym)
    for per, ii in grp:
        ii = ii.values
        if len(ii) >= 3: pos.iloc[ii[-2]] = 1.0          # decide al cierre del penúltimo -> mantiene el último
        if len(ii) >= 1: pos.iloc[ii[-1]] = 1.0
        if len(ii) >= 3: pos.iloc[ii[0]] = 1.0; pos.iloc[ii[1]] = 1.0  # mantiene días 1-3 (decisión del cierre anterior)
    S[f"R3_TOM_{sym}"] = run(df, hourly_from_daily(df, pos), sym)
# ---------- R4 tendencia intradía BTC ----------
df = load("BTCUSD", "H1", "FTMO"); td = tday(df.index)
op = df.groupby(td).open.transform("first")
D = daily_bars(df); sig = (np.log(D.close).diff().abs()).rolling(14).mean().shift(1)
sigh = pd.Series(sig.reindex(td).values, index=df.index)
for k in (0.5, 1.0):
    w = np.zeros(len(df)); cur_day = None; side = 0
    mv = (df.close / op - 1).values; h = df.index.hour.values; tdv = td.values; s_ = sigh.values
    for i in range(1, len(df)):
        if tdv[i] != cur_day: cur_day = tdv[i]; side = 0
        if side != 0: w[i] = side; continue
        # señal con el cierre de la barra i-1 (misma jornada), activa desde la barra i hasta las 17:00 NY
        if tdv[i - 1] == cur_day and 8 <= h[i - 1] <= 15 and not np.isnan(s_[i - 1]):
            if mv[i - 1] > k * s_[i - 1]: side = 1
            elif mv[i - 1] < -k * s_[i - 1]: side = -1
            w[i] = side
    S[f"R4_BTC_k{k}"] = run(df, pd.Series(w, index=df.index), "BTCUSD")
# ---------- R5 oro y R6 índices: IBS con/sin SMA200 ----------
def ibs_sleeve(sym, src, filt):
    df = load(sym, "H1", src); D = daily_bars(df); D = D[D.high > D.low]
    ibs = (D.close - D.low) / (D.high - D.low); sma = D.close.rolling(200).mean()
    entry = (ibs < 0.2) & ((D.close > sma) if filt else True)
    pos = np.zeros(len(D)); held = 0
    for i in range(len(D)):
        if held > 0:
            if D.close.iloc[i] > D.high.iloc[i - 1] or held >= 5: held = 0
            else: held += 1
        if held == 0 and entry.iloc[i]: held = 1
        pos[i] = 1.0 if held else 0.0
    return run(df, hourly_from_daily(df, pd.Series(pos, index=D.index)), sym)
S["R5_IBS_XAUUSD"] = ibs_sleeve("XAUUSD", "FTMO", False)
S["R5_IBS200_XAUUSD"] = ibs_sleeve("XAUUSD", "FTMO", True)
for sym, src in [("US500", "MIX"), ("US100", "MIX"), ("JP225", "MIX"), ("UK100", "MIX"), ("US30", "FTMO")]:
    S[f"R6_IBS200_{sym}"] = ibs_sleeve(sym, src, True)
pickle.dump(S, open(f"{SCR}/sleeves_r2.pkl", "wb"))
rows = []
for k_, d in S.items():
    i, o = split(d); si, so = stats(i), stats(o)
    rows.append(dict(manga=k_, sh_IS=si.get("sharpe"), ann_IS=si.get("ann"), act_IS=si.get("activos"),
                     sh_OOS=so.get("sharpe"), ann_OOS=so.get("ann"), vol_OOS=so.get("vol"), dd_OOS=so.get("maxdd"), act_OOS=so.get("activos")))
show(rows).to_csv("out_round2.csv", index=False)
