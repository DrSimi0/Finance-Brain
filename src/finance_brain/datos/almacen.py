"""Almacén local en Parquet: un archivo por (símbolo, timeframe).

Simple a propósito (presupuesto bajo, sin servidor). DuckDB puede leer estos
Parquet directamente cuando haga falta consultar en SQL.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class AlmacenParquet:
    def __init__(self, raiz: str | Path):
        self.raiz = Path(raiz)

    def _ruta(self, simbolo: str, timeframe: str) -> Path:
        return self.raiz / "barras" / timeframe / f"{simbolo.upper()}.parquet"

    def guardar(self, barras: pd.DataFrame, timeframe: str = "1Day") -> list[Path]:
        """Guarda barras (índice symbol, timestamp) fusionando con lo ya guardado."""
        rutas = []
        for simbolo, grupo in barras.groupby(level="symbol"):
            nuevo = grupo.droplevel("symbol")
            ruta = self._ruta(simbolo, timeframe)
            ruta.parent.mkdir(parents=True, exist_ok=True)
            if ruta.exists():
                previo = pd.read_parquet(ruta)
                nuevo = pd.concat([previo, nuevo])
                nuevo = nuevo[~nuevo.index.duplicated(keep="last")]
            nuevo.sort_index().to_parquet(ruta)
            rutas.append(ruta)
        return rutas

    def cargar(self, simbolo: str, timeframe: str = "1Day") -> pd.DataFrame:
        ruta = self._ruta(simbolo, timeframe)
        if not ruta.exists():
            raise FileNotFoundError(
                f"No hay datos de {simbolo} ({timeframe}) en {ruta}. "
                f"Descárgalos con: finance-brain datos descargar {simbolo}"
            )
        return pd.read_parquet(ruta)

    def simbolos(self, timeframe: str = "1Day") -> list[str]:
        carpeta = self.raiz / "barras" / timeframe
        return sorted(p.stem for p in carpeta.glob("*.parquet")) if carpeta.exists() else []
