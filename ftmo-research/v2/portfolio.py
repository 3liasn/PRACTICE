"""Cartera pre-registrada (Sharpe IS > 0,5, paridad de riesgo con vol IS, 10 % vol anual IS) + cartera post-hoc."""
import sys, pickle; sys.path.insert(0, '.')
from common2 import *
S = pickle.load(open(f"{SCR}/sleeves_v2.pkl", "rb"))

def build(names, label, target=0.10):
    P = pd.concat({k: S[k]["pnl"] for k in names}, axis=1).fillna(0.0)
    W = pd.concat({k: S[k]["worst"] for k in names}, axis=1).fillna(0.0)
    P = P[P.index < OOS_END]; W = W.reindex(P.index).fillna(0.0)
    isP = P[P.index < IS_END]
    vol = isP.std() * np.sqrt(252)
    w = (1 / vol) / (1 / vol).sum()
    port = (P * w).sum(axis=1)
    k = target / (port[port.index < IS_END].std() * np.sqrt(252))
    pw = w * k
    pnl = (P * pw).sum(axis=1); worst = (W * pw).sum(axis=1)  # suma de peores: conservador
    d = pd.DataFrame({"pnl": pnl, "worst": np.minimum(worst, np.minimum(pnl, 0))})
    i, o = split(d)
    rows = [stats(i, label + " IS"), stats(o, label + " OOS")]
    return d, rows, pw

pre = [k for k in S if (lambda s: s.get("sharpe", -9))(stats(split(S[k])[0])) > 0.5 and len(split(S[k])[1]) > 100]
print("Mangas pre-registradas (Sharpe IS > 0,5 con OOS):", pre)
dpre, rows, pw = build(pre, "PRE")
print(pw.round(3).to_dict())
show(rows)
pickle.dump(dpre, open(f"{SCR}/port_pre.pkl", "wb"))
# correlaciones OOS de las mangas con Sharpe OOS>0 para referencia
