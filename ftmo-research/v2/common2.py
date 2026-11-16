"""Librería común v2: datos, costes FTMO, motor de posiciones horarias y simulador de reglas FTMO 2-Step.

Convenciones
- Índice temporal = hora de Nueva York sin zona (servidor FTMO = NY+7). Barra etiquetada por su apertura.
- Día de trading = fecha de (hora NY + 7 h): cierra a las 17:00 NY, como el servidor.
- Pesos w = exposición nocional / balance inicial (w=1 → 100 % del balance). P&L sin componer: con riesgo fijo
  sobre el balance inicial, como en una cuenta FTMO que retira beneficios.
"""
import os, json
import numpy as np, pandas as pd

SCR = os.environ.get("SCR", "/tmp/claude-0/-home-user/ca8409e6-4186-5384-a79e-a0bc2932a16c/scratchpad")
DATA = f"{SCR}/data"
SPEC = f"{SCR}/ftmo/datos_ftmo_vps"
IS_END = pd.Timestamp("2021-01-01")
OOS_END = pd.Timestamp("2026-10-16")

FX = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
METALS = ["XAUUSD", "XAGUSD"]
INDICES = ["US500", "US100", "US30", "GER40", "UK100", "JP225"]
OIL = ["USOIL", "UKOIL"]
ALL17 = METALS + INDICES + FX + OIL

_cache = {}
def load(sym, tf="H1", src="FTMO"):
    """src='FTMO' (2015/2021-2026), 'OANDA' (2005-2020) o 'MIX' (OANDA hasta 2020-12-31 y FTMO después)."""
    k = (sym, tf, src)
    if k in _cache: return _cache[k]
    if src == "FTMO":
        f = f"{DATA}/{sym}_{tf}.parquet"
        df = pd.read_parquet(f)
    elif src == "OANDA":
        df = pd.read_parquet(f"{DATA}/OANDA_{sym}_{tf}.parquet")
    elif src == "MIX":
        a = load(sym, tf, "OANDA"); b = load(sym, tf, "FTMO")
        b = b[b.index >= IS_END] if sym in INDICES + OIL else b
        a = a[a.index < b.index[0]]
        df = pd.concat([a, b])
    df = df[["open", "high", "low", "close"]].astype("float64")
    df = df[df.index < OOS_END + pd.Timedelta(days=40)]
    _cache[k] = df
    return df

def tday(idx):
    """Día de trading del servidor (cierra 17:00 NY)."""
    return (idx + pd.Timedelta(hours=7)).normalize()

# ---------------- costes ----------------
_spec = json.load(open(f"{SPEC}/especificaciones.json"))
_sph = pd.read_csv(f"{SPEC}/spread_por_hora.csv")
_px26 = {}
def _price_2026(sym):
    if sym not in _px26:
        try:
            d = load(sym, "H1", "FTMO"); _px26[sym] = float(d.loc["2025-01-01":, "close"].median())
        except Exception:
            _px26[sym] = np.nan
    return _px26[sym]

COMM_RT_BP = {**{s: 0.5 for s in FX}, **{s: 1.0 for s in METALS}, **{s: 0.0 for s in INDICES + OIL},
              "BTCUSD": 13.0, "US2000": 0.0, "FRA40": 0.0, "AUS200": 0.0, "NL25": 0.0, "EURJPY": 0.5, "AUDJPY": 0.5}
SLIP_RT_BP = 0.5
PROXY = {"US2000": "US500", "FRA40": "GER40", "AUS200": "JP225", "NL25": "GER40", "EURJPY": "USDJPY", "AUDJPY": "USDJPY"}

def spread_bp_by_hour(sym):
    """24 valores: spread mediano (pb del precio 2025-26) por hora NY. BTC: 5 pb fijos (supuesto)."""
    if sym == "BTCUSD": return np.full(24, 5.0)
    s = PROXY.get(sym, sym)
    d = _sph[_sph.simbolo == s].set_index("hora_ny")["spread_med"].reindex(range(24))
    d = d.fillna(d.max())  # horas sin ticks (cierre) -> el peor spread
    return (d.values / _price_2026(s) * 1e4)

