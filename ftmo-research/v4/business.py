"""Capa de negocio FTMO (pre-registro v4): retiros × modo reto × modo fondeada, con escalado. 24 meses por plaza de 100k."""
import sys; sys.path.insert(0, ".")
from acct import *
REG = {"actual_2020+": load("2020-01-01", None), "viejo_2009-19": load(None, "2020-01-01")}
PAY = {"30d_todo": (30, 0.0), "14d_todo": (14, 0.0), "30d_colchon2": (30, 0.02), "30d_colchon4": (30, 0.04)}
rows = []
for reg, T in REG.items():
    for pname, (pe, buf) in PAY.items():
        for mc in (1.0, 1.5, 2.0, 2.5, 3.0):
            for mf in (1.0, 1.25, 1.5):
                r = run_mc(T, n_paths=2000, H=728, start_phase=1, m_c=mc, m_f=mf, pay_every=pe, buffer=buf, scaling=True, seed=7)
                nf = r.n_fund.sum()
                rows.append(dict(regimen=reg, retiro=pname, m_reto=mc, m_fond=mf, neto_mes=100 * r.net.mean() / 24,
                                 neto_p10=100 * r.net.quantile(0.1) / 24, neto_p50=100 * r.net.median() / 24,
                                 P_neto_pos=(r.net > 0).mean(), retos=r.nfees.mean(), meses_fondeado=r.days_funded.mean() / 30.44,
                                 P_pierde_fondeada_12m=(r.n_lost12.sum() / nf) if nf else np.nan,
                                 dias_a_fondeo_med=r.pass_day[r.pass_day >= 0].median(), P_escala=(r.scaled > 0).mean()))
R = pd.DataFrame(rows); R.to_csv("out_business.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
A = R[R.regimen == "actual_2020+"].set_index(["retiro", "m_reto", "m_fond"])
V = R[R.regimen == "viejo_2009-19"].set_index(["retiro", "m_reto", "m_fond"])
J = A[["neto_mes", "neto_p10", "P_neto_pos", "retos", "meses_fondeado", "P_pierde_fondeada_12m", "dias_a_fondeo_med", "P_escala"]].join(
    V[["neto_mes", "P_pierde_fondeada_12m"]].rename(columns=lambda c: c + "_viejo"))
base = J.loc[("30d_todo", 1.0, 1.0)]
print("BASE (retiro mensual, m=1):\n", base.round(3).to_string())
ok = J[(J.P_pierde_fondeada_12m <= 0.05) & (J.neto_mes_viejo >= base.neto_mes_viejo)]
print("\nTop 12 que cumplen la regla:\n", ok.sort_values("neto_mes", ascending=False).head(12).round(3).to_string())
print("\nTop 8 sin restricciones (referencia):\n", J.sort_values("neto_mes", ascending=False).head(8).round(3).to_string())
