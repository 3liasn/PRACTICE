# Investigación v2: ¿5 % al mes bajo reglas FTMO 2-Step? (16-nov-2026)

**Veredicto: no se consiguió.** Con datos del propio servidor FTMO hasta octubre de 2026, costes reales y BTC añadido,
ninguna estrategia ni combinación sostiene ≥ 5 % al mes sin perder la cuenta. Confirma la v1 (`../README.md`) con
datos nuevos e independientes.

Investigación separada: no toca `apex-v9`, MT5, el VPS ni el bot en vivo, y no envía órdenes.

## Qué cambia respecto de la v1

| | v1 (15-nov) | v2 (esta) |
|---|---|---|
| Datos | OANDA M1 2005 – may-2020 | **Velas del servidor FTMO** 2015 → 16-oct-2026 (17 símbolos, rama `data/ftmo-vps` de `apex-v9`) + OANDA 2005–2020 como entrenamiento de índices + **BTC** Bitstamp M1 2015 → 14-nov-2026 |
| Tramo fuera de muestra | 2013 – may-2020 | **2021 – oct-2026** (lo que más se parece a hoy) |
| Costes | supuestos en pb | **spread real por hora** de FTMO (ticks 2025–26), comisión, deslizamiento y **swaps reales** de FTMO |
| Método | partición fija | **pre-registro con commit** (`PREREG.md`, `d704ff4`) antes de medir; ronda 2 marcada «post-hoc» (`POSTHOC.md`) |

## Reglas FTMO modeladas

Objetivo 10 % (Challenge) y 5 % (Verification); pérdida diaria máxima 5 % del balance inicial contada sobre el peor
punto intradía (incluye flotante); pérdida máxima 10 % estática; mínimo 4 días operados; sin límite de tiempo.
Cuenta fondeada: retiro mensual, reparto 80 %, el balance vuelve al inicial tras el retiro. Reto 100k ≈ €540
(0,63 % de la cuenta), reembolsado con el primer pago.
**Ojo:** ftmo.com no es accesible desde el entorno de esta investigación; las reglas salen de varias fuentes de terceros
que coinciden entre sí. Conviene confirmarlas en la web de FTMO.

## Qué se probó: 80 mangas, 13 familias (Sharpe anual tras costes)

| Familia | Mangas | Sharpe IS (mediana) | Sharpe OOS 2021-26 (mediana) | Mejor OOS |
|---|---:|---:|---:|---|
| F1 Sesiones del oro y la plata (largo Asia / corto EE. UU., Blose et al. 2018) | 6 | −0,7 | −0,4 | 0,93 (oro largo de noche; IS 0,14) |
| F2 Tendencia BTC, conjunto Donchian (Zarattini et al. 2025) | 2 | **2,02** | **0,31** | 0,38 |
| F3 Reversión corta en índices (IBS < 0,2 / RSI2 < 10) | 14 | 0,26 | **0,50** | 0,78 (RSI2 US500) |
| F4 Tendencia multi-activo (17 símbolos) | 17 | −0,22 | −0,40 | 0,54 (oro) |
| F5 Estacionalidad por hora | mapa | — | — | solo artefactos de spread y BTC 17:00 NY (+5 pb/h, cuesta 18,5 pb) |
| F6 Rebalanceo de fin de mes en FX | 4 | 0,42 | −0,16 | 0,17 |
| F7 Pares AUD/NZD y oro/plata | 2 | −0,99 | −0,79 | −0,36 |
| R1 Deriva tras NFP/IPC/PCE/FOMC (post-hoc) | 20 | −0,31 | −0,60 | 0,87 (IS 0,15) |
| R3 Cambio de mes en índices (post-hoc) | 6 | 0,00 | 0,15 | 0,24 |
| R4 Tendencia intradía BTC (post-hoc) | 2 | −0,39 | −1,46 | −1,12 |
| R5 Reversión diaria en oro (post-hoc) | 2 | 0,54 | 0,10 | 0,21 |
| R6 Reversión índices con filtro SMA200 (post-hoc) | 5 | 0,03 | 0,27 | 0,70 |

Detalle por manga: `out_families.csv`, `out_round2.csv`, `out_f5_hourmap.csv`.

Lo que aguanta: la **reversión corta en índices de EE. UU.** es la única familia positiva dentro y fuera de muestra en
v1 (2013–2020) y en v2 (2021–2026). Pero rinde poco: Sharpe 0,5–0,8 por manga.

