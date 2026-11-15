import numpy as np, pandas as pd
DATA = "/home/user/ftmo-research/data"
_cache = {}
def load(inst, tz="America/New_York"):
    k = (inst, tz)
    if k not in _cache:
        df = pd.read_parquet(f"{DATA}/{inst}_M1.parquet")
        df.index = df.index.tz_convert(tz)
        _cache[k] = df
    return _cache[k]
def rth(df, start="09:30", end="16:00"):
    """Barras M1 de la sesion [start, end) en la zona horaria del indice."""
    t = df.index.time
    s = pd.Timestamp(start).time(); e = pd.Timestamp(end).time()
    m = (t >= s) & (t < e)
    return df[m]
def stats(daily, name="", ppy=252):
    """daily: Serie de retornos diarios (fraccion del capital). """
    d = daily.dropna()
    if len(d) == 0: return {}
    mu = d.mean() * ppy; sd = d.std() * np.sqrt(ppy)
    eq = d.cumsum()  # no compuesto (riesgo fijo sobre balance inicial, como en FTMO con retiros)
    dd = (eq - eq.cummax()).min()
    m = d.groupby([d.index.year, d.index.month]).sum()
    return dict(name=name, n=len(d), ann=mu, vol=sd, sharpe=mu / sd if sd > 0 else np.nan, maxdd=dd,
                calmar=mu / abs(dd) if dd < 0 else np.nan, mes_prom=m.mean(), mes_pos=(m > 0).mean(),
                peor_mes=m.min(), peor_dia=d.min())
def show(rows):
    df = pd.DataFrame(rows)
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.float_format", "{:.3f}".format):
        print(df.to_string(index=False))
