"""Monitor de salud del edge (diseño estadístico, no ajustado a datos): por familia (A, RANGE, N30) se guarda la R en
sombra de TODAS sus señales; si la media de las últimas W señales < 0 la familia se pausa (o se reduce a la mitad).
W por potencia: con el edge OOS, P(media<0) ≈ 4-9 %; con edge 0, ≈ 50 %. A: 30, RANGE: 300, N30: 300.
Escenarios: régimen actual, régimen viejo y 'el edge muere' (calentamiento y 6 meses en régimen actual, después viejo)."""
import sys; sys.path.insert(0, ".")
from acct import *
from numba import njit
FAM = np.array([0, 1, 1, 1, 2], dtype=np.int64)          # A, RANGE x3, N30
WIN = np.array([30, 300, 300], dtype=np.int64)

@njit(cache=True)
def life_m(seqA, seqB, switch_wk, warm_wk, oA, dA, RA, eA, sA, wsA, weA, oB, dB, RB, eB, sB, wsB, weB,
           base, isr, fam, win, H, mon_mode, pay_every, m_c, start_phase, fee):
    """Como acct.life (fondeada o ciclo con reto), con monitor. Semanas < switch_wk usan el régimen A; después el B.
    Las primeras warm_wk semanas solo llenan el monitor (no hay cuenta)."""
    MAXO = 128; BUF = 400
    buf = np.zeros((3, BUF)); nb = np.zeros(3, np.int64); pos = np.zeros(3, np.int64)
    o_risk = np.zeros(MAXO); o_R = np.zeros(MAXO); o_exit = np.zeros(MAXO, np.int64); o_eng = np.zeros(MAXO, np.int64)
    o_side = np.zeros(MAXO, np.int64); no = 0
    init = 1.0; bal = 1.0; peak = 1.0; phase = start_phase; split = 0.8; net = 0.0; nfees = 0; refunded = True
    if phase == 1:
        net -= fee; nfees = 1; refunded = False
    traded = 0; ltd = -1; last_pay = 0; lost = 0; paused_days = 0.0; fund_start = 0
    T0 = warm_wk * 7
    for dd_ in range(T0 + H):
        wj = dd_ // 7; dow = dd_ % 7
        reg = 0 if wj < switch_wk else 1
        w = seqA[wj] if reg == 0 else seqB[wj]
        ws = wsA if reg == 0 else wsB; we = weA if reg == 0 else weB
        off = oA if reg == 0 else oB; dur = dA if reg == 0 else dB; R = RA if reg == 0 else RB
        eng = eA if reg == 0 else eB; side = sA if reg == 0 else sB
        acct_on = dd_ >= T0
        d = dd_ - T0
        day_start = bal; DAILY = 0.05 * init; LINE = 0.9 * init
        mult = m_c if phase < 3 else 1.0
        for i in range(ws[w], we[w]):
            if off[i] != dow: continue
            e = eng[i]; f = fam[e]
            # factor del monitor (con la historia ANTES de esta señal)
            fac = 1.0
            if mon_mode > 0 and nb[f] >= win[f]:
                s = 0.0
                for j in range(win[f]):
                    s += buf[f, (pos[f] - 1 - j) % BUF]
                if s < 0: fac = 0.0 if mon_mode == 1 else 0.5
            # registra la R en sombra
            buf[f, pos[f] % BUF] = R[i]; pos[f] += 1; nb[f] += 1
            if not acct_on: continue
            if fac < 1.0 and phase == 3: paused_days += 1.0 / 60.0
            dd = (peak - bal) / init
            rp = base[e] * mult * fac
            if dd >= 0.04: rp *= 0.25
            elif dd >= 0.02: rp *= 0.5
            open_r = 0.0; open_f = 0.0; open_d = 0.0
            for k in range(no):
                open_r += o_risk[k]
                if isr[o_eng[k]] == 1: open_f += o_risk[k]
                if o_side[k] == side[i]: open_d += o_risk[k]
            ru = rp * init
            if isr[e] == 1: ru = min(ru, 0.0075 * mult * init - open_f)
            ru = min(ru, 0.04 * mult * init - open_r); ru = min(ru, 0.03 * mult * init - open_d)
            ru = min(ru, 0.8 * min(DAILY - (day_start - bal), bal - LINE) - open_r)
            if ru <= 1e-7 or no >= MAXO: continue
            o_risk[no] = ru; o_R[no] = R[i]; o_exit[no] = d + dur[i]; o_eng[no] = e; o_side[no] = side[i]; no += 1
            if d != ltd: traded += 1; ltd = d
        if not acct_on: continue
        flo = 0.0
        for k in range(no):
            if o_R[k] < 0: flo += o_R[k] * o_risk[k]
        eqw = bal + flo
        if eqw <= day_start - DAILY or eqw <= LINE:
            if phase == 3: lost += 1
            if start_phase == 3:
                return net, lost, bal - init + flo, paused_days, nfees
            net -= fee; nfees += 1; refunded = False; init = 1.0; bal = 1.0; peak = 1.0; phase = 1; split = 0.8
            no = 0; traded = 0; ltd = -1
            continue
        k = 0
        while k < no:
            if o_exit[k] <= d:
                bal += o_R[k] * o_risk[k]; no -= 1
                o_risk[k] = o_risk[no]; o_R[k] = o_R[no]; o_exit[k] = o_exit[no]; o_eng[k] = o_eng[no]; o_side[k] = o_side[no]
            else: k += 1
        if bal > peak: peak = bal
        if phase < 3:
            if bal >= init + (0.10 if phase == 1 else 0.05) * init and traded >= 4 and no == 0:
                phase = 3 if phase == 2 else 2
                bal = init; peak = init; traded = 0; ltd = -1
                if phase == 3: last_pay = d; fund_start = d
            continue
        if pay_every > 0 and d - last_pay >= pay_every and no == 0:
            last_pay = d; ex = bal - init
            if ex > 0:
                net += ex * split; bal -= ex; peak = bal
                if not refunded: net += fee; refunded = True
    return net, lost, bal - init, paused_days, nfees

