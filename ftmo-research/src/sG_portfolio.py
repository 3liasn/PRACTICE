"""Cartera (pesos fijados SOLO con IS) + simulador de reglas FTMO 2-Step por bootstrap de bloques."""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd, numba as nb
D = pd.read_pickle("out/sleeves.pkl"); S, FAM = D["S"], D["FAM"]
cal = pd.bdate_range("2005-01-03", "2020-05-13")
P = pd.DataFrame({k: v.p.reindex(cal).fillna(0) for k, v in S.items()}); M = pd.DataFrame({k: v.mae.reindex(cal).fillna(0) for k, v in S.items()})
IS = slice("2005", "2012"); OOS = slice("2013", "2020")
def sh(x): return x.mean() / x.std() * np.sqrt(252)
def mdd(x): e = x.cumsum(); return (e - e.cummax()).min()
is_sh = P[IS].apply(sh)
def portfolio(cols, label):
    fams = {}
    for c in cols: fams.setdefault(FAM[c], []).append(c)
    w = pd.Series(0.0, index=cols)
    for f, cs in fams.items():
        for c in cs: w[c] = 1 / P[IS][c].std() / len(cs) / len(fams)
    p = (P[cols] * w).sum(1); m = (M[cols] * w).sum(1)
    k = 0.10 / (p[IS].std() * np.sqrt(252))        # normaliza a 10% de vol anual en IS
    p, m = p * k, m * k
    print(f"\n== {label}: {len(cols)} mangas, {len(fams)} familias")
    for lab, sl in [("IS 2005-12", IS), ("OOS 2013-20", OOS)]:
        x = p[sl]; mo = x.groupby([x.index.year, x.index.month]).sum()
        print(f"  {lab}: Sharpe {sh(x):.2f} | ret anual {x.mean()*252:.1%} | vol {x.std()*np.sqrt(252):.1%} | maxDD {mdd(x):.1%} | mes medio {mo.mean():.2%} | meses>0 {(mo>0).mean():.0%} | peor mes {mo.min():.1%} | peor dia {x.min():.1%}")
    return p, m
sel = [c for c in P.columns if is_sh[c] >= 0.5]
pA, mA = portfolio(sel, "A) Seleccion por IS>=0.5 (regla honesta)")
mr = ["MR_L SPX500", "MR_L NAS100", "MR_L US2000"]
pB, mB = portfolio(mr, "B) Solo reversion larga indices USA")
best = [c for c in P.columns if sh(P[OOS][c]) >= 0.5 and is_sh[c] >= 0.5]
pC, mC = portfolio(best, "C) COTA OPTIMISTA: elegidas mirando tambien el OOS (sesgo de seleccion)")
print("   mangas C:", best)
pd.to_pickle({"A": (pA, mA), "B": (pB, mB), "C": (pC, mC)}, "out/portfolios.pkl")

@nb.njit(cache=True)
def ftmo(p, m, nsim, block, seed, dstop, months, keep_buffer):
    """p,m: retornos diarios y peor flotante (fraccion del balance inicial). Devuelve por simulacion:
    [pasa_fase1, pasa_fase2, dias_hasta_fondeo, meses_vivo, pago_total, quiebra_mes(0 si no)]"""
    np.random.seed(seed); n = len(p); out = np.zeros((nsim, 6))
    for s in range(nsim):
        i = np.random.randint(n); left = 0; days = 0; ok = True
        # --- fases de evaluacion
        for phase in range(2):
            tgt = 0.10 if phase == 0 else 0.05
            bal = 0.0; td = 0; passed = False
            for d in range(750):
                if left == 0: i = np.random.randint(n); left = block
                r = p[i]; w = m[i]; i = (i + 1) % n; left -= 1; days += 1
                if w <= -dstop: r = -dstop; w = -dstop          # corte diario de cartera
                if w <= -0.05 or bal + w <= -0.10: break         # perdida diaria / perdida maxima
                bal += r
                if r != 0: td += 1
                if bal >= tgt and td >= 4: passed = True; break
            if not passed: ok = False; break
            out[s, phase] = 1
        if not ok: continue
        out[s, 2] = days
        # --- cuenta fondeada
        bal = 0.0; paid = 0.0; alive = True; mo = 0
        for mo in range(months):
            for d in range(21):
                if left == 0: i = np.random.randint(n); left = block
                r = p[i]; w = m[i]; i = (i + 1) % n; left -= 1
                if w <= -dstop: r = -dstop; w = -dstop
                if w <= -0.05 or bal + w <= -0.10: alive = False; break
                bal += r
            if not alive: break
            if keep_buffer:
                if bal > 0.05: paid += bal - 0.05; bal = 0.05
            else:
                if bal > 0: paid += bal; bal = 0.0
        out[s, 3] = mo + 1 if alive else mo
        out[s, 4] = paid; out[s, 5] = 0 if alive else mo + 1
    return out
def table(p, m, label, months=24, nsim=20000):
    x = p[OOS].values; w = m[OOS].values
    base_vol = x.std() * np.sqrt(252); base_mu = x.mean() * 252
    rows = []
    for tv in [0.05, 0.10, 0.15, 0.20, 0.30, 0.45, 0.60]:
        k = tv / base_vol
        for kb in (0, 1):
            o = ftmo(x * k, w * k, nsim, 10, 7, 0.04, months, kb)
            f = o[:, 1] == 1
            rows.append(dict(vol_obj=f"{tv:.0%}", ret_mes_teorico=base_mu * k / 12, colchon=kb, pasa_eval=f.mean(), dias_eval=np.median(o[f, 2]) if f.any() else np.nan,
                             quiebra_12m=((o[f, 5] > 0) & (o[f, 5] <= 12)).mean() if f.any() else np.nan, quiebra_24m=(o[f, 5] > 0).mean() if f.any() else np.nan,
                             pago_mes_medio=(o[f, 4] / months).mean() if f.any() else np.nan))
    df = pd.DataFrame(rows)
    print(f"\n--- Simulacion FTMO 2-Step ({label}; bootstrap de dias OOS 2013-2020; corte diario -4%; {months} meses fondeado) ---")
    with pd.option_context("display.width", 220, "display.float_format", "{:.3f}".format): print(df.to_string(index=False))
if __name__ == "__main__":
    table(pA, mA, "cartera A")
    table(pB, mB, "cartera B: reversion indices USA")
    table(pC, mC, "cartera C: cota optimista")
