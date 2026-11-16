# Pre-registro v2 — ¿5 % al mes bajo FTMO 2-Step? (16-nov-2026)

Escrito **antes** de medir. Continúa la investigación v1 (`../README.md`, veredicto «no se consiguió» con OANDA 2005–2020)
atacando sus huecos: datos 2020–2026, precios y costes del propio servidor FTMO, y cripto.

## Datos
- Velas reales del servidor FTMO (rama `data/ftmo-vps` de `apex-v9`, exportadas el 16-oct-2026, solo lectura): 17 símbolos.
  FX y metales con intradía continuo desde 2015-01; índices y petróleo desde 2021 (US30 desde 2019-02).
- OANDA M1 2005 – may-2020 (repo público `FutureSharks/financial-data`): tramo de entrenamiento para índices y petróleo.
- BTC/USD M1 Bitstamp 2015 – nov-2026 (repo público `ff137/bitstamp-btcusd-minute-data`).

## Partición (fija)
- **IS (se elige aquí)**: hasta 2020-12-31. FX/metales/BTC: FTMO o Bitstamp 2015–2020. Índices/petróleo: OANDA 2005–may-2020.
- **OOS (se mira una vez por familia)**: 2021-01-01 → 2026-10-16 (BTC hasta 2026-11-14). Índices/petróleo: feed FTMO.
- Nada se reelige después de ver el OOS. Si se prueba algo nuevo después, se etiqueta «post-hoc».

## Costes (FTMO)
- Spread: mediana real por hora y símbolo (`spread_por_hora.csv`, ticks 2025–2026), pagado completo en cada ida y vuelta.
- Comisión: FX 5 USD/lote ida y vuelta (≈0,5 pb en EURUSD); metales 0,0007 %/lado... **se usa 1 pb ida y vuelta para metales**,
  0 en índices y petróleo (fuentes de terceros; ftmo.com no accesible desde el entorno).
- Deslizamiento: +0,5 pb por ida y vuelta en todo.
- Swap: el de la foto 2026-10-16 convertido a pb por noche sobre el precio de esa fecha; triple el miércoles (FX/metales) o el viernes (índices/petróleo).
- BTC (sin dato FTMO en el repo): 0,065 %/lado de comisión + 0,05 % de spread y deslizamiento = **0,18 % ida y vuelta**, y financiación de 0,03 %/noche en cualquier dirección (supuestos conservadores, sin fuente oficial).
- Prueba de estrés: todo coste ×2.

## Familias (parámetros cerrados aquí)
| id | familia | instrumentos | parámetros |
|---|---|---|---|
| F1 | Sesión del oro: largo en horas de Asia/Europa, fuera (o corto) en horas de EE. UU. (Blose et al. 2018) | XAUUSD, XAGUSD | ventanas NY: A = 18:00→08:00 largo; B = 08:00→16:00 corto; C = A+B |
| F2 | Tendencia BTC, conjunto Donchian (Zarattini et al. 2025) | BTCUSD | lookbacks {10,20,30,60,90,150,250} días, largo/plano y largo/corto, objetivo vol 25 % anual |
| F3 | Reversión corta en índices (IBS<0,2 / RSI2<10, salida cierre>máx. de ayer) | US500, US100, US2000*, UK100, JP225 | solo largos; *US2000 solo IS |
| F4 | TSMOM diario multi-activo | los 17 FTMO | señal = media de signos de retornos 20/60/120/250 d, objetivo vol 10 % por símbolo |
| F5 | Estacionalidad por hora (mapa IS → regla) | 17 FTMO + BTC | horas con t-stat IS ≥ 3 en el mismo signo; ventanas contiguas; operar solo si media IS > 2×coste |
| F6 | Fin de mes USD (rebalanceo, Melvin–Prins) | EURUSD, GBPUSD, AUDUSD, USDJPY | último día hábil, 10:00→11:00 NY; dirección según US500 vs resto del mundo en el mes |
| F7 | Pares: AUD/NZD, XAU/XAG | AUDUSD-NZDUSD, XAUUSD-XAGUSD | z-score 20 d del log-ratio, entra |z|>2, sale z=0, tope 10 días |

## Cartera
Pesos fijados con IS (paridad de riesgo sobre las mangas con Sharpe IS > 0,5), escala para 10 % de vol anual en IS.

## Puerta del objetivo (todas a la vez, en el OOS)
1. Media mensual ≥ 5 % del balance inicial tras costes, a la escala usada.
2. Ninguna violación de pérdida diaria (−5 %) ni de pérdida máxima (−10 %) en el camino OOS real.
3. Monte Carlo (bootstrap por bloques del OOS): P(perder la cuenta en 12 meses fondeado) ≤ 10 % y P(pasar Challenge+Verification en ≤ 60 días hábiles) ≥ 50 %.
4. Con costes ×2 la media mensual sigue ≥ 3 %.

Si nada cruza la puerta, el informe lo dice y muestra la frontera alcanzable (media mensual frente a riesgo de perder la cuenta).
