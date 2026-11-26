"""Estrategias de ejemplo.

Contrato: `senales(barras, **params)` devuelve (entradas, salidas) booleanas
alineadas con `barras.index`, donde la señal en t usa SOLO información
disponible al cierre de t. El motor de validación se encarga de ejecutarlas en
la barra siguiente (nunca en la misma barra que las generó).

Para añadir una estrategia: hereda de `Estrategia`, define `nombre`, `grid`
(rejilla de parámetros para walk-forward) y `senales`; regístrala en CATALOGO.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

import pandas as pd


class Estrategia(ABC):
    nombre: str = "base"
    grid: ClassVar[dict[str, list[Any]]] = {}

    @abstractmethod
    def senales(self, barras: pd.DataFrame, **params) -> tuple[pd.Series, pd.Series]:
        ...

    def combinaciones(self) -> list[dict[str, Any]]:
        """Producto cartesiano de la rejilla, filtrando combinaciones inválidas."""
        from itertools import product

        claves = list(self.grid)
        combos = [dict(zip(claves, vals)) for vals in product(*self.grid.values())]
        return [c for c in combos if self.valida(**c)]

    def valida(self, **params) -> bool:
        return True


class CruceMedias(Estrategia):
    """Largo cuando la media rápida está por encima de la lenta."""

    nombre = "cruce_medias"
    grid: ClassVar[dict[str, list[Any]]] = {"rapida": [10, 20, 50], "lenta": [50, 100, 200]}

    def valida(self, rapida: int, lenta: int) -> bool:
        return rapida < lenta

    def senales(self, barras: pd.DataFrame, rapida: int = 20, lenta: int = 100):
        c = barras["close"]
        mr = c.rolling(rapida, min_periods=rapida).mean()
        ml = c.rolling(lenta, min_periods=lenta).mean()
        arriba = (mr > ml) & ml.notna()
        entradas = arriba & ~arriba.shift(1, fill_value=False)
        salidas = ~arriba & arriba.shift(1, fill_value=False)
        return entradas, salidas


class ReversionRSI(Estrategia):
    """Compra cuando el RSI cae bajo `sobreventa`; sale cuando supera `salida`."""

    nombre = "reversion_rsi"
    grid: ClassVar[dict[str, list[Any]]] = {"periodo": [2, 5, 14], "sobreventa": [10, 20, 30], "salida": [50, 70]}

    def senales(self, barras: pd.DataFrame, periodo: int = 14, sobreventa: float = 30,
                salida: float = 50):
        rsi = rsi_wilder(barras["close"], periodo)
        entradas = (rsi < sobreventa) & (rsi.shift(1) >= sobreventa)
        salidas = (rsi > salida) & (rsi.shift(1) <= salida)
        return entradas.fillna(False), salidas.fillna(False)


def rsi_wilder(close: pd.Series, periodo: int) -> pd.Series:
    """RSI de Wilder, causal (solo usa datos hasta t)."""
    delta = close.diff()
    subida = delta.clip(lower=0).ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()
    bajada = (-delta.clip(upper=0)).ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()
    rs = subida / bajada
    return 100 - 100 / (1 + rs)


CATALOGO: dict[str, type[Estrategia]] = {
    CruceMedias.nombre: CruceMedias,
    ReversionRSI.nombre: ReversionRSI,
}
