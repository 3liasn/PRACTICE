"""¿Qué Sharpe haría falta? Estrategia hipotética con media 5 %/mes, colas gordas (t de Student, 4 g.l.)."""
import sys; sys.path.insert(0, '.')
from common2 import *
from lifecycle import funded_only, sim
rng = np.random.default_rng(11)
rows = []
for S_ in (1.0, 1.5, 2.0, 3.0, 4.0, 5.0):
    mu = 0.05 / 21; sd = 0.05 * 12 / S_ / np.sqrt(252)
    n = 400000
    t = rng.standard_t(4, n) / np.sqrt(4 / 2)          # var 1
    pnl = mu + sd * t
    worst = np.minimum(pnl, 0) - np.abs(rng.normal(0, 0.3 * sd, n))  # hundimiento intradía extra
    lost = []; paid = []; passed = []
    for s in range(20000):
        idx = rng.integers(0, n, 12 * 21)
        l, p, _ = funded_only(pnl, worst, idx, 1.0, 12, 21, 0.0); lost.append(l); paid.append(p)
        idx2 = rng.integers(0, n, 60)
        r1 = ftmo_path(pnl[idx2], worst[idx2], target=0.10)
        ok = False
        if r1[0] == "pass":
            idx3 = rng.integers(0, n, 60)
            ok = ftmo_path(pnl[idx3], worst[idx3], target=0.05)[0] == "pass"
        passed.append(ok)
    rows.append(dict(sharpe=S_, vol_anual=sd * np.sqrt(252), P_perder_12m=np.mean(lost), pago_bruto_mes=np.mean(paid) / 12,
                     P_pasar_ambas_fases_60d=np.mean(passed)))
show(rows).to_csv("out_required.csv", index=False)
