"""Rejilla dia x minuto (hora local) por instrumento, cacheada en npz."""
import os, numpy as np, pandas as pd
from common import load, DATA
def build(inst, tz="America/New_York"):
    fn = f"{DATA}/{inst}_{tz.replace('/', '-')}_grid.npz"
    if os.path.exists(fn):
        z = np.load(fn, allow_pickle=False)
        return pd.to_datetime(z["dates"]), z["O"], z["H"], z["L"], z["C"], z["V"]
    df = load(inst, tz)
    d = df.index.normalize().tz_localize(None)
    dates = pd.DatetimeIndex(sorted(d.unique()))
    di = dates.get_indexer(d)
    mi = df.index.hour.values * 60 + df.index.minute.values
    out = []
    for col in ["open", "high", "low", "close", "volume"]:
        a = np.full((len(dates), 1440), np.nan, dtype=np.float64)
        a[di, mi] = df[col].values
        out.append(a)
    np.savez(fn, dates=dates.values.astype("datetime64[D]"), O=out[0], H=out[1], L=out[2], C=out[3], V=out[4])
    return (dates, *out)
def ffill_flat(C):
    """ffill a lo largo del tiempo continuo (aplana dias)."""
    f = C.reshape(-1).copy()
    idx = np.where(~np.isnan(f), np.arange(len(f)), 0)
    np.maximum.accumulate(idx, out=idx)
    f = f[idx]
    return f.reshape(C.shape)
