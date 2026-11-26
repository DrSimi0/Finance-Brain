"""Finance Brain: laboratorio cuantitativo organizado por departamentos.

Departamentos (subpaquetes):
- datos:         descarga, almacenamiento y control de calidad de datos (alpaca-py).
- investigacion: estrategias deterministas y causales (generan señales).
- validacion:    riesgo y validación: backtest con costos, OOS, walk-forward (vectorbt).
- agentes:       capa de IA (TradingAgents) que PROPONE ideas; nunca las valida.
- ejecucion:     conexión a la cuenta Alpaca (solo lectura en esta versión).
- monitoreo:     reportes diarios.
"""

__version__ = "0.1.0"
