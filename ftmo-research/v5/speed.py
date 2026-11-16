"""v5 — Plan de fondeo rápido. Solo Challenge (+10 %) y Verification (+5 %), reintento al día siguiente si se rompe una regla.
Mismo motor de cuenta que v4/acct.py (reglas de cartera_recomendada.py), con palancas propias del reto (ver PREREG.md)."""
import sys, os, itertools
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "v4"))
from acct import load, BASE, ISRANGE
import numpy as np, pandas as pd
from numba import njit
from multiprocessing import Pool

DELAY_P1, DELAY_P2 = 1, 3          # días de trámite FTMO tras fase 1 y tras fase 2 (supuesto)
MIXES = {"oficial": BASE, "A_pesado": BASE * np.array([1.667, 1, 1, 1, 1]), "sin_N30": BASE * np.array([1, 1, 1, 1, 0])}
MAXF = 64

@njit(cache=True)
def to_funded(seq, off, dur, R, eng, side, ws, we, base, isr, H, m1, m2, guard, brake, freeze, micro, fail_days):
    """-> (día de fondeo o -1, nº de fallos). fail_days[j] = día del fallo j."""
    MAXO = 128
    o_risk = np.zeros(MAXO); o_R = np.zeros(MAXO); o_exit = np.zeros(MAXO, np.int64); o_eng = np.zeros(MAXO, np.int64)
    o_side = np.zeros(MAXO, np.int64); no = 0
    bal = 1.0; peak = 1.0; phase = 1; traded = 0; ltd = -1; fails = 0; frozen = False; wait = 0
    for d in range(H):
        if wait > 0:
            wait -= 1
            continue
        w = seq[d // 7]; dow = d % 7; day_start = bal
        m = m1 if phase == 1 else m2
        tgt = 0.10 if phase == 1 else 0.05
        if micro and dow < 5 and d != ltd:
            traded += 1; ltd = d                     # micro-operación de 0,01 lotes: cuenta el día
        if not frozen:
            for i in range(ws[w], we[w]):
                if off[i] != dow: continue
                e = eng[i]; rp = base[e] * m
                if rp <= 0: continue
                if brake:
                    dd = peak - bal
                    if dd >= 0.04: rp *= 0.25
                    elif dd >= 0.02: rp *= 0.5
                open_r = 0.0; open_f = 0.0; open_d = 0.0
                for k in range(no):
                    open_r += o_risk[k]
                    if isr[o_eng[k]] == 1: open_f += o_risk[k]
                    if o_side[k] == side[i]: open_d += o_risk[k]
                ru = rp
                if isr[e] == 1: ru = min(ru, 0.0075 * m - open_f)
                ru = min(ru, 0.04 * m - open_r); ru = min(ru, 0.03 * m - open_d)
                ru = min(ru, guard * min(0.05 - (day_start - bal), bal - 0.90) - open_r)
                if ru <= 1e-7 or no >= MAXO: continue
                o_risk[no] = ru; o_R[no] = R[i]; o_exit[no] = d + dur[i]; o_eng[no] = e; o_side[no] = side[i]; no += 1
                if d != ltd: traded += 1; ltd = d
        flo = 0.0
        for k in range(no):
            if o_R[k] < 0: flo += o_R[k] * o_risk[k]
        eqw = bal + flo
        if eqw <= day_start - 0.05 or eqw <= 0.90:
            if fails < fail_days.shape[0]: fail_days[fails] = d
            fails += 1; bal = 1.0; peak = 1.0; phase = 1; no = 0; traded = 0; ltd = -1; frozen = False; wait = 1
            continue
        k = 0
        while k < no:
            if o_exit[k] <= d:
                bal += o_R[k] * o_risk[k]; no -= 1
                o_risk[k] = o_risk[no]; o_R[k] = o_R[no]; o_exit[k] = o_exit[no]; o_eng[k] = o_eng[no]; o_side[k] = o_side[no]
            else: k += 1
        if bal > peak: peak = bal
        if bal >= 1.0 + tgt:
            if freeze: frozen = True
            if traded >= 4 and no == 0:
                if phase == 2:
                    return d + DELAY_P2, fails
                phase = 2; bal = 1.0; peak = 1.0; traded = 0; ltd = -1; frozen = False; wait = DELAY_P1
    return -1, fails

REG = {}
SEQS = {}
def init_reg(n=2000, H=728, seed=20261116):
    for name, (a, b) in {"actual": ("2020-01-01", None), "viejo": (None, "2020-01-01")}.items():
        T = load(a, b); REG[name] = T
        rng = np.random.default_rng(seed); nwk = H // 7 + 2; nb = nwk // 8 + 1
        S = np.zeros((n, nwk), np.int64)
        for s in range(n):
            st = rng.integers(0, T["NW"], nb)
            S[s] = ((st[:, None] + np.arange(8)[None, :]) % T["NW"]).reshape(-1)[:nwk]
        SEQS[name] = S

def sim_cfg(reg, cfg, H=728):
    T = REG[reg]; S = SEQS[reg]; n = S.shape[0]
    fd = np.full(n, -1, np.int64); nf = np.zeros(n, np.int64); FD = np.full((n, MAXF), -1, np.int64)
    base = MIXES[cfg["mix"]]
    for s in range(n):
        fd[s], nf[s] = to_funded(S[s], T["off"], T["dur"], T["R"], T["eng"], T["side"], T["ws"], T["we"], base, ISRANGE, H,
                                 cfg["m1"], cfg["m2"], cfg["guard"], cfg["brake"], cfg["freeze"], cfg["micro"], FD[s])
    return fd, nf, FD

def summ(fd, fees, H=728):
    ok = fd >= 0; dd = np.where(ok, fd, H)
    return dict(dias_media=dd.mean(), dias_mediana=np.median(dd), dias_p80=np.percentile(dd, 80), dias_p95=np.percentile(dd, 95),
                P30=(ok & (fd <= 30)).mean(), P60=(ok & (fd <= 60)).mean(), P90=(ok & (fd <= 90)).mean(),
                P_24m=ok.mean(), retos=fees.mean())

def _work(cfg):
    r = dict(cfg)
    for reg in ("actual", "viejo"):
        fd, nf, _ = sim_cfg(reg, cfg)
        r.update({f"{k}_{reg}": v for k, v in summ(fd, nf + 1).items()})
    return r

GRID = [dict(m1=m1, m2=m2, guard=g, brake=b, freeze=f, micro=mi, mix=mx)
        for m1, m2, g, b, f, mi, mx in itertools.product((1, 2, 3, 4, 5, 6, 8), (1, 1.5, 2, 3, 4), (0.8, 0.95),
                                                         (True, False), (False, True), (False, True), tuple(MIXES))]

if __name__ == "__main__":
    init_reg()
    with Pool(4, initializer=init_reg) as p:
        rows = p.map(_work, GRID, chunksize=8)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_speed.csv"), index=False)
    print("filas", len(R))
