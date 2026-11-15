import sys; sys.path.insert(0, "src")
from common import *
for inst in ["SPX500_USD", "NAS100_USD", "XAU_USD", "EUR_USD", "WTICO_USD", "UK100_GBP", "FR40_EUR", "US2000_USD", "JP225_USD"]:
    df = load(inst)
    r = rth(df)
    c = r.groupby(r.index.date).size()
    c = pd.Series(c.values, index=pd.to_datetime(c.index))
    full = df.groupby(df.index.date).size(); full = pd.Series(full.values, index=pd.to_datetime(full.index))
    by = pd.DataFrame({"dias": c.groupby(c.index.year).size(), "min_rth_med": c.groupby(c.index.year).median(),
                       "min_rth_p10": c.groupby(c.index.year).quantile(0.1), "min_dia_med": full.groupby(full.index.year).median()})
    # rango tipico de barra M1 en bps como proxy de spread/ruido
    by["rng_bps_med"] = ((r.high - r.low) / r.close * 1e4).groupby(r.index.year).median()
    print(inst); print(by.T.round(1).to_string()); print()
