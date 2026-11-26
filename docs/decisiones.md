# Registro de decisiones

## 2026-11-26 — Repos externos como dependencias, no copiados

- **vectorbt** (`pip`, v1.2.x): motor de backtest. Se usa `Portfolio.from_signals` con
  comisión y deslizamiento. Envuelto en `finance_brain.validacion` para imponer las reglas
  del laboratorio (ejecución en la barra siguiente, costos obligatorios, walk-forward).
- **alpaca-py** (`pip`, v0.45.x): datos históricos y lectura de la cuenta.
- **TradingAgents** (TauricResearch, Apache-2.0): extra opcional `[agentes]`, fijado al tag
  **v0.7.1** e instalado desde GitHub (no está en PyPI).

### Por qué TradingAgents v0.7.1 y no la última versión

El 24-nov-2026 TauricResearch publicó TradingAgents **1.0**, que reescribe el proyecto como
una aplicación de terminal en Node/TypeScript ("agentic finance research"): sus binarios se
publican solo para Linux y macOS, requiere Node ≥ 22 y responde preguntas de research; no
tiene API de Python. La v0.7.1 (27-oct-2026) es la última versión Python: el grafo
multi-agente (analistas → debate alcista/bajista → trader → riesgo → gestor de cartera)
con `TradingAgentsGraph.propagate(ticker, fecha)`, instalable con pip en Windows.

Implicaciones: v0.7.1 no recibirá mejoras nuevas. El puente
(`agentes/tradingagents_puente.py`) solo usa `propagate`, así que cambiar de motor de
agentes en el futuro (p. ej. llamar a la 1.x con `tradingagents -p ... --json` desde otra
máquina, o a otro framework) se limita a ese archivo.

## 2026-11-26 — Las decisiones del LLM no se backtestean

Un LLM entrenado con datos hasta su fecha de corte "conoce" lo que pasó después de
cualquier fecha histórica que se le pida analizar. Por eso:

1. Las ideas se registran (`resultados/ideas.jsonl`, append-only) con su hora de registro.
2. Una idea con `fecha_analisis` anterior a la fecha de registro se marca **contaminada**
   y no cuenta.
3. Las ideas válidas se evalúan solo con precios **posteriores** a su registro
   (`finance-brain evaluar-ideas`).
4. Lo que sí se backtestea son reglas deterministas del catálogo (`investigacion/`).

## 2026-11-26 — Ejecución en solo lectura

`ejecucion/` lee cuenta, posiciones y órdenes; no envía órdenes. La estrategia en vivo
sigue donde está. El envío de órdenes llegará en una fase posterior, primero en paper,
con límites de riesgo explícitos.

## 2026-11-26 — Almacenamiento en Parquet

Un archivo por símbolo y timeframe en `data/barras/`. Sin servidor (presupuesto bajo,
Windows nativo). DuckDB puede consultarlos directamente cuando haga falta SQL.
