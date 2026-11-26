"""Descarga de barras históricas de acciones con alpaca-py.

Notas de rigor:
- `adjustment="all"` ajusta por splits y dividendos. El ajuste es retroactivo
  (usa eventos corporativos posteriores), lo cual es estándar para medir
  retornos, pero los NIVELES de precio ajustados no son los que se veían en
  su día: no usar umbrales de precio absolutos sobre series ajustadas.
- Sesgo de supervivencia: si eliges hoy un universo de tickers "que existen",
  el backtest ignora las empresas que desaparecieron. Define el universo con
  una fecha de corte (point-in-time) y documenta de dónde sale.
- El feed `iex` es gratuito pero solo refleja el volumen negociado en IEX.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

import pandas as pd

from ..config import Configuracion

_TIMEFRAMES = {"1Day": ("Day", 1), "1Hour": ("Hour", 1), "15Min": ("Minute", 15),
               "5Min": ("Minute", 5), "1Min": ("Minute", 1)}


class AlpacaDatos:
    """Cliente de datos históricos. `cliente` se puede inyectar (útil en tests)."""

    def __init__(self, config: Configuracion, cliente=None):
        self.config = config
        if cliente is None:
            config.exigir_claves_alpaca()
            from alpaca.data.historical import StockHistoricalDataClient

            cliente = StockHistoricalDataClient(config.alpaca_api_key, config.alpaca_secret_key)
        self._cliente = cliente

    def descargar_barras(
        self,
        simbolos: Iterable[str],
        inicio: datetime | str,
        fin: datetime | str | None = None,
        timeframe: str = "1Day",
        ajuste: str = "all",
    ) -> pd.DataFrame:
        """Devuelve un DataFrame con índice (symbol, timestamp) en UTC y columnas OHLCV."""
        from alpaca.data.enums import Adjustment, DataFeed
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

        if timeframe not in _TIMEFRAMES:
            raise ValueError(f"timeframe no soportado: {timeframe}. Opciones: {list(_TIMEFRAMES)}")
        unidad, cantidad = _TIMEFRAMES[timeframe]
        solicitud = StockBarsRequest(
            symbol_or_symbols=[s.upper() for s in simbolos],
            timeframe=TimeFrame(cantidad, getattr(TimeFrameUnit, unidad)),
            start=pd.Timestamp(inicio).to_pydatetime(),
            end=pd.Timestamp(fin).to_pydatetime() if fin is not None else None,
            adjustment=Adjustment(ajuste),
            feed=DataFeed(self.config.alpaca_data_feed),
        )
        df = self._cliente.get_stock_bars(solicitud).df
        return normalizar_barras(df)


def normalizar_barras(df: pd.DataFrame) -> pd.DataFrame:
    """Asegura índice (symbol, timestamp) UTC ordenado y sin duplicados."""
    if df.empty:
        return df
    if not isinstance(df.index, pd.MultiIndex):
        raise TypeError("Se esperaba índice MultiIndex (symbol, timestamp)")
    df = df.copy()
    simbolos = df.index.get_level_values(0)
    tiempos = pd.to_datetime(df.index.get_level_values(1), utc=True)
    df.index = pd.MultiIndex.from_arrays([simbolos, tiempos], names=["symbol", "timestamp"])
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df
