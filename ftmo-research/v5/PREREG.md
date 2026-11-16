# Pre-registro v5 — Plan de fondeo rápido (16-nov-2026)

Objetivo de Silvio: **llegar a la cuenta fondeada lo antes posible** con la cartera `RANGE3big+S2_A1.5_N207`; después, estabilizar.
Escrito antes de medir. Solo investigación: no cambia el bot, su config, MT5 ni el VPS.

## Métrica principal
Días naturales desde la compra del primer reto hasta tener la cuenta fondeada, **contando reintentos** (si se rompe una regla se
compra otro reto al día siguiente). Secundarias: tarifas pagadas (€540 por reto de 100k), P(fondeada en ≤ 30/60/90 días).
Régimen actual = bootstrap por bloques de 8 semanas de 2020-01 → 2026-10; régimen viejo = 2009-03 → 2019-12 (se informa siempre).

## Palancas (rejilla cerrada)
1. Multiplicador de riesgo en fase 1 (m1 ∈ {1, 2, 3, 4, 5, 6, 8}) y en fase 2 (m2 ∈ {1; 1,5; 2; 3; 4}), por separado.
2. Guard en el reto: 0,8 (oficial) o 0,95.
3. Freno S2 en el reto: sí / no.
4. Final de fase: seguir operando, o **congelar al llegar al objetivo** (no abrir más; pasar en cuanto se cierre lo abierto).
5. **Micro-operaciones** de 0,01 lotes para completar los 4 días de trading (un día cuenta si se abre algo).
6. Mezcla de motores en el reto: oficial · A pesado (A ×1,67) · sin N30.
7. **Escalera de retos en paralelo** (2 o 3 cuentas a la vez, mismas señales y misma dirección, riesgos distintos): días hasta la
   PRIMERA fondeada y tarifas totales. Se prueba sobre las 5 mejores configuraciones individuales.

## Regla de decisión
Se elige la configuración individual con menor media de días en el régimen actual; si otra queda a ≤ 5 % de esa media con menos
tarifas esperadas, se prefiere la de menos tarifas. Para la escalera: solo se recomienda si baja la media de días ≥ 20 % frente a la
mejor individual. En todos los casos se informa el régimen viejo.

## Después de fondearse (estabilizar, de v4)
Fondeada con el riesgo oficial (m = 1), monitor de salud del edge «mitad», retiro mensual.
