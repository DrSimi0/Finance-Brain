"""Puente hacia TradingAgents (TauricResearch, Apache-2.0), usado como dependencia.

Se fija la versión Python v0.7.1 (extra `[agentes]`). La API usada es la pública:
`TradingAgentsGraph(config=...).propagate(ticker, fecha) -> (estado_final, rating)`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .registro_ideas import IdeaPropuesta

_MSG_INSTALAR = (
    "TradingAgents no está instalado. Instálalo con:\n"
    '    pip install -e ".[agentes]"\n'
    "y configura el proveedor/clave del LLM en .env (ver .env.example)."
)


class PuenteTradingAgents:
    """Ejecuta el grafo multi-agente y devuelve una IdeaPropuesta.

    `grafo` permite inyectar un objeto con método `propagate` (tests / otros motores).
    """

    def __init__(self, overrides: dict[str, Any] | None = None, grafo=None, debug: bool = False):
        self._config: dict[str, Any] = {}
        if grafo is None:
            try:
                from tradingagents.default_config import DEFAULT_CONFIG
                from tradingagents.graph.trading_graph import TradingAgentsGraph
            except ImportError as exc:  # pragma: no cover - depende del entorno
                raise ImportError(_MSG_INSTALAR) from exc
            self._config = {**DEFAULT_CONFIG, **(overrides or {})}
            grafo = TradingAgentsGraph(debug=debug, config=self._config)
        self._grafo = grafo

    def proponer(self, ticker: str, fecha: str | None = None) -> IdeaPropuesta:
        fecha = fecha or date.today().isoformat()
        estado, rating = self._grafo.propagate(ticker.upper(), fecha)
        decision = ""
        if isinstance(estado, dict):
            decision = str(estado.get("final_trade_decision", ""))
        modelo = str(self._config.get("deep_think_llm", "")) if self._config else ""
        return IdeaPropuesta(ticker=ticker.upper(), fecha_analisis=fecha, rating=str(rating),
                             decision=decision, modelo=modelo)