def scen(TA, TB, switch_after_wk, H, mon_mode, n=2000, warm_wk=104, pay_every=0, m_c=1.0, start_phase=3, seed=3):
    rng = np.random.default_rng(seed); NWk = warm_wk + H // 7 + 2; out = np.zeros((n, 5))
    def seq(T):
        nb_ = NWk // 8 + 1; st = rng.integers(0, T["NW"], nb_)
        return ((st[:, None] + np.arange(8)[None, :]) % T["NW"]).reshape(-1)[:NWk].astype(np.int64)
    for s in range(n):
        sa, sb = seq(TA), seq(TB)
        out[s] = life_m(sa, sb, warm_wk + switch_after_wk, warm_wk, TA["off"], TA["dur"], TA["R"], TA["eng"], TA["side"],
                        TA["ws"], TA["we"], TB["off"], TB["dur"], TB["R"], TB["eng"], TB["side"], TB["ws"], TB["we"],
                        BASE, ISRANGE, FAM, WIN, H, mon_mode, pay_every, m_c, start_phase, 0.0063)
    return pd.DataFrame(out, columns=["net", "lost", "final", "paused", "nfees"])

if __name__ == "__main__":
    NEW = load("2020-01-01", None); OLD = load(None, "2020-01-01")
    rows = []
    S = {"actual": (NEW, NEW, 10**6), "viejo": (OLD, OLD, 0), "muere_a_6m": (NEW, OLD, 26)}
    for sname, (A, B, sw) in S.items():
        for mm, mname in [(0, "sin monitor"), (1, "pausa"), (2, "mitad")]:
            f = scen(A, B, sw, 364, mm)                                   # fondeada 12 m sin retiros
            g = scen(A, B, sw, 728, mm, pay_every=30, m_c=2.5, start_phase=1, seed=4)   # ciclo 24 m, política propuesta
            rows.append(dict(escenario=sname, monitor=mname, P_pierde_fondeada_12m=(f.lost > 0).mean(),
                             pct_mes_12m=100 * f.final.mean() / 12, neto_mes_ciclo24=100 * g.net.mean() / 24,
                             neto_p10=100 * g.net.quantile(0.1) / 24, retos=g.nfees.mean()))
    R = pd.DataFrame(rows); R.to_csv("out_monitor.csv", index=False)
    pd.set_option("display.width", 200); print(R.round(3).to_string(index=False))
