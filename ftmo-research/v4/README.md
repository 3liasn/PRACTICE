# v4: mejoras para `RANGE3big+S2_A1.5_N207` sin tocar sus reglas de entrada (16-nov-2026)

Solo investigación. No cambia `bot-definitivo`, su config, el bot, MT5 ni el VPS. Pre-registro: `PREREG.md` (commit `63b556a`).

## Base y calibración
Simulador de cuenta propio (`acct.py`) que opera las 14 616 operaciones del ledger de la tanda 15 (Dukascopy) con las reglas de
`cartera_recomendada.py` (riesgos, tope RANGE 0,75 %, 4 %/3 %, guard 0,8, freno S2). Diferencias conocidas: N30 sin stop en
lugar de N207 y flotante aproximado (una perdedora cuenta su pérdida final cada día abierta).

| Régimen actual 2020+ | Este simulador | Oficial Duka |
|---|---|---|
| %/mes, camino histórico sin retiros | 2,01 | 1,96–2,17 |
| Peor día | −2,31 % | −2,37 % |
| P(pasar el reto en 1 año) | 73 % | 81 % (MT5 67–70 %) |

En 2009–19 sale algo peor que el oficial (−0,08 %/mes; quiebra 12 m 7,8 %). Las cifras absolutas son de Dukascopy;
en MT5 (la referencia) la cartera rinde ≈ 16 % menos. **Las mejoras relativas son lo que cuenta.**

## Mejora 1 — Modo reto: ×2,5 de riesgo en Challenge y Verification (la grande)
En la evaluación solo está en juego la tarifa (€540 ≈ 0,63 %) y el tiempo; hoy se opera igual que en la fondeada y se tarda ~7 meses.
Ciclo de vida de 24 meses por plaza de 100k (tarifa, reembolso con el primer pago, 80 %→90 % y +25 % con el plan de escalado,
retiro mensual). Riesgo de la cuenta fondeada **sin cambios**. 3 semillas × 5 000 rutas:

| | Neto/mes (régimen actual) | Días hasta fondeada | P(perder la fondeada en 12 m) | Retos pagados | Neto/mes (régimen viejo) |
|---|---|---|---|---|---|
| Base (reto ×1) | 1,22–1,25 % | 198–206 | 0,1 % | 1,00 | 0,00 % |
| Reto ×2 | 1,45–1,48 % | 128–134 | 0,1–0,2 % | 1,05 | 0,03 % |
| **Reto ×2,5** | **1,49–1,51 % (+21 %)** | **102–108** | 0,1 % | 1,10 | 0,04 % |

El reto ×2,5 llega a fondeada ~3,5 meses antes. Cuesta ~0,1 retos más (régimen actual) o ~0,55 (régimen viejo). Detalle: `out_business.csv`.
Subir el riesgo de la **fondeada** (m_fond 1,5) daría 2,1 %/mes, pero en 2009–19 la pérdida de la fondeada sube del 9 % al 24–26 %
y rompe tu regla aprobada (quiebra IS ≤ 5 %): **no se recomienda**.

## Mejora 2 — Monitor de salud del edge (seguro contra que el edge muera)
Diseño estadístico, no ajustado a datos: por familia (A, RANGE, N30) se lleva la R en sombra de todas sus señales; si la media
de las últimas W (A 30, RANGE 300, N30 300) es < 0, la familia opera a la mitad («mitad») o se pausa («pausa»).
Distinto de la tanda 16, que intentó *aprender* un interruptor con 2009–19. `monitor.py`, `out_monitor.csv`.

| Escenario | Métrica | Sin monitor | Mitad | Pausa |
|---|---|---|---|---|
| Régimen actual | %/mes en 12 m | 1,99 | 1,94 (−2 %) | 1,89 (−5 %) |
| Régimen viejo | P(perder la fondeada en 12 m) | **8,0 %** | **1,0 %** | 0,1 % |

Recomendado: **«mitad»**. Cuesta ≈ 2 % del rendimiento si el edge sigue y divide por 8 el riesgo de perder la cuenta si vuelve un oro como el de 2009–19.

## Mejora 3 — Reversión en índices al 20–30 % de la volatilidad (v3)
Correlación diaria con la cartera 0,04. Sharpe 2021–26 de 1,99 a 2,05–2,07: ≈ +3–4 % de retorno con el mismo riesgo.
Pequeña y «dudosa» con tu DSR, pero es la única fuente no-oro con evidencia en los dos periodos.

## Lo que se probó y no sirve
- **Sizing por volatilidad del oro** (`regime.py`): RANGE gana en 2020+ en los tres terciles de vol (+0,059/+0,061/+0,070 R) y pierde
  en 2009–19 en los tres. A cambia de signo entre periodos. No hay patrón común: no se propone.
- **Inclinación alcista** (`side.py`): en 2020+ los largos rinden el doble que los cortos (RANGE +0,085 contra +0,043 R; A +0,76
  contra +0,39). En 2009–19 los largos de RANGE perdían (−0,038 R, t −3,4). Parte del edge actual es el oro alcista. Es un riesgo, no una palanca.
- Retirar cada 14 días rinde menos que cada 30 (1,15 contra 1,23 %/mes) porque el plan de escalado se cumple menos.
- El colchón de 2 % antes de retirar cuesta ~4 % de ingreso. En el régimen viejo baja la pérdida de la fondeada del 9–10 % al 7 %.

## Juntas
Reto ×2,5 + retiro mensual + monitor «mitad» + índices al 20 %: de ≈ 1,23 a ≈ 1,5 %/mes neto por plaza de 100k en Dukascopy
(≈ +20–23 %). En MT5, de ≈ 1,0 a ≈ 1,25 %/mes neto. Mucho más protegida si el edge del oro se apaga.

## Antes de usarlo
- Pasarlo por tu método v2 (sello, validación MT5, OK de Silvio). Nada de esto está en el bot.
- Confirmar en FTMO que no hay tope de riesgo por operación en la evaluación 2-Step. Con ×2,5, A arriesga 3,75 % por operación
  (el guard limita el riesgo abierto al 80 % del margen diario). Un hueco a través del stop puede costar el reto (solo la tarifa).
