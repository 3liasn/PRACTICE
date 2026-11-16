"""Datos v2: velas reales del servidor FTMO (rama data/ftmo-vps de apex-v9) + BTC Bitstamp M1.

Salida (parquet, en SCRATCH/data):
  <SYM>_H1.parquet, <SYM>_M5.parquet : índice = hora NY (naive; servidor FTMO = NY+7), columnas OHLC + vol
  BTCUSD_H1.parquet / BTCUSD_M5.parquet : misma convención (hora NY naive)
Se descarta el tramo anterior a 'intradía continuo desde' en índices y petróleo.
"""
import os, gzip, pandas as pd, numpy as np
from multiprocessing import Pool
SCR = os.environ.get("SCR", "/tmp/claude-0/-home-user/ca8409e6-4186-5384-a79e-a0bc2932a16c/scratchpad")
SRC = f"{SCR}/ftmo/datos_ftmo_vps"
OUT = f"{SCR}/data"
os.makedirs(OUT, exist_ok=True)
SYMS = ["XAUUSD", "XAGUSD", "US500", "US100", "US30", "GER40", "UK100", "JP225", "EURUSD", "GBPUSD",
        "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "USOIL", "UKOIL"]
# primera fecha con intradía continuo (README de datos_ftmo_vps, columna M5 y H1)
CONT = {"H1": {"GER40": "2021-05-03", "JP225": "2021-02-01", "UK100": "2021-01-04", "UKOIL": "2021-01-04",
               "US100": "2021-02-01", "US30": "2019-02-08", "US500": "2021-02-01", "USOIL": "2021-01-04"},
        "M5": {"GER40": "2022-01-03", "JP225": "2021-09-01", "UK100": "2021-09-01", "UKOIL": "2021-01-04",
               "US100": "2021-09-01", "US30": "2019-02-08", "US500": "2021-09-01", "USOIL": "2021-01-04"}}

def conv(args):
    sym, tf = args
    df = pd.read_csv(f"{SRC}/{sym}{tf}_FTMO.csv.gz", header=None,
                     names=["t", "open", "high", "low", "close", "vol"])
    df["t"] = pd.to_datetime(df["t"], format="%Y.%m.%d %H:%M") - pd.Timedelta(hours=7)  # -> hora NY
    df = df.drop_duplicates("t").set_index("t").sort_index()
    c = CONT[tf].get(sym)
    if c: df = df[df.index >= pd.Timestamp(c)]
    df = df.iloc[1:]  # la primera barra puede ser un agregado
    df.to_parquet(f"{OUT}/{sym}_{tf}.parquet")
    return sym, tf, len(df), str(df.index[0]), str(df.index[-1])

def btc():
    a = pd.read_csv(f"{SCR}/crypto/btc_hist.csv.gz")
    b = pd.read_csv(f"{SCR}/crypto/btc_latest.csv")
    df = pd.concat([a, b]).drop_duplicates("timestamp").sort_values("timestamp")
    t = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    df = df.assign(t=t).set_index("t")[["open", "high", "low", "close", "volume"]].rename(columns={"volume": "vol"})
    df = df[~df.index.duplicated()]
    df = df[df.index >= "2015-01-01"]
    out = []
    for tf, rule in [("M5", "5min"), ("H1", "1h")]:
        r = df.resample(rule, label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"}).dropna()
        r.to_parquet(f"{OUT}/BTCUSD_{tf}.parquet")
        out.append(("BTCUSD", tf, len(r), str(r.index[0]), str(r.index[-1])))
    return out

if __name__ == "__main__":
    with Pool(8) as p:
        for r in p.imap_unordered(conv, [(s, tf) for s in SYMS for tf in ("H1", "M5")]):
            print(*r, flush=True)
    for r in btc(): print(*r, flush=True)
