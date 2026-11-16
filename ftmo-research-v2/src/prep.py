"""Convierte HistData (EST fija = UTC-5, sin horario de verano) y Binance (UTC) a parquet M1 en UTC.
Fuentes: histdata.com (descarga gratuita ASCII M1) y data.binance.vision (klines spot 1m)."""
import glob, zipfile, io, os, sys
import pandas as pd, numpy as np
H = "/home/user/data2/hist"; B = "/home/user/data2/binance"; OUT = "/home/user/data2/pq"
def hist(pair):
    dfs = []
    for f in sorted(glob.glob(f"{H}/{pair}_*.zip")):
        z = zipfile.ZipFile(f)
        name = [n for n in z.namelist() if n.endswith(".csv")][0]
        d = pd.read_csv(z.open(name), sep=";", header=None, names=["t", "open", "high", "low", "close", "volume"])
        dfs.append(d)
    df = pd.concat(dfs, ignore_index=True)
    df["time"] = pd.to_datetime(df.t, format="%Y%m%d %H%M%S") + pd.Timedelta(hours=5)
    df = df.set_index(pd.DatetimeIndex(df.time).tz_localize("UTC"))[["open", "high", "low", "close"]]
    df = df[~df.index.duplicated()].sort_index()
    df.to_parquet(f"{OUT}/{pair}.parquet"); print(pair, len(df), df.index[0], df.index[-1], df.close.iloc[-1], flush=True)
def binance(sym):
    dfs = []
    for f in sorted(glob.glob(f"{B}/{sym}-1m-*.zip")):
        z = zipfile.ZipFile(f)
        d = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 1, 2, 3, 4, 5])
        dfs.append(d)
    df = pd.concat(dfs, ignore_index=True); df.columns = ["t", "open", "high", "low", "close", "volume"]
    t = df.t.astype(np.int64); t = np.where(t > 1e14, t // 1000, t)  # Binance pasó a microsegundos en 2025
    df.index = pd.to_datetime(t, unit="ms", utc=True)
    df = df[["open", "high", "low", "close"]]
    df = df[~df.index.duplicated()].sort_index()
    df.to_parquet(f"{OUT}/{sym}.parquet"); print(sym, len(df), df.index[0], df.index[-1], df.close.iloc[-1], flush=True)
def ftmo_gold():
    """Oro M5 del servidor FTMO (hora servidor = Nueva York + 7 h)."""
    df = pd.read_csv("/home/user/asistente-trading/data/oro/XAUUSDM5_FTMO.csv.gz", header=None,
                     names=["t", "open", "high", "low", "close", "v"])
    t = pd.to_datetime(df.t, format="%Y.%m.%d %H:%M") - pd.Timedelta(hours=7)
    idx = pd.DatetimeIndex(t).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    df.index = idx; df = df[df.index.notna()].tz_convert("UTC")[["open", "high", "low", "close"]]
    df = df[~df.index.duplicated()].sort_index()
    df.to_parquet(f"{OUT}/XAUUSD_FTMO_M5.parquet"); print("FTMO gold", len(df), df.index[0], df.index[-1])
if __name__ == "__main__":
    for a in sys.argv[1:]:
        if a == "ftmo": ftmo_gold()
        elif a.endswith("USDT"): binance(a)
        else: hist(a)
