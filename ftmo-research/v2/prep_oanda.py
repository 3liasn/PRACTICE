"""OANDA M1 2005-2020 (repo público FutureSharks/financial-data) -> M5/H1 en hora NY naive, para el tramo IS."""
import os, glob, pandas as pd
from multiprocessing import Pool
SCR = os.environ.get("SCR", "/tmp/claude-0/-home-user/ca8409e6-4186-5384-a79e-a0bc2932a16c/scratchpad")
SRC = f"{SCR}/fs/pyfinancialdata/data/currencies/oanda"
OUT = f"{SCR}/data"
MAP = {"SPX500_USD": "US500", "NAS100_USD": "US100", "UK100_GBP": "UK100", "JP225_USD": "JP225",
       "WTICO_USD": "USOIL", "XAU_USD": "XAUUSD", "US2000_USD": "US2000", "FR40_EUR": "FRA40",
       "AU200_AUD": "AUS200", "EUR_USD": "EURUSD", "GBP_USD": "GBPUSD", "AUD_USD": "AUDUSD", "USD_CAD": "USDCAD",
       "EUR_JPY": "EURJPY", "AUD_JPY": "AUDJPY", "NL25_EUR": "NL25"}
def conv(inst):
    files = sorted(glob.glob(f"{SRC}/{inst}/*/*.csv"))
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    df = df.drop_duplicates("time").sort_values("time").set_index("time")[["open", "high", "low", "close", "volume"]]
    df = df.rename(columns={"volume": "vol"}).astype("float64")
    out = []
    for tf, rule in [("M5", "5min"), ("H1", "1h")]:
        r = df.resample(rule).agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"}).dropna()
        r.to_parquet(f"{OUT}/OANDA_{MAP[inst]}_{tf}.parquet")
        out.append((MAP[inst], tf, len(r), str(r.index[0]), str(r.index[-1])))
    return out
if __name__ == "__main__":
    with Pool(4) as p:
        for res in p.imap_unordered(conv, list(MAP)):
            for r in res: print(*r, flush=True)
