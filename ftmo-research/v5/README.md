# v5 — Plan de fondeo rápido para `RANGE3big+S2_A1.5_N207` (16-nov-2026)

Objetivo de Silvio: **fondearse lo antes posible y después estabilizar.** Pre-registro: `PREREG.md` (commit `0107a65`).
Solo investigación: no cambia el bot, su config, MT5 ni el VPS.

Motor: el simulador de cuenta de v4 (14 616 operaciones del ledger de la tanda 15, reglas de `cartera_recomendada.py`,
calibrado contra las cifras oficiales). Solo fases Challenge (+10 %) y Verification (+5 %); si se rompe una regla se compra otro
reto al día siguiente. Trámite FTMO supuesto: 1 día tras la fase 1 y 3 tras la fase 2. Mismas rutas para todas las
configuraciones (números aleatorios comunes). Régimen actual = bootstrap de 2020-01 → 2026-10.

## Resultado (días naturales hasta la fondeada, contando reintentos; 3 semillas)

| Plan | Cuentas a la vez | Media | Mediana | P(≤ 60 d) | P(≤ 90 d) | Retos pagados (media) |
|---|---:|---:|---:|---:|---:|---:|
| Como ahora (×1, guard 0,8, S2) | 1 | 268–271 | 209–217 | 8 % | 16 % | 1,0 |
| **A. Mejor individual** | 1 | **159–168** | 87–89 | 33 % | 51–52 % | 1,3 |
| **B. Escalera de 2** | 2 | **113–116** | 61–66 | 48 % | 64 % | 2,6 |
| **C. Escalera de 3** | 3 | **98–100** | 59–61 | 50 % | 67–68 % | 3,7 |

- **A:** fase 1 ×2 (A 3 %, RANGE 1 % c/u con tope 1,5 %, N30 0,5 %), fase 2 ×1,5, guard 0,95, freno S2 apagado en el reto,
  micro-operaciones de 0,01 lotes para completar los 4 días y congelar al llegar al objetivo.
- **B:** cuenta «agresiva» (fase 1 ×6, fase 2 ×3, guard 0,95, sin freno; el guard limita cada operación a ≈ 4,75 %) + cuenta
  «segura» (×2 / ×1, guard 0,8, sin freno). Mismas señales y misma dirección, nunca cobertura entre cuentas.
- **C:** agresiva + A + oficial. El 99 % se fondea en menos de 24 meses.
- Control: dos cuentas **iguales** no aceleran nada (161 días, el doble de tarifas). La escalera gana porque la agresiva se fondea en
  las rutas buenas y la segura sobrevive a las malas.
- Con «rápida (×4/×3) + A» hay un 71 % de probabilidad de que la segunda cuenta también se fondee en los 60 días siguientes.

Datos completos: `out_speed.csv` (1 680 configuraciones), `out_ladder.csv`.

## Lo que se aprendió
1. **Más riesgo no es más rápido.** Por encima de ×3 en la fase 1 la media empeora (×8: 286 días de media en la rejilla): se
   falla y se repite. El punto dulce está en ×2–3.
2. **La fase 2 debe ir más suave que la 1** (×1–1,5): perder la verificación te devuelve al principio.
3. **N30 acelera:** quitarlo sube la media a 322 días.
4. Congelar al llegar al objetivo **solo** con micro-operaciones; sin ellas te quedas sin completar los 4 días.
5. **Régimen viejo** (si el edge del oro se apaga): ningún plan es rápido. La escalera de 3 tarda 336 días de media y gasta
   5,6 retos. Es el precio del seguro.

## ¿Compensan las tarifas? (régimen actual)
Fondeada estable ≈ 1,6–2 %/mes de 100k (MT5–Duka). Cada día antes vale ≈ 55–65 USD.
- **B** adelanta ≈ 155 días (≈ 8 500–10 000 USD) y cuesta ≈ 1,6 retos más (≈ €870).
- **C** adelanta ≈ 170 días (≈ 9 300–11 000 USD) por ≈ 2,7 retos más (≈ €1 460).

## Después de fondearse: estabilizar (v4)
Fondeada con el riesgo oficial (×1), monitor de salud del edge «mitad», retiro mensual. Las otras cuentas de la escalera
siguen; si se fondean, es capital extra.

## Antes de usarlo
- Confirmar con FTMO: (1) operar varias cuentas propias con las mismas señales y en la misma dirección; (2) que no haya tope de
  riesgo por operación en la evaluación; (3) el capital máximo combinado.
- Pasarlo por tu método (sello, validación en MT5) y tu OK. Es post-hoc sobre 2020+ y depende de que el edge siga vivo.
