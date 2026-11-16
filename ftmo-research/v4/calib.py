import sys; sys.path.insert(0, ".")
from acct import *
for lab, (a, b) in {"OOS 2020+": ("2020-01-01", None), "IS 2009-19": (None, "2020-01-01")}.items():
    T = load(a, b)
    h = historical(T)
    months = T["NW"] * 7 / 30.44
    print(f"{lab}: semanas {T['NW']} | histórico fondeada sin retiros: %/mes {100*h[6]/months:.3f} peor día {100*h[7]:.2f} % min eq {100*(h[8]-1):.2f} % fondos perdidos {int(h[4])}")
    mc = run_mc(T, n_paths=2000)
    print(f"   MC 52 sem: P(breach) {100*(mc.n_lost12>0).mean():.2f} %  %/mes medio {100*mc.final.mean()/12:.3f} p50 {100*mc.final.median()/12:.3f}  peor día p1 {100*mc.worst_day.quantile(0.01):.2f}")
    mcc = run_mc(T, n_paths=2000, start_phase=1, fee=0.0, H=364)
    print(f"   reto (mismo riesgo): P(pasar en 1 año) {100*(mcc.pass_day>=0).mean():.1f} %  días a pasar mediana {mcc.pass_day[mcc.pass_day>=0].median():.0f}")
