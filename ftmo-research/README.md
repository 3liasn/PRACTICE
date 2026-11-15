# Investigación: ¿5 % mensual bajo reglas FTMO 2-Step?

**Veredicto: no se consiguió.** Ninguna estrategia ni combinación probada sostiene una media de ≥ 5 % al mes
respetando las reglas FTMO 2-Step cuando se valida fuera de muestra y con costes realistas.

Investigación independiente: no toca `apex-v9`, `xauusd-quant-ecosystem`, MT5 ni el bot en vivo, y no envía órdenes.

## Datos

- OANDA, velas de 1 minuto, enero 2005 – mayo 2020, 25 instrumentos (índices, oro, petróleo, FX, bonos, agrícolas).
  Fuente: repositorio público `FutureSharks/financial-data` (`src/prep.py` los convierte a parquet).
- Partición fija: **dentro de muestra (IS) 2005–2012**, **fuera de muestra (OOS) 2013 – mayo 2020**.
- Costes por ida y vuelta en puntos básicos del precio (US500 1,5; US100 1,5; US2000 3; XAUUSD 1,5; EURUSD 1; …)
  más swap por noche natural en posiciones que duermen.

Limitaciones: los datos acaban en mayo de 2020 (2020–2026 sin probar), son precios de OANDA y no del servidor de
FTMO, y no hay datos de cripto ni de acciones.

## Reglas FTMO modeladas

Objetivo 10 % (Challenge) y 5 % (Verification), mínimo 4 días operados, pérdida diaria máxima 5 % del balance
inicial (incluye flotante), pérdida máxima 10 % estática. En la cuenta fondeada se simulan dos políticas de retiro:
retirar todo cada mes o dejar un colchón del 5 %.

## Qué se probó

| Familia | Script | Resultado tras costes |
|---|---|---|
| Momentum intradía "área de ruido" (Zarattini et al.) en índices USA | `s1_noise.py` | Sharpe −0,2 a 0,7 (configuración del artículo), drawdowns de 25–51 % |
| Ruptura de rango de apertura (5/15/30/60 min) en índices, oro, petróleo, FX, bonos | `sB_orb.py` | Sin ventaja consistente IS→OOS |
| Estacionalidad horaria (25 instrumentos) | `s2_tod.py`, `sD_misc.py` | Efectos reales de 1–4 pb, del tamaño del coste |
| Reversión diaria IBS/RSI2/días bajistas en 8 índices | `sA_dailymr.py` | Funciona solo en índices USA |
| Reversión y tendencia diaria en los 25 instrumentos | `sE_daily_all.py` | Tendencia negativa; reversión solo en índices USA |
| Momentum de última media hora, fade de gap, cambio de mes | `sD_misc.py` | Sharpe OOS entre −0,9 y 0,6 |

## Resultados de cartera (`sG_portfolio.py`)

Pesos fijados solo con IS, normalizada a 10 % de volatilidad anual en IS.

| Cartera | Sharpe IS | Sharpe OOS | Mes medio OOS | Max DD OOS |
|---|---|---|---|---|
| A · todas las mangas con Sharpe IS ≥ 0,5 (16 mangas) | 2,56 | 0,48 | 0,30 % | −16,8 % |
| B · reversión larga IBS < 0,2 en US500, US100 y US2000 | 1,29 | 0,94 | 0,50 % | −6,5 % |
| C · cota optimista (elegidas mirando también el OOS) | 1,91 | 1,11 | 0,73 % | −8,8 % |

La cartera A es el ejemplo de lo que pasa al elegir por backtest: 2,2 % al mes dentro de muestra, 0,3 % fuera.

Simulación FTMO sobre los días OOS (bootstrap por bloques, 24 meses fondeado, corte diario de cartera en −4 %):
escalando la cartera B hasta una media teórica de ~4,7 % al mes, la cuenta se pierde en 12 meses en el 93–99 % de
los casos. El pago medio mensual realmente cobrado no pasa de ~1 % del balance en ninguna escala.

## Qué haría falta (`sH_verify.py`)

Estrategia hipotética con media de 5 % al mes, colas gordas; probabilidad de perder la cuenta en 12 meses:

| Sharpe real | Retirando todo cada mes | Dejando colchón del 5 % |
|---|---|---|
| 1,0 | 99,8 % | 98,4 % |
| 2,0 | 77,7 % | 47,5 % |
| 3,0 | 23,2 % | 6,9 % |
| 4,0 | 3,6 % | 0,7 % |

Lo mejor validado aquí tiene Sharpe ≈ 0,9–1,1 fuera de muestra. Hace falta 3–4.

## Revisión independiente

Un agente revisor distinto del autor reejecutó `sG_portfolio.py` y `sH_verify.py`, reimplementó la reversión IBS
desde el parquet y escribió su propio simulador. Confirmó las cifras de arriba y no encontró sesgo de anticipación.
Sus observaciones, todas a favor de la estrategia (es decir, la realidad sería peor):

- El simulador recorta cada día en −4 % con ejecución perfecta, así que la regla de pérdida diaria del 5 % nunca
  salta. Sin ese corte, la quiebra a 12 meses sube de 23 % a 63 % con Sharpe 3 y de 3,6 % a 24 % con Sharpe 4.
- Los pagos simulados son brutos; con el reparto del 80 % serían un 20 % menores.
- La cartera B se destacó después de ver el OOS; su 0,94 tiene un error estándar de ~0,36.
- Con costes al doble, el Sharpe OOS de la reversión baja a 0,93 (US100), 0,49 (US500) y 0,42 (US2000).
- De las 176 series exploradas, el mejor Sharpe OOS individual es 1,08. Eligiendo a posteriori, la cartera llega
  a 1,6–2,0, todavía por debajo de 3–4.

## Reproducir

```bash
pip install pandas numpy numba pyarrow scipy
# editar las rutas de src/prep.py y src/common.py
python3 src/prep.py            # CSV -> parquet
python3 src/sF_sleeves.py      # mangas
python3 src/sG_portfolio.py    # carteras + simulador FTMO
python3 src/sH_verify.py       # verificación independiente + tabla de Sharpe requerido
```
