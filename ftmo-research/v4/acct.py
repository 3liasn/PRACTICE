"""Simulador de cuenta FTMO por operación para la cartera RANGE3big+S2_A1.5 (ledger de la tanda 15).

Reglas (backtest_v3/cartera_recomendada.py): riesgo por 1R A 1,5 %, N59f/W_dst/N141 0,5 %, N30 0,25 %; tope RANGE 0,75 %;
riesgo abierto 4 %; por dirección 3 %; guard 0,8·min(margen diario, distancia a la línea) − riesgo abierto; freno S2.
Flotante (proxy, el ledger no trae el camino intradía): una operación que acaba perdiendo cuenta su pérdida final como
flotante en cada día que está abierta; una ganadora cuenta 0. Todo en fracción del balance inicial original (100k = 1).
"""
import os
import numpy as np, pandas as pd
from numba import njit

SCR = os.environ.get("SCR", "/tmp/claude-0/-home-user/ca8409e6-4186-5384-a79e-a0bc2932a16c/scratchpad")
LED = f"{SCR}/bd/backtest_v3_out_tanda15_ledger_duka.parquet"
ENG = ["ACompression", "N59f", "W_dst", "N141", "N30GapFade"]
BASE = np.array([0.015, 0.005, 0.005, 0.005, 0.0025])
ISRANGE = np.array([0, 1, 1, 1, 0], dtype=np.int64)

def broker_day(ns):
    t = pd.DatetimeIndex(pd.to_datetime(np.asarray(ns), utc=True)).tz_convert("America/New_York").tz_localize(None)
    t = t + pd.Timedelta(hours=7)
    return t.normalize().values.astype("datetime64[D]").astype(np.int64)

def load(start=None, end=None):
    d = pd.read_parquet(LED).sort_values("entry_ns").reset_index(drop=True)
    d["ed"] = broker_day(d.entry_ns); d["xd"] = broker_day(d.exit_ns)
    if start: d = d[d.ed >= np.datetime64(start, "D").astype(np.int64)]
    if end: d = d[d.ed < np.datetime64(end, "D").astype(np.int64)]
    d = d.reset_index(drop=True)
    d["wk"] = (d.ed + 3) // 7
    d["off"] = d.ed - (d.wk * 7 - 3)
    d["dur"] = (d.xd - d.ed).clip(lower=0)
    d["eng"] = d.strategy.map({e: i for i, e in enumerate(ENG)}).astype(np.int64)
    d = d.sort_values(["wk", "off", "entry_ns"]).reset_index(drop=True)
    w0 = d.wk.min(); d["w"] = d.wk - w0
    NW = int(d.w.max()) + 1
    ws = np.searchsorted(d.w.values, np.arange(NW)); we = np.searchsorted(d.w.values, np.arange(NW), side="right")
    return dict(off=d.off.values.astype(np.int64), dur=d.dur.values.astype(np.int64), R=d.r.values.astype(np.float64),
                eng=d.eng.values, side=d.side.values.astype(np.int64), ws=ws.astype(np.int64), we=we.astype(np.int64),
                NW=NW, df=d)

