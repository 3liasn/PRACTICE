# Pre-registro v4 — mejorar `RANGE3big+S2_A1.5_N207` sin tocar sus reglas de entrada (16-nov-2026)

Escrito antes de medir. Solo investigación: no cambia `bot-definitivo`, el bot, MT5 ni el VPS.

## Base
Ledger por operación de la tanda 15 (Dukascopy, motor backtest_v3; N30GapFade en lugar de N207: diferencia conocida).
Simulador de cuenta propio con las reglas de `cartera_recomendada.py`: riesgo por motor, tope RANGE 0,75 %, riesgo abierto 4 %,
por dirección 3 %, guard 0,8, freno S2 (DD ≥ 2 % → ×0,5; ≥ 4 % → ×0,25). Primero se calibra: debe reproducir, con la misma MC
(bloques de 8 semanas, 52 semanas, sin retiros), el orden de magnitud oficial Duka OOS: ≈ 2,1 %/mes, P(breach) < 1 %,
peor día ≈ −2,4 %, DD ≈ 7 %. Si no, se ajusta el proxy de flotante y se documenta.

## Palancas (rejilla cerrada aquí)
1. **Política de retiros** en la fondeada: nunca (como la MC oficial) · todo cada 30 d · todo cada 14 d · por encima de un colchón de 2 % · de 4 %.
2. **Modo reto**: multiplicador de riesgo en Challenge/Verification m_c ∈ {1; 1,5; 2; 2,5; 3} (topes ×m_c; guard igual).
3. **Modo fondeada**: m_f ∈ {1; 1,25; 1,5}.
4. **Plan de escalado** FTMO activo en todo: ciclo de 4 meses con +10 % neto y ≥ 2 pagos → +25 % de balance inicial y 90 %.

## Métrica y regla de decisión (fija)
Ciclo de vida de 24 meses en una «plaza» de 100k: reto €540 (0,63 %), reembolso con el primer pago, 80 % → 90 % al escalar,
si se rompe una regla se paga otro reto. Métrica: **ingreso neto medio por mes** (% de 100k).
Se elige la combinación que maximiza el ingreso en el régimen actual (bootstrap 2020-01 → 2026-10) **con dos condiciones**:
(a) P(perder la cuenta fondeada en sus primeros 12 meses) ≤ 5 %; (b) en el régimen viejo (bootstrap 2009-03 → 2019-12) el
ingreso neto medio no es peor que el de la política base (m_c = 1, m_f = 1, retiro mensual).

## Palancas de cartera (después)
5. Reversión IBS/RSI2 en índices dentro de la misma cuenta, cuota de vol 20 % (fijada por v3, sin reoptimizar).
6. ¿El edge depende de la volatilidad del oro? Se mide R por terciles de vol realizada 20 d (vs su mediana de 250 d) en IS y en OOS.
   Solo se propone un sizing por régimen si el patrón tiene el mismo signo en los dos periodos.
