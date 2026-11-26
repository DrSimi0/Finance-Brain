# Arquitectura por departamentos

```
                 ┌────────────────────────── Dirección (tú) ───────────────────────────┐
                 │  decide qué se investiga, aprueba pasar a paper / real              │
                 └─────────────────────────────────────────────────────────────────────┘
   Agentes IA (TradingAgents)        Investigación                Riesgo / Validación
   agentes/  ── propone ideas ──►    investigacion/  ─ señales ─► validacion/
   (registro prospectivo,            estrategias causales,        backtest con costos,
    nunca backtest)                  catálogo con rejillas        walk-forward, veredicto
            ▲                               ▲                             │
            │                               │                             ▼
   Datos  datos/  (alpaca-py → Parquet, control de calidad)     resultados/experimentos/*.json
            ▲
   Ejecución ejecucion/ (Alpaca, solo lectura) ──► Monitoreo monitoreo/ (reporte diario)
```

## Reglas que el código impone

| Riesgo | Cómo se controla | Dónde |
| --- | --- | --- |
| Look-ahead en señales | La señal en t usa solo datos ≤ t; test que lo verifica truncando datos | `tests/test_validacion.py::test_estrategias_son_causales` |
| Look-ahead en ejecución | Señal de t se ejecuta en la apertura de t+1 | `validacion/backtest.py`, test `test_ejecucion_en_barra_siguiente` |
| Look-ahead del LLM | Ideas históricas marcadas "contaminadas"; evaluación solo con precios posteriores | `agentes/registro_ideas.py` |
| Ignorar costos | Comisión y deslizamiento siempre aplicados (configurables en `.env`) | `ModeloCostos` |
| Sobreajuste | Walk-forward IS→OOS, ratio de degradación, nº de combinaciones reportado | `validacion/walk_forward.py` |
| Concluir con poca muestra | Mínimo de operaciones OOS antes de cualquier veredicto | `validacion/veredicto.py` |
| Reproducibilidad | Cada validación guarda JSON con datos, parámetros, costos, versiones y commit | `experimentos.py` |
| Supervivencia | Documentado: el universo debe fijarse con fecha de corte | `datos/alpaca_datos.py` |

## Limitaciones conocidas (honestas)

- En cada tramo OOS la cartera empieza plana: una estrategia de cruce que ya estaba
  "dentro" no entra hasta el siguiente cruce. Es conservador, pero sesga a la baja.
- Solo largos, un activo a la vez, tamaño = todo el capital. Sin cortos ni carteras aún.
- El Sharpe usa 252 periodos/año: válido para barras diarias, no intradía.
- Precios ajustados retroactivamente (splits y dividendos): bien para retornos, no para
  umbrales de precio absoluto.
- Los criterios del veredicto (`Criterios`) son un punto de partida, no un estándar.
