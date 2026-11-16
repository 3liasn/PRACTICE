"""Motor común: carga de datos, P&L por barra con costes y swap, agregación por día FTMO (Europe/Prague)."""
import numpy as np, pandas as pd
PQ = "/home/user/data2/pq"
# Coste ida y vuelta (fracción del nocional): spread FTMO medido + comisión + deslizamiento, redondeado al alza.
COST = dict(XAUUSD=3e-4, XAGUSD=6e-4, NSXUSD=2e-4, SPXUSD=2e-4, GRXEUR=2.5e-4, JPXJPY=3e-4, WTIUSD=6e-4,
            EURUSD=1.2e-4, GBPUSD=1.6e-4, USDJPY=1.4e-4, AUDUSD=1.6e-4, BTCUSDT=12e-4, ETHUSDT=15e-4,
            # cruces FX: spread nocturno FTMO estimado + comisión (~0,5 pip), conservador
            EURGBP=2.2e-4, EURCHF=2.4e-4, AUDNZD=3.0e-4, AUDCAD=3.0e-4, GBPCHF=3.0e-4, USDCHF=2.2e-4, USDCAD=1.8e-4,
            EURCAD=2.4e-4, GBPCAD=2.8e-4, EURAUD=2.4e-4, NZDCAD=4.0e-4)
# Swap anual aproximado (fracción del nocional por año) para (largo, corto); negativo = pago.
# Oro/índices de especificaciones.json del servidor FTMO; cripto conservador.
SWAP = dict(XAUUSD=(-0.06, -0.004), XAGUSD=(-0.06, -0.01), NSXUSD=(-0.09, 0.0), SPXUSD=(-0.09, 0.0),
            GRXEUR=(-0.06, 0.0), JPXJPY=(-0.04, -0.01), WTIUSD=(-0.06, -0.02), EURUSD=(-0.02, -0.01),
            GBPUSD=(-0.02, -0.01), USDJPY=(0.0, -0.05), AUDUSD=(-0.02, -0.02), BTCUSDT=(-0.25, -0.25), ETHUSDT=(-0.25, -0.25),
            **{k: (-0.02, -0.02) for k in ['EURGBP','EURCHF','AUDNZD','AUDCAD','GBPCHF','USDCHF','USDCAD','EURCAD','GBPCAD','EURAUD','NZDCAD']})
# Coste absoluto en unidades de precio (ida y vuelta) cuando es más fiel que un porcentaje.
# Oro: spread FTMO medido 0,30–0,46 (data/oro/spread_por_hora.csv) + comisión ~0,0014 % + 0,1 de deslizamiento.
COST_ABS = dict(XAUUSD=0.45)
def cost_frac(sym, price):
    sym = sym.replace('_FTMO', '')
    return COST_ABS[sym] / price if sym in COST_ABS else COST[sym] + 0 * price
_c = {}
def load(sym, tf="5min"):
    k = (sym, tf)
    if k in _c: return _c[k]
    if sym == "XAUUSD_FTMO": df = pd.read_parquet(f"{PQ}/XAUUSD_FTMO_M5.parquet")
    else: df = pd.read_parquet(f"{PQ}/{sym}.parquet")
    if tf != "1min" and not (sym == "XAUUSD_FTMO" and tf == "5min"):
        df = df.resample(tf, label="left", closed="left").agg(dict(open="first", high="max", low="min", close="last")).dropna()
    df = df[df.index >= "2016-01-01"]
    _c[k] = df; return df
def bar_pnl(close, pos, sym):
    """pos[t] = exposición (nocional / capital inicial) mantenida desde el cierre de t hasta el de t+1.
    Devuelve P&L por barra (fracción del capital inicial, sin componer: riesgo fijo como en FTMO con retiros)."""
    sym = sym.replace("_FTMO", "")
    c = close.values; p = np.nan_to_num(np.asarray(pos, float))
    ret = np.zeros_like(c); ret[1:] = c[1:] / c[:-1] - 1
    ret[np.abs(ret) > 0.2] = 0  # huecos de datos absurdos
    held = np.zeros_like(p); held[1:] = p[:-1]
    pnl = held * ret
    dp = np.abs(np.diff(np.concatenate([[0], p])))
    pnl -= dp * cost_frac(sym, c) / 2
    # swap: se cobra si la posición cruza las 17:00 de Nueva York (rollover); miércoles triple en FX/metales
    ny = close.index.tz_convert("America/New_York")
    day = ny.date
    newday = np.zeros(len(c), bool); hrs = ny.hour.values
    after = (hrs >= 17)
    key = np.where(after, pd.to_datetime(day).values + np.timedelta64(1, "D"), pd.to_datetime(day).values)
    newday[1:] = key[1:] != key[:-1]
    sl, ss = SWAP[sym]
    mult = np.ones(len(c)); wd = ny.dayofweek.values
    mult[(wd == 2) & newday] = 3 if sym not in ("NSXUSD", "SPXUSD", "GRXEUR", "JPXJPY", "BTCUSDT", "ETHUSDT") else 1
    sw = np.where(held > 0, held * sl / 360, np.abs(held) * ss / 360)
    pnl += np.where(newday, sw * mult, 0)
    return pd.Series(pnl, index=close.index)
def daily(pnl):
    """Agrega P&L por barra a días de Praga: pnl del día y peor flotante intradía (mínimo acumulado, <=0)."""
    pr = pnl.index.tz_convert("Europe/Prague")
    g = pd.Series(pnl.values, index=pr.date)
    cum = g.groupby(level=0).cumsum()
    out = pd.DataFrame({"pnl": g.groupby(level=0).sum(), "low": cum.groupby(level=0).min().clip(upper=0),
                        "act": (g != 0).groupby(level=0).any()})
    out.index = pd.to_datetime(out.index)
    return out
def stats(d, name=""):
    x = d["pnl"] if isinstance(d, pd.DataFrame) else d
    m = x.groupby([x.index.year, x.index.month]).sum()
    ann = x.sum() / ((x.index[-1] - x.index[0]).days / 365.25)
    vol = m.std() * np.sqrt(12)
    eq = x.cumsum(); dd = (eq - eq.cummax()).min()
    return dict(name=name, mes=m.mean() * 100, sharpe_m=ann / vol if vol > 0 else np.nan, maxdd=dd * 100,
                mes_pos=(m > 0).mean() * 100, peor_mes=m.min() * 100,
                peor_dia=(d["low"].min() * 100 if isinstance(d, pd.DataFrame) else x.min() * 100))
def show(rows):
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.float_format", "{:.2f}".format):
        print(pd.DataFrame(rows).to_string(index=False))