def cost_bp_by_hour(sym, mult=1.0):
    """Coste por ida y vuelta (pb) por hora NY: spread + comisión + deslizamiento."""
    return mult * (spread_bp_by_hour(sym) + COMM_RT_BP.get(sym, 0.5) + SLIP_RT_BP)

def swap_bp(sym):
    """(largo, corto) en pb del nocional por noche, foto 2026-10-16. BTC: −3 pb/noche en ambos lados (supuesto)."""
    if sym == "BTCUSD": return (-3.0, -3.0)
    s = PROXY.get(sym, sym)
    sp = _spec[s]; px = _price_2026(s)
    return (sp["swap_long"] * sp["point"] / px * 1e4, sp["swap_short"] * sp["point"] / px * 1e4)

def triple_day(sym):
    """weekday (0=lunes) del día cuyo rollover cobra triple."""
    if sym == "BTCUSD": return None
    s = PROXY.get(sym, sym)
    return 2 if _spec[s]["swap_rollover3days"] == 3 else 4

# ---------------- motor ----------------
def run(df, w, sym, cost_mult=1.0, swap=True):
    """df: velas (H1 o M5) de sym; w: Serie de pesos alineada a df.index = exposición mantenida DURANTE la barra
    (decidida con información hasta el cierre de la barra anterior). Devuelve DataFrame diario con
    pnl (fracción del balance inicial), worst (mínimo intradía acumulado del día), turnover, expo."""
    w = w.reindex(df.index).fillna(0.0).values
    c = df["close"].values; lo = df["low"].values; hi = df["high"].values
    prev = np.r_[np.nan, c[:-1]]
    r = c / prev - 1.0; r[0] = 0.0
    rlo = lo / prev - 1.0; rhi = hi / prev - 1.0; rlo[0] = 0; rhi[0] = 0
    gap = np.r_[False, np.diff(df.index.values).astype("timedelta64[h]").astype(float) > 24 * 5]
    r[gap] = 0.0; rlo[gap] = 0.0; rhi[gap] = 0.0   # hueco entre feeds (OANDA->FTMO): sin P&L
    # huecos de varios días (fin de semana): el retorno de la primera barra ya incluye el hueco: correcto.
    pnl = w * r
    worst_bar = np.where(w > 0, w * rlo, np.where(w < 0, w * rhi, 0.0))
    hours = df.index.hour.values
    cbp = cost_bp_by_hour(sym, cost_mult)[hours] / 1e4
    dw = np.abs(np.diff(np.r_[0.0, w]))
    cost = dw * cbp / 2.0
    td = tday(df.index)
    out = pd.DataFrame({"pnl": pnl - cost, "worst_bar": worst_bar - cost, "turn": dw, "absw": np.abs(w)}, index=df.index)
    out["td"] = td
    # swap: posición que cruza el cierre de día (última barra del día y primera del siguiente, mismo signo)
    if swap:
        g = out.groupby("td")
        last_w = pd.Series(w, index=df.index).groupby(td).last()
        first_w = pd.Series(w, index=df.index).groupby(td).first().shift(-1)
        carried = np.where(np.sign(last_w) == np.sign(first_w), np.sign(last_w) * np.minimum(abs(last_w), abs(first_w)), 0.0)
        sl, ss = swap_bp(sym)
        rate = np.where(carried > 0, sl, np.where(carried < 0, ss, 0.0)) / 1e4
        mult = np.ones(len(last_w))
        tdw = triple_day(sym)
        if tdw is not None:
            mult = np.where(last_w.index.weekday == tdw, 3.0, 1.0)
        else:
            mult = np.where(last_w.index.weekday == 4, 3.0, 1.0)  # BTC: viernes cubre el fin de semana
        swp = pd.Series(np.abs(carried) * rate * mult, index=last_w.index)
    # agregación diaria con peor punto intradía
    pnl_s = out["pnl"].values
    cum_before = out.groupby("td")["pnl"].cumsum().values - pnl_s
    out["dip"] = cum_before + np.minimum(out["worst_bar"].values, 0.0)
    daily = out.groupby("td").agg(pnl=("pnl", "sum"), worst=("dip", "min"), turn=("turn", "sum"), expo=("absw", "mean"))
    if swap:
        daily["pnl"] += swp.reindex(daily.index).fillna(0.0)
    daily["worst"] = np.minimum(daily["worst"], np.minimum(daily["pnl"], 0.0))
    return daily

