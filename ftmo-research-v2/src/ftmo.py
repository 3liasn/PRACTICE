"""Simulador FTMO 2-Step sobre series diarias (día de Praga) con pnl y peor flotante intradía.
Reglas: fase 1 +10 %, fase 2 +5 %, mínimo 4 días operados por fase, sin límite de tiempo;
pérdida diaria: el equity no puede bajar 5 % del balance inicial por debajo del balance de inicio del día;
pérdida máxima: equity >= 90 % del inicial (estática). Fondeada: retiro del 80 % del beneficio a fin de mes.
Unidades: fracción del balance inicial."""
import numpy as np, pandas as pd
def run(pnl, low, act, month_end, k, buffer=0.0, max_days=None, split=0.8):
    """Devuelve (resultado, dias_f1, dias_f2, pagos (lista por mes fondeado), meses_fondeado, rend_mensual_fondeado)."""
    n = len(pnl); i = 0
    for target in (0.10, 0.05):
        eq = 1.0; days = 0; start = i
        while True:
            if i >= n or (max_days and i - start > max_days): return ("sin_datos", None, None, [], 0, [])
            if eq + k * low[i] < eq - 0.05 + 1e-12 or eq + k * low[i] < 0.90: return ("falla_fase%d" % (1 if target == 0.10 else 2), i, None, [], 0, [])
            eq += k * pnl[i]; days += act[i]; i += 1
            if eq >= 1 + target and days >= 4: break
        if target == 0.10: d1 = i
    eq = 1.0; pays = []; rets = []; m0 = eq
    while i < n:
        if eq + k * low[i] < eq - 0.05 + 1e-12 or eq + k * low[i] < 0.90:
            rets.append(eq + k * low[i] - m0); return ("perdida_fondeada", d1, i, pays, len(pays), rets)
        eq += k * pnl[i]
        if month_end[i]:
            rets.append(eq - m0)
            if eq > 1 + buffer:
                pays.append(split * (eq - 1 - buffer)); eq = 1 + buffer
            else: pays.append(0.0)
            m0 = eq
        i += 1
    return ("vive", d1, i, pays, len(pays), rets)
def evaluate(d, k, starts=None, buffer=0.0, horizon_m=12, fee=0.0054, boot=0, block=20, seed=0):
    """Simula cuentas que empiezan en cada inicio de mes (o bootstrap por bloques). horizon_m: meses de calendario
    desde que se compra el reto. Devuelve métricas de economía por reto comprado."""
    pnl = d["pnl"].values; low = d["low"].values; act = d["act"].values.astype(int)
    idx = d.index; me = np.r_[idx.month[1:] != idx.month[:-1], True]
    H = int(horizon_m * 21)
    res = []
    if boot:
        rng = np.random.default_rng(seed)
        for b in range(boot):
            nb = H // block + 1; st = rng.integers(0, len(pnl) - block, nb)
            ii = np.concatenate([np.arange(s, s + block) for s in st])[:H]
            mme = np.zeros(H, bool); mme[20::21] = True
            res.append(run(pnl[ii], low[ii], act[ii], mme, k, buffer))
    else:
        if starts is None: starts = np.where(np.r_[True, idx.month[1:] != idx.month[:-1]])[0]
        for s in starts:
            e = min(len(pnl), s + H)
            if e - s < H * 0.9: continue
            res.append(run(pnl[s:e], low[s:e], act[s:e], me[s:e], k, buffer))
    out = pd.Series([r[0] for r in res]).value_counts(normalize=True).to_dict()
    pays = np.array([sum(r[3]) for r in res])
    fund_m = np.array([r[4] for r in res])
    allrets = np.concatenate([r[5] for r in res if r[5]]) if any(r[5] for r in res) else np.array([0.0])
    passed = np.mean([r[0] in ("vive", "perdida_fondeada") for r in res])
    return dict(k=k, n=len(res), pasa=passed * 100, pierde_fondeada=out.get("perdida_fondeada", 0) * 100,
                vive=out.get("vive", 0) * 100, mes_fondeada=allrets.mean() * 100,
                pago_total=pays.mean() * 100, pago_mes=(pays.mean() - fee * 0.0) / horizon_m * 100,
                neto_mes=(pays.mean() + passed * fee - fee * (1 + 0)) / horizon_m * 100)
