"""Escalera de retos en paralelo: varias cuentas a la vez con las mismas señales (misma dirección, nunca cobertura entre cuentas)
y multiplicadores distintos. Métrica: días hasta la PRIMERA fondeada; tarifas totales hasta entonces (todas las cuentas)."""
import sys; sys.path.insert(0, ".")
import speed as S
import numpy as np, pandas as pd
S.init_reg(n=3000)
def C(m1, m2, g=0.95, b=False): return dict(m1=m1, m2=m2, guard=g, brake=b, freeze=True, micro=True, mix="oficial")
SINGLES = {"mejor (2/1,5)": C(2, 1.5), "elegida regla (3/2 freno)": C(3, 2, 0.95, True), "rápida (4/3 freno)": C(4, 3, 0.95, True),
           "agresiva (6/3)": C(6, 3), "segura (2/1 g0,8)": C(2, 1, 0.8), "oficial (1/1)": C(1, 1, 0.8, True), "x1,5": C(1.5, 1, 0.8, True)}
LADDERS = {"control: 2 iguales (2/1,5)": ["mejor (2/1,5)", "mejor (2/1,5)"],
           "rápida + mejor": ["rápida (4/3 freno)", "mejor (2/1,5)"],
           "agresiva + mejor": ["agresiva (6/3)", "mejor (2/1,5)"],
           "agresiva + segura": ["agresiva (6/3)", "segura (2/1 g0,8)"],
           "mejor + oficial": ["mejor (2/1,5)", "oficial (1/1)"],
           "3: agresiva + mejor + oficial": ["agresiva (6/3)", "mejor (2/1,5)", "oficial (1/1)"],
           "3: rápida + mejor + x1,5": ["rápida (4/3 freno)", "mejor (2/1,5)", "x1,5"]}
H = 728
rows = []
for reg in ("actual", "viejo"):
    res = {k: S.sim_cfg(reg, c) for k, c in SINGLES.items()}
    for k, (fd, nf, FD) in res.items():
        rows.append(dict(regimen=reg, plan=k, cuentas=1, **S.summ(fd, nf + 1)))
    for lname, members in LADDERS.items():
        n = len(res[members[0]][0])
        first = np.full(n, H, np.int64); fees = np.zeros(n)
        fds = np.array([res[m][0] for m in members]); fds_ = np.where(fds >= 0, fds, H)
        first = fds_.min(axis=0)
        for m in members:
            FD = res[m][2]
            fees += 1 + ((FD >= 0) & (FD < first[:, None])).sum(axis=1)
        fd_out = np.where(first < H, first, -1)
        r = dict(regimen=reg, plan=lname, cuentas=len(members), **S.summ(fd_out, fees))
        # bonus: ¿la segunda cuenta también se fondea en los 60 días siguientes?
        srt = np.sort(fds_, axis=0)
        r["P_2a_fondeada_+60d"] = ((srt[1] < H) & (srt[1] - srt[0] <= 60)).mean()
        rows.append(r)
R = pd.DataFrame(rows); R.to_csv("out_ladder.csv", index=False)
pd.set_option("display.width", 250)
c = ["plan", "cuentas", "dias_media", "dias_mediana", "dias_p80", "P30", "P60", "P90", "P_24m", "retos", "P_2a_fondeada_+60d"]
for reg in ("actual", "viejo"):
    print(f"\n=== régimen {reg}"); print(R[R.regimen == reg][c].round(3).to_string(index=False))