# ---------------- estadística ----------------
def stats(d, name="", col="pnl"):
    x = d[col].dropna() if isinstance(d, pd.DataFrame) else d.dropna()
    x = x[x.index.weekday < 7]
    if len(x) < 20: return dict(name=name, n=len(x))
    act = x[x != 0]
    yrs = (x.index[-1] - x.index[0]).days / 365.25
    ann = x.sum() / yrs
    vol = x.std() * np.sqrt(len(x) / yrs)
    eq = x.cumsum(); dd = (eq - eq.cummax()).min()
    m = x.groupby([x.index.year, x.index.month]).sum()
    return dict(name=name, dias=len(x), activos=len(act), ann=ann, vol=vol, sharpe=ann / vol if vol > 0 else np.nan,
                maxdd=dd, mes_med=m.mean(), mes_pos=(m > 0).mean(), peor_mes=m.min(), peor_dia=x.min())

def show(rows, fmt="{:.3f}"):
    df = pd.DataFrame(rows)
    with pd.option_context("display.width", 250, "display.max_columns", 40, "display.float_format", fmt.format):
        print(df.to_string(index=False))
    return df

def split(d):
    return d[d.index < IS_END], d[(d.index >= IS_END) & (d.index < OOS_END)]

# ---------------- simulador FTMO ----------------
def ftmo_path(pnl, worst, start=0, target=0.10, daily=0.05, maxl=0.10, min_days=4, max_days=None):
    """Recorre días desde start. Devuelve (resultado, días usados) con resultado 'pass'|'fail'|'timeout'."""
    bal = 0.0; traded = 0; n = len(pnl)
    end = n if max_days is None else min(n, start + max_days)
    for i in range(start, end):
        if worst[i] <= -daily or bal + worst[i] <= -maxl:
            return "fail", i - start + 1
        bal += pnl[i]
        if pnl[i] != 0: traded += 1
        if bal >= target and traded >= min_days:
            return "pass", i - start + 1
    return "timeout", end - start

def ftmo_funded(pnl, worst, start, months=12, split_=0.8, keep=0.0, daily=0.05, maxl=0.10, day_index=None):
    """Cuenta fondeada: cada fin de mes retira lo que exceda 'keep' (fracción del balance inicial).
    Devuelve (perdida(bool), pagos_brutos_totales, meses_vividos)."""
    bal = 0.0; paid = 0.0
    idx = day_index
    m0 = (idx[start].year, idx[start].month); months_seen = 0
    for i in range(start, len(pnl)):
        cur = (idx[i].year, idx[i].month)
        if cur != m0:
            months_seen += 1; m0 = cur
            if bal > keep:
                paid += (bal - keep) * split_; bal = keep
            if months_seen >= months: return False, paid, months_seen
        if worst[i] <= -daily or bal + worst[i] <= -maxl:
            return True, paid, months_seen
        bal += pnl[i]
    return False, paid, months_seen

def block_bootstrap(n_days, length, block, rng):
    starts = rng.integers(0, n_days - block, size=length // block + 1)
    return np.concatenate([np.arange(s, s + block) for s in starts])[:length]
