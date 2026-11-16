# Investigación v2: ¿5 % mensual bajo reglas FTMO 2-Step? (datos 2016 – oct 2026)

**Veredicto: no se consiguió.** Ninguna estrategia ni combinación probada da ≥ 5 % al mes respetando las reglas
FTMO 2-Step fuera de muestra. Ni siquiera eligiendo las mangas mirando el futuro (cota con trampa) se llega.

Continúa `../ftmo-research/` (OANDA 2005–2020), que ya dio el mismo veredicto. Esta versión cubre lo que quedó
sin probar allí: 2020–2026, cripto, el oro del ciclo alcista y los motores de ruptura de `bot-definitivo`.
Solo investigación: no toca `apex-v9`, `bot-definitivo`, MT5, el VPS ni el bot en vivo, y no envía órdenes.

## Datos (fuentes)

| Fuente | Instrumentos | Periodo |
|---|---|---|
| histdata.com, M1 ASCII (EST fija → UTC) | XAUUSD, XAGUSD, NSXUSD (US100), SPXUSD (US500), GRXEUR (GER40), WTIUSD, EURUSD, GBPUSD, cruces | ene 2016 – oct 2026 |
| data.binance.vision, klines 1m | BTCUSDT, ETHUSDT | ene 2018 – oct 2026 |
| Servidor FTMO (export solo lectura, `asistente-trading/data/oro`) | XAUUSD M5, spreads por hora, swaps | 2015 – oct 2026 |

Partición fija: **IS 2016–2021** (cripto 2018–2021), **OOS 2022 – oct 2026**.

Costes ida y vuelta: oro 0,45 USD (spread FTMO medido 0,30–0,46 + comisión ~0,0014 % + deslizamiento);
índices 2 pb; FX mayores 1,2–1,6 pb; cruces nocturnos 2,2–4 pb; cripto 12–15 pb (0,065 % de comisión + spread).
Swap por noche con los valores de `especificaciones.json` del servidor FTMO (oro e índices) y supuestos
conservadores en el resto. Comisiones FTMO: fuentes no oficiales, a verificar en tu plataforma.

## Reglas FTMO modeladas (`src/ftmo.py`)

Fase 1 +10 %, fase 2 +5 %, mínimo 4 días operados, sin límite de tiempo. Pérdida diaria: el equity (con
flotante) no puede caer 5 % del balance inicial por debajo del balance al inicio del día de Praga. Pérdida máxima:
equity ≥ 90 % del inicial (estática). Fondeada: retiro del 80 % del beneficio a fin de mes (con y sin colchón
del 5 %). Se simula con la historia real (un arranque por mes) y con bootstrap por bloques de 20 días.

Prueba sintética del simulador (estrategia de 5 %/mes, colas gordas, 12 meses): con Sharpe 2 se pierde la
fondeada en el 54 % de los casos; con Sharpe 3, 37 %; con Sharpe 4, 20 %. Coincide con el estudio anterior.

## Qué se probó y qué salió (Sharpe mensual anualizado, neto de costes)

| Familia | Script | IS | OOS | Conclusión |
|---|---|---|---|---|
| Tendencia diaria (TSMOM 20/60/120/250, Donchian 20/55) en oro, US100, BTC, ETH | `sleeves.py` | −0,3 a 1,2 | −0,3 a 1,0 | Cripto pierde la ventaja en 2022–2026; oro mejora por el ciclo alcista |
| Ruptura del máx/mín de día/semana/mes, stop 0,15·ATR, 2R (Engine B congelado) | `breakout.py`, `scan_breakout.py` | ventaja **bruta** 0,03–0,5R | neta ≈ 0 | El coste se lleva 0,15–0,25R por operación con stops tan cortos |
| Misma ruptura con stops más anchos (k 0,3/0,6/1; rr 1/2/4, elegido en IS) | `scan_k.py` | — | semanal 0,1–1,0; diaria negativa | Ventaja pequeña en rupturas semanales |
| Reversión nocturna tipo *night scalper* (EURGBP, EURCHF, AUDNZD, EURUSD) | `night.py` | — | — | Ventaja bruta 0,3–2 pb por operación < coste 2–3 pb |
| Reversión IBS en índices | `sleeves.py` | US100 0,72 | US100 1,20; US500 0,78 | La manga más sólida; solo índices USA |