@njit(cache=True)
def life(seq, off, dur, R, eng, side, ws, we, base, isr, H, start_phase, m_c, m_f, pay_every, buffer, scaling,
         fee, brake, fam_cap, max_open, max_dir, guard):
    """Una ruta de H días. seq[j] = semana del histórico usada en la semana simulada j.
    start_phase: 1 = reto (paga tarifa), 3 = fondeada directamente.
    Devuelve: neto, pagos, nfees, n_fund, n_fund_lost12, days_funded, final_bal_rel, worst_day, min_eq_rel, pass_day, scaled"""
    MAXO = 128
    o_risk = np.zeros(MAXO); o_R = np.zeros(MAXO); o_exit = np.zeros(MAXO, np.int64); o_eng = np.zeros(MAXO, np.int64)
    o_side = np.zeros(MAXO, np.int64); no = 0
    init = 1.0; bal = 1.0; peak = 1.0; phase = start_phase; split = 0.8
    net = 0.0; paid = 0.0; nfees = 0; n_fund = 0; n_lost12 = 0; days_funded = 0; refunded = True; scaled = 0
    if phase == 1:
        net -= fee; nfees = 1; refunded = False
    phase_start_bal = bal; traded = 0; last_traded_day = -1
    fund_start = 0 if phase == 3 else -1
    if phase == 3: n_fund = 1
    cyc_start = 0; cyc_profit = 0.0; cyc_pay = 0; last_pay = 0
    worst_day = 0.0; min_eq = 1.0; pass_day = -1
    for d in range(H):
        wj = d // 7; dow = d % 7
        w = seq[wj]
        day_start = bal
        DAILY = 0.05 * init; LINE = init * 0.90
        mult = m_c if phase < 3 else m_f
        # nuevas operaciones del día
        for i in range(ws[w], we[w]):
            if off[i] != dow:
                continue
            e = eng[i]
            dd = (peak - bal) / init
            rp = base[e] * mult
            if brake:
                if dd >= 0.04: rp *= 0.25
                elif dd >= 0.02: rp *= 0.5
            open_r = 0.0; open_f = 0.0; open_d = 0.0
            for k in range(no):
                open_r += o_risk[k]
                if isr[o_eng[k]] == 1: open_f += o_risk[k]
                if o_side[k] == side[i]: open_d += o_risk[k]
            rp_usd = rp * init
            if isr[e] == 1: rp_usd = min(rp_usd, fam_cap * mult * init - open_f)
            rp_usd = min(rp_usd, max_open * mult * init - open_r)
            rp_usd = min(rp_usd, max_dir * mult * init - open_d)
            room = guard * min(DAILY - (day_start - bal), bal - LINE) - open_r
            rp_usd = min(rp_usd, room)
            if rp_usd <= 1e-7 or no >= MAXO:
                continue
            o_risk[no] = rp_usd; o_R[no] = R[i]; o_exit[no] = d + dur[i]; o_eng[no] = e; o_side[no] = side[i]; no += 1
            if d != last_traded_day:
                traded += 1; last_traded_day = d
        # peor equity del día (proxy) y cierres
        flo = 0.0
        for k in range(no):
            if o_R[k] < 0: flo += o_R[k] * o_risk[k]
        eq_w = bal + flo
        wd_ = (eq_w - day_start) / init
        if wd_ < worst_day: worst_day = wd_
        if eq_w / init < min_eq: min_eq = eq_w / init
        if eq_w <= day_start - DAILY or eq_w <= LINE:
            # se pierde la cuenta
            if phase == 3:
                if d - fund_start < 365: n_lost12 += 1
            if start_phase == 3 and H <= 400:
                return net, paid, nfees, n_fund, n_lost12, days_funded, (eq_w - 1.0), worst_day, min_eq, pass_day, scaled
            net -= fee; nfees += 1; refunded = False
            init = 1.0; bal = 1.0; peak = 1.0; phase = 1; split = 0.8; no = 0; traded = 0; last_traded_day = -1
            phase_start_bal = 1.0
            continue
        k = 0
        while k < no:
            if o_exit[k] <= d:
                pnl = o_R[k] * o_risk[k]; bal += pnl
                if phase == 3: cyc_profit += pnl
                no -= 1
                o_risk[k] = o_risk[no]; o_R[k] = o_R[no]; o_exit[k] = o_exit[no]; o_eng[k] = o_eng[no]; o_side[k] = o_side[no]
            else:
                k += 1
        if bal > peak: peak = bal
        if phase < 3:
            tgt = 0.10 if phase == 1 else 0.05
            if bal >= phase_start_bal + tgt * init and traded >= 4 and no == 0:
                if phase == 1:
                    phase = 2
                else:
                    phase = 3; n_fund += 1; fund_start = d; last_pay = d; cyc_start = d; cyc_profit = 0.0; cyc_pay = 0
                    if pass_day < 0: pass_day = d
                bal = init; peak = init; phase_start_bal = init; traded = 0; last_traded_day = -1
            continue
        days_funded += 1
        # retiros
        if pay_every > 0 and d - last_pay >= pay_every and no == 0:
            last_pay = d
            ex = bal - init * (1.0 + buffer)
            if ex > 0:
                paid += ex * split; net += ex * split; bal -= ex; peak = bal; cyc_pay += 1
                if not refunded:
                    net += fee; refunded = True
        # plan de escalado
        if scaling and d - cyc_start >= 120:
            if cyc_profit >= 0.10 * init and cyc_pay >= 2 and bal >= init:
                inc = 0.25  # +25 % del balance inicial original (aditivo, conservador)
                init += inc; bal += inc; peak = bal; split = 0.9; scaled += 1
            cyc_start = d; cyc_profit = 0.0; cyc_pay = 0
    return net, paid, nfees, n_fund, n_lost12, days_funded, bal - init, worst_day, min_eq, pass_day, scaled

def run_mc(T, n_paths=2000, H=364, block_weeks=8, seed=20261109, **kw):
    p = dict(start_phase=3, m_c=1.0, m_f=1.0, pay_every=0, buffer=0.0, scaling=False, fee=0.0063, brake=True,
             fam_cap=0.0075, max_open=0.04, max_dir=0.03, guard=0.8)
    p.update(kw)
    rng = np.random.default_rng(seed)
    NW = T["NW"]; nwk = H // 7 + 2; nb = nwk // block_weeks + 1
    out = np.zeros((n_paths, 11))
    for s in range(n_paths):
        starts = rng.integers(0, NW, nb)
        seq = ((starts[:, None] + np.arange(block_weeks)[None, :]) % NW).reshape(-1)[:nwk].astype(np.int64)
        out[s] = life(seq, T["off"], T["dur"], T["R"], T["eng"], T["side"], T["ws"], T["we"], BASE, ISRANGE, H,
                      p["start_phase"], p["m_c"], p["m_f"], p["pay_every"], p["buffer"], p["scaling"], p["fee"], p["brake"],
                      p["fam_cap"], p["max_open"], p["max_dir"], p["guard"])
    return pd.DataFrame(out, columns=["net", "paid", "nfees", "n_fund", "n_lost12", "days_funded", "final", "worst_day",
                                      "min_eq", "pass_day", "scaled"])

def historical(T, **kw):
    """Camino histórico real (semanas en orden), fondeada sin retiros."""
    p = dict(start_phase=3, m_c=1.0, m_f=1.0, pay_every=0, buffer=0.0, scaling=False, fee=0.0063, brake=True,
             fam_cap=0.0075, max_open=0.04, max_dir=0.03, guard=0.8)
    p.update(kw)
    seq = np.arange(T["NW"], dtype=np.int64); H = T["NW"] * 7
    return life(seq, T["off"], T["dur"], T["R"], T["eng"], T["side"], T["ws"], T["we"], BASE, ISRANGE, H,
                p["start_phase"], p["m_c"], p["m_f"], p["pay_every"], p["buffer"], p["scaling"], p["fee"], p["brake"],
                p["fam_cap"], p["max_open"], p["max_dir"], p["guard"])
