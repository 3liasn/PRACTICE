# v3: ¿se puede mejorar la cartera de bot-definitivo con fuentes no-oro? (16-nov-2026)

Cartera actual `RANGE3big+S2_A1.5_N207` reconstruida desde el ledger por operación de la tanda 15
(`bot-definitivo`, rama `fix/bt3-revision-integridad`, `backtest_v3/out/tanda15/ledger_duka.parquet`).
Las R por motor reproducen las publicadas: A +0,621R (t 3,82; n 148), N59f +0,068R, W_dst +0,068R, N141 +0,058R (OOS 2020+).

La reconstrucción no lleva el freno S2 completo ni el guard 0,8: sale más alta que la oficial (3,0 %/mes Duka frente a 2,17).
Sirve para comparar, no como cifra absoluta.

## Hallazgos
1. Régimen: la cartera reconstruida da Sharpe ≈ 2,0 en 2020–26 y **−0,15 en 2009–19** (caída −72 % a riesgo completo sin freno).
2. Reversión IBS/RSI2 en índices (v2) con 20–30 % de la volatilidad: Sharpe 2021–26 de 1,99 a 2,05–2,07 (≈ +3–4 % de
   retorno con el mismo riesgo); en 2009–19 pasa de −0,15 a −0,06/−0,10. Correlación diaria con el oro 0,04.
3. Tendencia BTC (v2): neutra en 2021–26 (1,98–2,00). Lo que mejora en 2015–19 es su periodo de selección: no cuenta.
4. Mezcla a partes iguales de riesgo: empeora (1,67–1,82). Las fuentes nuevas son más débiles que el oro en el régimen actual.

`marginal.py` y `tradeoff.py`; salidas en `out_marginal.csv` y `out_tradeoff.csv`.
