"""Controles básicos de calidad de datos antes de investigar."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ReporteCalidad:
    filas: int
    problemas: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problemas


def revisar_barras(df: pd.DataFrame, max_hueco_dias: int = 5) -> ReporteCalidad:
    """Revisa un DataFrame OHLCV de un símbolo (índice temporal)."""
    rep = ReporteCalidad(filas=len(df))
    if df.empty:
        rep.problemas.append("sin datos")
        return rep
    faltan = {"open", "high", "low", "close", "volume"} - set(df.columns)
    if faltan:
        rep.problemas.append(f"faltan columnas: {sorted(faltan)}")
        return rep
    if not df.index.is_monotonic_increasing:
        rep.problemas.append("índice no ordenado")
    if df.index.duplicated().any():
        rep.problemas.append(f"{int(df.index.duplicated().sum())} timestamps duplicados")
    nulos = int(df[["open", "high", "low", "close"]].isna().sum().sum())
    if nulos:
        rep.problemas.append(f"{nulos} precios nulos")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        rep.problemas.append("precios <= 0")
    incoherentes = (df["high"] < df[["open", "close", "low"]].max(axis=1)) | (
        df["low"] > df[["open", "close", "high"]].min(axis=1)
    )
    if incoherentes.any():
        rep.problemas.append(f"{int(incoherentes.sum())} barras con high/low incoherentes")
    if len(df) > 1:
        huecos = pd.Series(df.index).diff().dt.days
        grandes = int((huecos > max_hueco_dias).sum())
        if grandes:
            rep.problemas.append(f"{grandes} huecos de más de {max_hueco_dias} días")
    return rep
