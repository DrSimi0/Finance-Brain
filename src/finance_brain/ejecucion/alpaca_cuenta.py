"""Lectura de cuenta, posiciones y órdenes en Alpaca.

Deliberadamente NO incluye envío de órdenes: la estrategia en vivo del usuario
sigue funcionando donde está. Ejecutar desde aquí será una fase posterior,
con límites de riesgo explícitos y paper trading primero.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from ..config import Configuracion


class CuentaAlpaca:
    def __init__(self, config: Configuracion, cliente=None):
        if cliente is None:
            config.exigir_claves_alpaca()
            from alpaca.trading.client import TradingClient

            cliente = TradingClient(config.alpaca_api_key, config.alpaca_secret_key,
                                    paper=config.alpaca_paper)
        self._c = cliente
        self.paper = config.alpaca_paper

    def resumen_cuenta(self) -> dict:
        a = self._c.get_account()
        campos = ("equity", "last_equity", "cash", "buying_power", "portfolio_value", "status")
        return {k: getattr(a, k, None) for k in campos}

    def posiciones(self) -> pd.DataFrame:
        filas = [{
            "simbolo": p.symbol, "cantidad": float(p.qty),
            "precio_medio": float(p.avg_entry_price), "precio_actual": float(p.current_price or 0),
            "valor_mercado": float(p.market_value or 0), "pnl_no_realizado": float(p.unrealized_pl or 0),
        } for p in self._c.get_all_positions()]
        return pd.DataFrame(filas)

    def ordenes(self, dias: int = 1, limite: int = 500) -> pd.DataFrame:
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest

        desde = datetime.now(UTC) - timedelta(days=dias)
        req = GetOrdersRequest(status=QueryOrderStatus.ALL, after=desde, limit=limite)
        filas = [{
            "simbolo": o.symbol, "lado": str(getattr(o.side, "value", o.side)),
            "cantidad": o.qty, "ejecutada": o.filled_qty,
            "precio_ejecucion": o.filled_avg_price,
            "estado": str(getattr(o.status, "value", o.status)), "creada": o.created_at,
        } for o in self._c.get_orders(filter=req)]
        return pd.DataFrame(filas)
