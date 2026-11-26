# Finance Brain

El "cerebro" de **Finance Lab**: un laboratorio cuantitativo organizado como una firma, por
departamentos, donde los agentes de IA **proponen** ideas y un motor estadístico las
**valida** (o las descarta). Todo en Python, instalable con `pip` en Windows, sin WSL ni Docker.

| Departamento | Carpeta | Qué hace | Librería base |
| --- | --- | --- | --- |
| Datos | `src/finance_brain/datos/` | Descarga barras de Alpaca, las guarda en Parquet y revisa su calidad | [alpaca-py](https://github.com/alpacahq/alpaca-py) |
| Investigación | `src/finance_brain/investigacion/` | Estrategias deterministas y causales (catálogo) | pandas |
| Riesgo / Validación | `src/finance_brain/validacion/` | Backtest con costos, walk-forward IS→OOS y veredicto | [vectorbt](https://github.com/polakowo/vectorbt) |
| Agentes IA | `src/finance_brain/agentes/` | Pide análisis multi-agente y registra la idea para evaluarla a futuro | [TradingAgents](https://github.com/TauricResearch/TradingAgents) v0.7.1 |
| Ejecución | `src/finance_brain/ejecucion/` | Lee cuenta, posiciones y órdenes de Alpaca (**solo lectura**) | alpaca-py |
| Monitoreo | `src/finance_brain/monitoreo/` | Reporte diario en Markdown | — |

Las librerías externas se usan como **dependencias** (no se copia su código). Detalles y
motivos en [docs/arquitectura.md](docs/arquitectura.md) y [docs/decisiones.md](docs/decisiones.md).

> **Aviso importante sobre TradingAgents.** El 24-nov-2026 salió TradingAgents 1.0, que ya
> no es una librería de Python: es una app de terminal en Node sin versión para Windows. Por
> eso aquí se fija la **v0.7.1**, la última en Python. Ver [docs/decisiones.md](docs/decisiones.md).

---

## Instalación en Windows (paso a paso)

Todo se hace en **PowerShell** (botón Inicio → escribe "PowerShell").

### 1. Instala Python 3.12 y Git (solo la primera vez)

```powershell
winget install Python.Python.3.12
winget install Git.Git
```

Cierra y vuelve a abrir PowerShell para que reconozca los comandos. Comprueba:

```powershell
py -3.12 --version
git --version
```

> Se recomienda Python **3.12**: vectorbt depende de numba, que tiene instaladores listos
> para esa versión. 3.11 y 3.13 también deberían funcionar.

### 2. Descarga el repo

```powershell
cd $HOME
git clone https://github.com/DrSimi0/Finance-Brain.git
cd Finance-Brain
```

### 3. Instala todo con un comando

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_windows.ps1
```

Con la capa de agentes de IA (descarga más paquetes; necesita Git):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_windows.ps1 -ConAgentes
```

El script crea un entorno virtual `.venv`, instala las dependencias, crea tu `.env` a partir
de `.env.example`, ejecuta los tests y una demo con datos sintéticos.

<details>
<summary>Instalación manual (lo mismo que hace el script)</summary>

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # si da error: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install --upgrade pip
pip install -e ".[dev]"               # núcleo: datos + validación + tests
pip install -e ".[agentes]"           # opcional: TradingAgents
Copy-Item .env.example .env
python -m pytest
finance-brain demo
```
</details>

### 4. Pon tus claves

```powershell
notepad .env
```

Rellena `ALPACA_API_KEY` y `ALPACA_SECRET_KEY` (empieza con las de **paper**,
`ALPACA_PAPER=true`). Si vas a usar agentes, elige proveedor del LLM y pon su clave.
**`.env` nunca se sube a GitHub** (está en `.gitignore`).

### 5. Cada vez que abras una terminal nueva

```powershell
cd $HOME\Finance-Brain
.\.venv\Scripts\Activate.ps1
```

---

## Uso

```powershell
# Probar que todo funciona (no necesita claves)
finance-brain demo

# Datos: descargar barras diarias desde 2016 y guardarlas en data/
finance-brain datos descargar SPY QQQ AAPL --desde 2016-01-01

# Validación: walk-forward con costos de una estrategia del catálogo
finance-brain validar SPY --estrategia cruce_medias --ventanas 5 --frac-is 0.7
finance-brain validar QQQ --estrategia reversion_rsi

# Agentes: pedir una idea a TradingAgents (hoy) y registrarla
finance-brain idea NVDA
finance-brain idea NVDA --validar cruce_medias   # además valida una regla en ese ticker

# Evaluar a futuro las ideas registradas (retorno a 20 barras tras el registro)
finance-brain evaluar-ideas --horizonte 20

# Monitoreo: reporte diario de tu cuenta Alpaca (solo lectura)
finance-brain reporte
```

Cada validación imprime las ventanas IS/OOS, las métricas OOS con costos, una referencia de
comprar y mantener en los mismos tramos y un **veredicto**:

- `EVIDENCIA_INSUFICIENTE`: muy pocas operaciones fuera de muestra para concluir.
- `RECHAZADA`: no cumple los criterios (Sharpe OOS, drawdown, degradación IS→OOS).
- `APROBADA_PARA_PAPER`: no se pudo descartar; el siguiente paso es paper trading.
  **No significa que sea rentable.**

Además guarda un JSON reproducible en `resultados/experimentos/` (datos usados, parámetros,
costos, versiones de librerías y commit de git).

### Ejemplo real de la demo (paseo aleatorio, sin ventaja por construcción)

```
OOS combinado (con costos):  retorno_total 5.34%  sharpe 0.12  max_drawdown -25.68%  n_operaciones 18
Referencia comprar y mantener: retorno_total 67.84%  sharpe 0.49
combinaciones probadas: 40 | ratio degradación IS→OOS: 0.45
VEREDICTO: EVIDENCIA_INSUFICIENTE
```

Es el comportamiento esperado: sobre ruido, el sistema no debe declarar éxito.

---

## Rigor: qué protege el código y qué no

- **Look-ahead**: las señales se ejecutan en la apertura de la barra siguiente; un test
  verifica que cada estrategia es causal (truncar el futuro no cambia el pasado).
- **LLM**: sus decisiones no se backtestean (el modelo ya "vio" el futuro de cualquier fecha
  pasada). Se registran y se evalúan solo con precios posteriores. Un análisis con fecha
  pasada queda marcado como *contaminado*.
- **Costos**: comisión y deslizamiento siempre aplicados (`FB_FEES`, `FB_SLIPPAGE`).
- **Sobreajuste**: walk-forward, ratio de degradación y número de combinaciones probadas.
- **Supervivencia**: no se resuelve automáticamente. Fija tu universo de tickers con una
  fecha de corte y documenta de dónde sale.
- Limitaciones conocidas en [docs/arquitectura.md](docs/arquitectura.md#limitaciones-conocidas-honestas).

## Añadir una estrategia

1. Crea una clase en `src/finance_brain/investigacion/estrategias.py` que herede de
   `Estrategia`, con `nombre`, `grid` y `senales()` (solo datos hasta t).
2. Regístrala en `CATALOGO`.
3. `python -m pytest` comprobará automáticamente que es causal.
4. `finance-brain validar TICKER --estrategia tu_nombre`.

## Tests

```powershell
python -m pytest
```

Se ejecutan también en GitHub Actions en Windows y Ubuntu (`.github/workflows/tests.yml`).

## Próximas fases

- Ejecución en paper desde aquí, con límites de riesgo.
- Seguimiento de la estrategia en vivo de Alpaca en el reporte diario.
- NinjaTrader 8 (monitoreo) y futuros NQ.
- Agentes por departamento orquestando estos módulos.
