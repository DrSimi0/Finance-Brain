"""Registro append-only de ideas propuestas por agentes y su evaluación prospectiva."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

# Dirección implícita de cada rating de TradingAgents (escala de 5 niveles).
DIRECCION = {"buy": 1.0, "overweight": 0.5, "hold": 0.0, "underweight": -0.5, "sell": -1.0}


@dataclass
class IdeaPropuesta:
    ticker: str
    fecha_analisis: str          # fecha "as of" que se pidió al agente (YYYY-MM-DD)
    rating: str                  # Buy/Overweight/Hold/Underweight/Sell/REVIEW
    decision: str = ""           # texto de la decisión final
    fuente: str = "tradingagents"
    modelo: str = ""
    creada_en: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    validacion: dict | None = None  # veredicto de una regla determinista asociada (opcional)

    @property
    def evaluable_prospectivamente(self) -> bool:
        """Solo si se analizó "hoy" (fecha_analisis >= fecha de registro).
        Un análisis de una fecha pasada está contaminado por look-ahead del LLM."""
        creada = pd.Timestamp(self.creada_en).tz_convert("UTC").date()
        return pd.Timestamp(self.fecha_analisis).date() >= creada

    @property
    def direccion(self) -> float | None:
        return DIRECCION.get(self.rating.strip().lower())


class RegistroIdeas:
    """Archivo JSONL: una idea por línea. Nunca se reescriben ideas pasadas."""

    def __init__(self, ruta: str | Path):
        self.ruta = Path(ruta)

    def agregar(self, idea: IdeaPropuesta) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self.ruta.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(idea), ensure_ascii=False) + "\n")

    def leer(self) -> list[IdeaPropuesta]:
        if not self.ruta.exists():
            return []
        with self.ruta.open(encoding="utf-8") as f:
            return [IdeaPropuesta(**json.loads(linea)) for linea in f if linea.strip()]


def evaluar_ideas_prospectivas(ideas: list[IdeaPropuesta], precios: dict[str, pd.DataFrame],
                               horizonte: int = 20) -> pd.DataFrame:
    """Retorno a `horizonte` barras desde la primera apertura POSTERIOR al registro.

    precios: {ticker: DataFrame con columnas open/close e índice temporal UTC}.
    Estados: evaluada | pendiente | contaminada (análisis histórico) | sin_rating | sin_datos.
    """
    filas = []
    for idea in ideas:
        fila = {"ticker": idea.ticker, "fecha_analisis": idea.fecha_analisis,
                "creada_en": idea.creada_en, "rating": idea.rating,
                "retorno": None, "retorno_con_signo": None}
        df = precios.get(idea.ticker)
        if not idea.evaluable_prospectivamente:
            fila["estado"] = "contaminada"
        elif idea.direccion is None:
            fila["estado"] = "sin_rating"
        elif df is None or df.empty:
            fila["estado"] = "sin_datos"
        else:
            idx = pd.DatetimeIndex(df.index)
            idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
            posteriores = df[idx > pd.Timestamp(idea.creada_en).tz_convert("UTC")]
            if len(posteriores) < horizonte + 1:
                fila["estado"] = "pendiente"
            else:
                entrada = float(posteriores["open"].iloc[0])
                salida = float(posteriores["close"].iloc[horizonte])
                ret = salida / entrada - 1
                fila.update(estado="evaluada", retorno=ret, retorno_con_signo=ret * idea.direccion)
        filas.append(fila)
    return pd.DataFrame(filas)
