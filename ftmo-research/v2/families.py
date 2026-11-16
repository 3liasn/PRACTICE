"""Familias F1-F4, F6, F7 del pre-registro. Cada manga -> P&L diario con exposición unitaria."""
import sys, pickle; sys.path.insert(0, '.')
from common2 import *

def daily_bars(df):
    g = df.groupby(tday(df.index))
    return pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last()})

def hourly_from_daily(df, wd):
    """peso decidido al cierre del día d -> se mantiene durante todas las barras del día d+1."""
    return pd.Series(wd.shift(1).reindex(tday(df.index)).values, index=df.index).fillna(0.0)

def src_of(sym):
    return "MIX" if sym in ["US500", "US100", "UK100", "JP225", "USOIL"] else "FTMO"

if __name__ == '__main__':
    S = {}
    # ---------- F1 sesión del oro ----------
    for sym in METALS:
        df = load(sym, "H1", "FTMO"); h = df.index.hour
        A = pd.Series(np.where((h >= 18) | (h < 8), 1.0, 0.0), index=df.index)
        B = pd.Series(np.where((h >= 8) & (h < 16), -1.0, 0.0), index=df.index)
        S[f"F1A_{sym}"] = run(df, A, sym); S[f"F1B_{sym}"] = run(df, B, sym); S[f"F1C_{sym}"] = run(df, A + B, sym)

    # ---------- F2 tendencia BTC (Donchian ensemble, vol objetivo 25 %) ----------
    df = load("BTCUSD", "H1", "FTMO"); D = daily_bars(df)
    c = D.close; LBS = [10, 20, 30, 60, 90, 150, 250]
    def donch(c, L, short):
        up = c.rolling(L).max().shift(1); dn = c.rolling(L).min().shift(1); mid = (up + dn) / 2
        pos = np.zeros(len(c)); p = 0
        for i in range(len(c)):
            if np.isnan(up.iloc[i]): continue
            x = c.iloc[i]
            if p == 0:
                if x >= up.iloc[i]: p = 1
                elif short and x <= dn.iloc[i]: p = -1
            elif p == 1 and x < mid.iloc[i]: p = 0 if not short or x > dn.iloc[i] else -1
            elif p == -1 and x > mid.iloc[i]: p = 0 if x < up.iloc[i] else 1
            pos[i] = p
        return pd.Series(pos, index=c.index)
    vol = np.log(c).diff().rolling(30).std() * np.sqrt(365)
    for short in (False, True):
        sig = sum(donch(c, L, short) for L in LBS) / len(LBS)
        wd = (sig * 0.25 / vol).clip(-2, 2)
        S[f"F2_BTC_{'LS' if short else 'L'}"] = run(df, hourly_from_daily(df, wd), "BTCUSD")

    # ---------- F3 reversión corta en índices ----------
    def rsi2(c):
        d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/2).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/2).mean()
        return 100 - 100 / (1 + up / dn)
    for sym in ["US500", "US100", "UK100", "JP225", "US2000", "US30", "GER40"]:
        src = "OANDA" if sym == "US2000" else ("FTMO" if sym in ["US30", "GER40"] else "MIX")
        df = load(sym, "H1", src); D = daily_bars(df)
        D = D[(D.high > D.low)]
        ibs = (D.close - D.low) / (D.high - D.low); r2 = rsi2(D.close)
        for name, entry in [("IBS", ibs < 0.2), ("RSI2", r2 < 10)]:
            pos = np.zeros(len(D)); held = 0
            for i in range(len(D)):
                if held > 0:
                    if D.close.iloc[i] > D.high.iloc[i - 1] or held >= 5: held = 0
                    else: held += 1
                if held == 0 and entry.iloc[i]: held = 1
                pos[i] = 1.0 if held > 0 else 0.0
            S[f"F3_{name}_{sym}"] = run(df, hourly_from_daily(df, pd.Series(pos, index=D.index)), sym)

    # ---------- F4 TSMOM multi-activo ----------
    for sym in ALL17:
        df = load(sym, "H1", src_of(sym)); D = daily_bars(df); c = D.close
        sig = sum(np.sign(np.log(c / c.shift(L))) for L in (20, 60, 120, 250)) / 4
        v = np.log(c).diff().rolling(60).std() * np.sqrt(252)
        wd = (sig * 0.10 / v).clip(-5, 5).fillna(0)
        S[f"F4_{sym}"] = run(df, hourly_from_daily(df, wd), sym)

    # ---------- F6 fin de mes USD ----------
    spx = daily_bars(load("US500", "H1", "MIX")).close
    for sym, usd_base in [("EURUSD", False), ("GBPUSD", False), ("AUDUSD", False), ("USDJPY", True)]:
        df = load(sym, "H1", "FTMO"); w = pd.Series(0.0, index=df.index)
        days = pd.Series(df.index.normalize().unique())
        days = days[days.dt.weekday < 5]
        last = days.groupby([days.dt.year, days.dt.month]).max()
        for d in last:
            mtd_start = spx[spx.index < d.replace(day=1)]
            cur = spx[spx.index < d]  # cierre del día anterior: sin anticipación (corregido)
            if len(mtd_start) == 0 or len(cur) == 0: continue
            us_up = cur.iloc[-1] > mtd_start.iloc[-1]
            sell_usd = us_up
            sgn = 1.0 if sell_usd else -1.0
            if usd_base: sgn = -sgn
            t = d + pd.Timedelta(hours=10)
            if t in w.index: w.loc[t] = sgn
        S[f"F6_{sym}"] = run(df, w, sym)

    # ---------- F7 pares ----------
    for a, b in [("AUDUSD", "NZDUSD"), ("XAUUSD", "XAGUSD")]:
        da = load(a, "H1", "FTMO"); db = load(b, "H1", "FTMO")
        idx = da.index.intersection(db.index); da, db = da.loc[idx], db.loc[idx]
        ca = daily_bars(da).close; cb = daily_bars(db).close
        lr = np.log(ca / cb); z = (lr - lr.rolling(20).mean()) / lr.rolling(20).std()
        pos = np.zeros(len(z)); p = 0; held = 0
        for i in range(len(z)):
            zi = z.iloc[i]
            if p != 0:
                held += 1
                if (p == 1 and zi >= 0) or (p == -1 and zi <= 0) or held >= 10: p = 0; held = 0
            if p == 0 and not np.isnan(zi):
                if zi > 2: p = -1; held = 0
                elif zi < -2: p = 1; held = 0
            pos[i] = p
        pos = pd.Series(pos, index=z.index)
        ra = run(da, hourly_from_daily(da, pos), a); rb = run(db, hourly_from_daily(db, -pos), b)
        S[f"F7_{a[:3]}{b[:3]}"] = ra.add(rb, fill_value=0)

    pickle.dump(S, open(f"{SCR}/sleeves_v2.pkl", "wb"))
    rows = []
    for k, d in S.items():
        i, o = split(d)
        si, so = stats(i, k), stats(o, k)
        rows.append(dict(manga=k, sh_IS=si.get("sharpe"), ann_IS=si.get("ann"), sh_OOS=so.get("sharpe"), ann_OOS=so.get("ann"),
                         vol_OOS=so.get("vol"), dd_OOS=so.get("maxdd"), dias_act_OOS=so.get("activos"),
                         turn_OOS=o.turn.sum() / max(1, (o.index[-1] - o.index[0]).days / 365.25) if len(o) else np.nan))
    R = show(rows)
    R.to_csv("out_families.csv", index=False)
