"""v3: ¿qué aporta a la cartera de bot-definitivo (RANGE3big+S2_A1.5_N207) añadir fuentes NO-oro?
Cartera oro reconstruida desde el ledger por operación de la tanda 15 (Dukascopy, motor backtest_v3).
Fuentes nuevas: reversión IBS/RSI2 en índices USA/JP (v2) y tendencia BTC (v2). Regla de mezcla fijada antes:
paridad de riesgo entre mangas con la vol IS (<2020); después se escala todo a la P(quiebra 12 m) de la cartera actual."""
import sys, pickle; sys.path.insert(0, "../v2")
from common2 import *
from numba import njit
LED = f"{SCR}/bd/backtest_v3_out_tanda15_ledger_duka.parquet"
RISK = {"ACompression": 1.5, "N59f": 0.5, "W_dst": 0.5, "N141": 0.5, "N30GapFade": 0.25}
RANGE = {"N59f", "W_dst", "N141"}

def gold_daily():
    d = pd.read_parquet(LED).sort_values("entry_ns").reset_index(drop=True)
    open_rng = []  # (exit_ns, risk)
    risk = np.zeros(len(d))
    for i, r in d.iterrows():
        open_rng = [(x, k) for (x, k) in open_rng if x > r.entry_ns]
        if r.strategy in RANGE:
            used = sum(k for _, k in open_rng)
            k = max(0.0, min(0.5, 0.75 - used)); risk[i] = k
            if k > 0: open_rng.append((r.exit_ns, k))
        else:
            risk[i] = RISK[r.strategy]
    d["pnl"] = d.r * risk / 100
    ex = pd.to_datetime(d.exit_ns, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    d["td"] = tday(pd.DatetimeIndex(ex))
    g = d.groupby("td").pnl.sum()
    g = g[g.index.weekday < 5]
    return pd.DataFrame({"pnl": g, "worst": np.minimum(g, 0)}), d

@njit(cache=True)
def account(pnl, worst, idx, k, months, mdays, brake):
    """12 meses fondeada con freno S2 sobre el DD desde el máximo; retiro mensual. -> (quiebra, pagos, peor_dia)"""
    bal = 0.0; peak = 0.0; paid = 0.0
    for t in range(months * mdays):
        i = idx[t]; m = 1.0
        if brake:
            dd = peak - bal
            if dd >= 0.04: m = 0.25
            elif dd >= 0.02: m = 0.5
        p = pnl[i] * k * m; w = worst[i] * k * m
        if w <= -0.05 or bal + w <= -0.10: return 1, paid
        bal += p; peak = max(peak, bal)
        if (t + 1) % mdays == 0 and bal > 0:
            paid += bal; bal = 0.0; peak = 0.0
    return 0, paid

def mc(df, k, brake=True, nsim=20000, seed=5):
    o = df[(df.index >= "2020-01-01") & (df.index < OOS_END)]
    pnl, worst = o.pnl.values, o.worst.values; n = len(pnl); rng = np.random.default_rng(seed)
    L = np.zeros(nsim); P = np.zeros(nsim)
    for s in range(nsim):
        idx = block_bootstrap(n, 12 * 21 + 20, 20, rng)
        L[s], P[s] = account(pnl, worst, idx, k, 12, 21, brake)
    return L.mean(), P.mean() / 12

def hist(df, k, start="2020-01-01"):
    o = df[(df.index >= start) & (df.index < OOS_END)] * k
    m = o.pnl.groupby([o.index.year, o.index.month]).sum(); eq = o.pnl.cumsum()
    return dict(mes=m.mean(), mediana=m.median(), peor_mes=m.min(), peor_dia=o.worst.min(), dd=(eq - eq.cummax()).min(),
                sharpe=o.pnl.mean() / o.pnl.std() * np.sqrt(252))

if __name__ == "__main__":
    G, led = gold_daily()
    ports = pickle.load(open(f"{SCR}/ports.pkl", "rb"))   # v2: MR_indices (10 % vol IS) etc.
    S = pickle.load(open(f"{SCR}/sleeves_v2.pkl", "rb"))
    MR = ports["MR_indices"]
    B = S["F2_BTC_L"][["pnl", "worst"]].copy()
    wd = B.index.weekday; tgt = B.index + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")
    B = pd.DataFrame({"pnl": B.pnl.groupby(tgt).sum(), "worst": B.worst.groupby(tgt).sum().clip(upper=0)})
    print("Cartera oro reconstruida (Duka, sin freno), 2020-01 -> 2026-10:", {k: round(v, 4) for k, v in hist(G, 1).items()})
    print("   IS 2009-19:", {k: round(v, 4) for k, v in hist(G[G.index < "2020-01-01"], 1, "2009-01-01").items()})
    # correlaciones diarias y mensuales en el periodo común
    J = pd.concat({"oro": G.pnl, "MRidx": MR.pnl, "BTC": B.pnl}, axis=1)
    Jc = J[(J.index >= "2021-02-01") & (J.index < OOS_END)].fillna(0)
    print("corr diaria 2021-02+:\n", Jc.corr().round(3))
    print("corr mensual:\n", Jc.groupby([Jc.index.year, Jc.index.month]).sum().corr().round(3))
    # mezcla: paridad de riesgo con vol IS (<2020)
    volIS = {"oro": G[G.index < "2020-01-01"].pnl.std(), "MRidx": MR[MR.index < "2020-01-01"].pnl.std(),
             "BTC": B[B.index < "2020-01-01"].pnl.std()}
    def mix(names):
        w = {n: 1 / volIS[n] for n in names}; s = sum(w.values()); w = {n: v / s for n, v in w.items()}
        srcs = {"oro": G, "MRidx": MR, "BTC": B}
        idx = G.index.union(MR.index).union(B.index)
        pnl = sum(srcs[n].pnl.reindex(idx).fillna(0) * w[n] for n in names)
        worst = sum(srcs[n].worst.reindex(idx).fillna(0) * w[n] for n in names)
        df = pd.DataFrame({"pnl": pnl, "worst": np.minimum(worst, np.minimum(pnl, 0))})
        df = df[df.index >= "2021-02-01"]  # periodo común: índices FTMO desde feb-2021
        return df, w
    variants = {"oro (actual)": ["oro"], "oro+MRidx": ["oro", "MRidx"], "oro+BTC": ["oro", "BTC"], "oro+MRidx+BTC": ["oro", "MRidx", "BTC"]}
    rows = []
    for name, names in variants.items():
        df, w = mix(names)
        # escala que iguala la P(quiebra 12 m) de la cartera actual a escala 1 (mismo periodo)
        if name == "oro (actual)":
            base_df = df; target, _ = mc(df, 1.0)
            print(f"P(quiebra 12m) cartera actual, escala 1, 2021-02+: {target:.4f}")
        lo, hi = 0.2, 6.0
        for _ in range(18):
            mid = (lo + hi) / 2; p, _ = mc(df, mid, nsim=6000)
            lo, hi = (mid, hi) if p <= target else (lo, mid)
        k = lo; p, pay = mc(df, k)
        h = hist(df, k, "2021-02-01")
        rows.append(dict(cartera=name, pesos={a: round(b, 3) for a, b in w.items()}, escala=round(k, 3), sharpe=h["sharpe"],
                         mes_medio=h["mes"], mediana=h["mediana"], peor_mes=h["peor_mes"], peor_dia=h["peor_dia"], dd=h["dd"],
                         P_quiebra_12m=p, pago_mes_bruto=pay))
    R = show(rows, "{:.4f}"); R.to_csv("out_marginal.csv", index=False)
