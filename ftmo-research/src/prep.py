"""Convierte los CSV M1 de OANDA (repo publico FutureSharks/financial-data) a parquet por instrumento."""
import sys, glob, os
import pandas as pd
from multiprocessing import Pool
SRC = "/home/user/data_src/futuresharks/pyfinancialdata/data/currencies/oanda"
OUT = "/home/user/ftmo-research/data"
def conv(inst):
    files = glob.glob(f"{SRC}/{inst}/*/*.csv")
    dfs = []
    for f in files:
        d = pd.read_csv(f)
        if len(d): dfs.append(d)
    df = pd.concat(dfs, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.drop_duplicates("time").sort_values("time").set_index("time")
    df = df[["open", "high", "low", "close", "volume"]].astype("float64")
    df.to_parquet(f"{OUT}/{inst}_M1.parquet")
    return inst, len(df), str(df.index[0]), str(df.index[-1])
if __name__ == "__main__":
    insts = sorted(d for d in os.listdir(SRC) if os.path.isdir(f"{SRC}/{d}"))
    with Pool(4) as p:
        for r in p.imap_unordered(conv, insts):
            print(*r, flush=True)
