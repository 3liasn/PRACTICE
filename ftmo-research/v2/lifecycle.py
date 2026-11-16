"""Frontera FTMO con lo mejor encontrado: retorno mensual vs. riesgo de perder la cuenta, y economía del ciclo
completo (reto -> verificación -> fondeada -> pagos; si se pierde, se paga otro reto). Solo días OOS 2021-2026."""
import sys, pickle; sys.path.insert(0, '.')
from common2 import *
from numba import njit
S = {**pickle.load(open(f"{SCR}/sleeves_v2.pkl", "rb")), **pickle.load(open(f"{SCR}/sleeves_r2.pkl", "rb"))}

def weekdays(d):
    """fines de semana (BTC) se suman al lunes siguiente."""
    d = d.copy(); wd = d.index.weekday
    tgt = d.index + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")
    g = d.groupby(tgt)
    return pd.DataFrame({"pnl": g.pnl.sum(), "worst": g.worst.sum().clip(upper=0)})

def build(names, target=0.10, fit="IS"):
    P = pd.concat({k: S[k]["pnl"] for k in names}, axis=1).fillna(0.0)
    W = pd.concat({k: S[k]["worst"] for k in names}, axis=1).reindex(P.index).fillna(0.0)
    P = P[P.index < OOS_END]; W = W.loc[P.index]
    base = P[P.index < IS_END] if fit == "IS" else P[P.index >= IS_END]
    base = base.loc[:, base.std() > 0]
    vol = base.std() * np.sqrt(252); w = (1 / vol) / (1 / vol).sum(); w = w.reindex(P.columns).fillna(0)
    port = (P * w).sum(axis=1); k = target / (port.loc[base.index].std() * np.sqrt(252)); w = w * k
    d = pd.DataFrame({"pnl": (P * w).sum(axis=1), "worst": (W * w).sum(axis=1)})
    d["worst"] = np.minimum(d.worst, np.minimum(d.pnl, 0))
    return weekdays(d)

@njit(cache=True)
def sim(pnl, worst, idx, k, fee, split, months, mdays, phase_start):
    """Una ruta. phase_start: 0 = reto. Devuelve (neto, pagos, n_retos, meses_fondeado, perdio_fondeada)."""
    phase = phase_start; bal = 0.0; traded = 0; net = -fee if phase == 0 else 0.0
    paid = 0.0; nfee = 1 if phase == 0 else 0; fmonths = 0; lost_funded = 0; refunded = phase == 2
    day_in_month = 0
    T = months * mdays
    for t in range(T):
        i = idx[t]
        p = pnl[i] * k; wv = worst[i] * k
        if phase == 2:
            day_in_month += 1
        if wv <= -0.05 or bal + wv <= -0.10:
            if phase == 2: lost_funded += 1
            phase = 0; bal = 0.0; traded = 0; net -= fee; nfee += 1; refunded = False; day_in_month = 0
            continue
        bal += p
        if p != 0: traded += 1
        if phase == 0 and bal >= 0.10 and traded >= 4:
            phase = 1; bal = 0.0; traded = 0
        elif phase == 1 and bal >= 0.05 and traded >= 4:
            phase = 2; bal = 0.0; traded = 0; day_in_month = 0
        elif phase == 2 and day_in_month >= mdays:
            fmonths += 1; day_in_month = 0
            if bal > 0:
                paid += bal * split; net += bal * split
                if not refunded: net += fee; refunded = True
                bal = 0.0
    return net, paid, nfee, fmonths, lost_funded

@njit(cache=True)
def funded_only(pnl, worst, idx, k, months, mdays, keep):
    """Cuenta fondeada desde cero: ¿se pierde en 'months'? media mensual bruta retirada."""
    bal = 0.0; paid = 0.0
    for t in range(months * mdays):
        i = idx[t]; p = pnl[i] * k; wv = worst[i] * k
        if wv <= -0.05 or bal + wv <= -0.10:
            return 1, paid, t
        bal += p
        if (t + 1) % mdays == 0 and bal > keep:
            paid += bal - keep; bal = keep
    return 0, paid, months * mdays

def frontier(d, label, ks, nsim=20000, months=12, mdays=21, block=20, seed=7):
    o = d[d.index >= IS_END]; pnl = o.pnl.values; worst = o.worst.values; n = len(pnl)
    rng = np.random.default_rng(seed)
    rows = []
    base_m = o.pnl.groupby([o.index.year, o.index.month]).sum()
    for k in ks:
        lost = np.zeros(nsim); paid = np.zeros(nsim); net = np.zeros(nsim); nfee = np.zeros(nsim); fm = np.zeros(nsim)
        for s in range(nsim):
            idx = block_bootstrap(n, months * mdays + block, block, rng)
            l, p, _ = funded_only(pnl, worst, idx, k, months, mdays, 0.0)
            lost[s] = l; paid[s] = p
            idx2 = block_bootstrap(n, 24 * mdays + block, block, rng)
            nt, pd_, nf, fmm, lf = sim(pnl, worst, idx2, k, 0.0063, 0.8, 24, mdays, 0)
            net[s] = nt; nfee[s] = nf; fm[s] = fmm
        # camino histórico real OOS con esa escala
        x = o.pnl * k; xm = x.groupby([x.index.year, x.index.month]).sum(); eq = x.cumsum()
        rows.append(dict(cartera=label, escala=k, mes_medio_hist=xm.mean(), peor_mes_hist=xm.min(),
                         maxdd_hist=(eq - eq.cummax()).min(), peor_dia_hist=(o.worst * k).min(),
                         P_perder_fondeada_12m=lost.mean(), pago_bruto_mes_fondeada=paid.mean() / months,
                         neto_mes_ciclo24m=net.mean() / 24, neto_mediana_24m=np.median(net) / 24,
                         P_neto_pos_24m=(net > 0).mean(), retos_pagados=nfee.mean(), meses_fondeado=fm.mean()))
    return rows

if __name__ == "__main__":
    V1 = pickle.load(open(f"{SCR}/sleeves_v2.pkl", "rb"))
    PRE = [k for k in V1 if stats(split(V1[k])[0]).get("sharpe", -9) > 0.5 and len(split(V1[k])[1]) > 100]
    print("PRE (filtro pre-registrado):", PRE)
    MR = ['F3_IBS_US500', 'F3_RSI2_US500', 'F3_IBS_US100', 'F3_RSI2_US100', 'F3_IBS_US30', 'F3_RSI2_US30',
          'F3_RSI2_JP225', 'F3_IBS_JP225']
    allk = [k for k in S if len(split(S[k])[1]) > 100]
    OPT = [k for k in allk if stats(split(S[k])[1]).get("sharpe", -9) > 0.5 and stats(split(S[k])[0]).get("sharpe", 0) > 0]
    print("OPT (elegidas mirando el OOS):", OPT)
    ports = {"PRE": build(PRE), "MR_indices": build(MR), "OPT_cota": build(OPT, fit="OOS")}
    pickle.dump(ports, open(f"{SCR}/ports.pkl", "wb"))
    for name, d in ports.items():
        print(name, stats(split(d)[0], "IS"), "\n   ", stats(split(d)[1], "OOS"))
    rows = []
    for name, d in ports.items():
        rows += frontier(d, name, [0.5, 1, 1.5, 2, 3, 4, 6])
    R = show(rows, "{:.4f}")
    R.to_csv("out_frontier.csv", index=False)
