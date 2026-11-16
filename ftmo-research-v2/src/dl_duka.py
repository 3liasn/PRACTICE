"""Descarga velas M1 BID de Dukascopy (archivos diarios .bi5), con caché por día y reanudable.
Uso: python3 dl_duka.py SIMBOLO DIVISOR [hilos]"""
import lzma, sys, os, datetime as dt, urllib.request, urllib.error, time, random
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
OUT = "/home/user/data2/duka"; RAW = "/home/user/data2/duka_raw"
def fetch(sym, d):
    p = f"{RAW}/{sym}/{d:%Y%m%d}.bi5"
    if os.path.exists(p): return p
    url = f"https://datafeed.dukascopy.com/datafeed/{sym}/{d.year}/{d.month-1:02d}/{d.day:02d}/BID_candles_min_1.bi5"
    for k in range(12):
        try:
            with urllib.request.urlopen(url, timeout=30) as r: raw = r.read()
            open(p + ".tmp", "wb").write(raw); os.replace(p + ".tmp", p); return p
        except urllib.error.HTTPError as e:
            if e.code == 404: open(p, "wb").close(); return p
            time.sleep(min(60, 2 ** k) + random.random())
        except Exception:
            time.sleep(min(60, 2 ** k) + random.random())
    print("FAIL", sym, d, flush=True); return None
def parse(p, d):
    raw = open(p, "rb").read()
    if not raw: return None
    b = lzma.decompress(raw)
    a = np.frombuffer(b, dtype=">u4").reshape(-1, 6)
    v = np.frombuffer(b, dtype=">f4").reshape(-1, 6)[:, 5]
    base = int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp())
    return np.column_stack([a[:, 0].astype(np.int64) + base, a[:, 1:5].astype(np.float64), v.astype(np.float64)])
def run(sym, start, end, div, th):
    os.makedirs(f"{RAW}/{sym}", exist_ok=True)
    days = [start + dt.timedelta(i) for i in range((end - start).days + 1)]
    days = [d for d in days if d.weekday() != 5]
    with ThreadPoolExecutor(th) as ex: paths = list(ex.map(lambda d: fetch(sym, d), days))
    nfail = sum(p is None for p in paths)
    arr = np.vstack([r for r in (parse(p, d) for p, d in zip(paths, days) if p) if r is not None and len(r)])
    df = pd.DataFrame(arr, columns=["t", "open", "close", "low", "high", "volume"])
    df["time"] = pd.to_datetime(df.t.astype(np.int64), unit="s", utc=True)
    df = df.set_index("time")[["open", "high", "low", "close", "volume"]]
    df[["open", "high", "low", "close"]] /= div
    df = df[df.volume > 0]
    df = df[~df.index.duplicated()].sort_index()
    df.to_parquet(f"{OUT}/{sym}_M1.parquet")
    print(sym, len(df), df.index[0], df.index[-1], df.close.iloc[-1], "fallos:", nfail, flush=True)
if __name__ == "__main__":
    sym, div = sys.argv[1], float(sys.argv[2]); th = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    run(sym, dt.date(2016, 1, 1), dt.date(2026, 11, 13), div, th)