Nota para `bot-definitivo`: el +0,3R del Engine B se midió con velas H1. En M1 la ventaja **bruta** de la ruptura
semanal en oro es ~0,17R y la **neta** de costes ~0,07R (`out/scan_brk_k015_neto.csv`). Dentro de una vela H1
no se sabe si se tocó antes el stop o el objetivo, y eso infla el resultado.

## Cartera y simulación FTMO

**Regla honesta** (`portfolio.py`): entra toda manga con Sharpe IS ≥ 0,3, pesos de igual volatilidad en IS,
cartera a 10 % de volatilidad anual en IS. 13 mangas, correlación media OOS 0,07.

| | Mes medio | Sharpe | Max DD | Meses positivos |
|---|---|---|---|---|
| IS 2016–2021 | 1,91 % | 2,29 | −5,3 % | 76 % |
| **OOS 2022–2026** | **0,70 %** | **0,86** | −14,6 % | 60 % |

Simulación FTMO OOS (`sim_port.py`, bootstrap 2000 rutas, 12 meses desde la compra del reto):

| Escala | Mes teórico | Pasa las 2 fases | Pierde la fondeada | Pago medio cobrado al mes |
|---|---|---|---|---|
| 1× | 0,68 % | 30 % | 1 % | 0,08 % |
| 2× | 1,37 % | 35 % | 29 % | 0,18 % |
| 3× | 2,05 % | 8 % | 8 % | 0,02 % |
| 7,3× (5 %/mes) | 5,00 % | **0 %** | — | 0 % |

**Cota con trampa** (`cota_optimista.py`): 8 mangas elegidas mirando el OOS y flotante intradía ignorado.
Sharpe 1,72, mes medio 1,41 % con 10 % de vol. Escalada a 5 %/mes: pasa el 47 %, pierde la fondeada el 45 %
(de las que pasan, el 97 % la pierde en 12 meses) y el pago real cobrado es 0,55 % al mes. El mejor pago se da a
2× (mes teórico 2,8 %): pasa el 75 % y cobra ~1 % al mes. Esto es un techo, no algo esperable.

## Por qué no sale

5 % al mes con una pérdida máxima del 10 % y diaria del 5 % exige una estrategia con Sharpe real ≥ 3–4 (ver tabla
sintética). Lo mejor validado fuera de muestra en dos estudios (16 + 11 años, ~200 series) está en 0,9–1,2 por manga
y ~0,9 en cartera; con trampa, 1,7. La distancia no se cierra combinando más mangas: lo que sube dentro de muestra
cae al validar.

## Revisión

Pendiente de revisión independiente (ver la nota de la PR).

## Reproducir

```bash
pip install pandas numpy numba pyarrow scipy
python3 src/dl_hist.py XAUUSD NSXUSD SPXUSD GRXEUR EURUSD XAGUSD ...   # ~20 s por año e instrumento
bash: descargar data.binance.vision BTCUSDT/ETHUSDT 1m mensuales en /home/user/data2/binance
python3 src/prep.py ftmo XAUUSD NSXUSD SPXUSD GRXEUR EURUSD XAGUSD BTCUSDT ETHUSDT EURGBP EURCHF AUDNZD
python3 src/scan_k.py XAUUSD NSXUSD SPXUSD GRXEUR BTCUSDT ETHUSDT XAGUSD EURUSD
python3 src/portfolio.py && python3 src/sim_port.py && python3 src/cota_optimista.py
```
`src/dl_duka.py` (Dukascopy) queda como alternativa; ese servidor limita las descargas (HTTP 429).