## Carteras

| Cartera | Cómo se eligió | Sharpe IS | Sharpe OOS | Mes medio OOS (vol 10 %) |
|---|---|---:|---:|---:|
| PRE | filtro pre-registrado (Sharpe IS > 0,5): BTC tendencia ×2 + fin de mes GBP | 2,22 | **0,35** | 0,27 % |
| MR_indices | reversión IBS/RSI2 en US500, US100, US30, JP225 | 0,35 | **0,63** | 0,57 % |
| OPT_cota | **trampa a propósito**: las mangas con Sharpe OOS > 0,5 (elegidas mirando el resultado) | 0,42 | 1,11 | 0,93 % |

La cartera PRE repite el patrón de la v1: lo que brilla en el pasado (BTC 2015–2020) se apaga después.

## Frontera FTMO con lo mejor encontrado (bootstrap por bloques de los días OOS, 20 000 rutas)

| Cartera | Escala | Mes medio | Caída máx. histórica | P(perder la cuenta fondeada en 12 m) | Neto/mes del ciclo completo* |
|---|---:|---:|---:|---:|---:|
| MR_indices | 1 | 0,57 % | −16,7 % | 47 % | 0,09 % |
| MR_indices | 6 | 3,43 % | −100 % | 100 % | −0,87 % |
| OPT_cota | 1 | 0,93 % | −9,9 % | 37 % | 0,24 % |
| OPT_cota | 6 | **5,59 %** | **−59 %** | **100 %** | −1,60 % |

\* Ciclo completo a 24 meses: se paga el reto, se pasa (o no) Challenge y Verification, se cobra el 80 % cada mes en la
cuenta fondeada, y si se pierde se paga otro reto. Lo máximo que sale es **0,43 %/mes** (OPT_cota, escala 1,5) y
0,19 %/mes con la cartera honesta MR_indices. Tabla completa: `out_frontier.csv`.

Llegar al 5 % al mes exige subir tanto el riesgo que la cuenta se pierde en todas las simulaciones, incluso con la cota tramposa.

## Qué haría falta (`required.py`)

Estrategia hipotética con media de 5 % al mes, colas gordas (t de Student, 4 g.l.), retiro mensual:

| Sharpe real | Vol anual | P(perder la cuenta en 12 m) | P(pasar las dos fases en ≤ 60 días) |
|---:|---:|---:|---:|
| 1 | 60 % | 100 % | 17 % |
| 2 | 30 % | 98 % | 49 % |
| 3 | 20 % | 56 % | 65 % |
| 4 | 15 % | 20 % | 73 % |
| 5 | 12 % | 8 % | 79 % |

Hace falta Sharpe ≈ 5 tras costes. Lo mejor validado aquí tiene 0,35–0,63; con trampa, 1,11. Coincide con la tabla
de la v1 (su revisor obtuvo 63 % y 24 % para Sharpe 3 y 4 sin el corte diario).

## Errores encontrados y corregidos durante el trabajo

- **F6 (fin de mes FX) tenía anticipación**: decidía a las 10:00 NY con el cierre del US500 de ese mismo día (17:00).
  Corregido a «cierre del día anterior». Su Sharpe OOS bajó de 0,79 a 0,12 (GBPUSD). Todas las tablas son posteriores.

## Limitaciones

- Índices y petróleo: el servidor FTMO solo sirve intradía desde 2021; su entrenamiento usa OANDA 2005 – may-2020.
- Swaps: foto del 16-oct-2026 aplicada a todo el periodo (en 2015–2021, con tipos cerca de cero, eran menores). En
  petróleo la foto refleja la curva de futuros de ese día y es poco fiable fuera de él.
- BTC: FTMO no está en los datos; coste supuesto 0,18 % ida y vuelta y 3 pb/noche (sin fuente oficial).
- Sin acciones individuales (no hay datos alcanzables desde el entorno): no se pudo probar la ruptura de apertura
  en «acciones en juego» (Zarattini et al. 2024), que es la estrategia publicada con el Sharpe más alto que conozco.
- El peor punto intradía sale de velas H1 o M5, no de ticks.

## Reproducir

```bash
pip install pandas numpy numba pyarrow
python3 prep.py && python3 prep_oanda.py     # requiere los CSV fuente (ver docstrings)
python3 f5_hourmap.py && python3 families.py && python3 round2.py
python3 portfolio.py && python3 lifecycle.py && python3 required.py
```
