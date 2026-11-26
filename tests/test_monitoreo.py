from datetime import UTC, datetime
from types import SimpleNamespace as NS

from finance_brain.config import Configuracion
from finance_brain.ejecucion import CuentaAlpaca
from finance_brain.monitoreo import generar_reporte_diario


class ClienteFalso:
    def get_account(self):
        return NS(equity="101000", last_equity="100000", cash="5000", buying_power="10000",
                  portfolio_value="101000", status="ACTIVE")

    def get_all_positions(self):
        return [NS(symbol="SPY", qty="10", avg_entry_price="500", current_price="510",
                   market_value="5100", unrealized_pl="100")]

    def get_orders(self, filter=None):
        return [NS(symbol="SPY", side=NS(value="buy"), qty="10", filled_qty="10",
                   filled_avg_price="500", status=NS(value="filled"),
                   created_at=datetime(2026, 11, 26, tzinfo=UTC))]


def test_reporte_diario(tmp_path):
    cuenta = CuentaAlpaca(Configuracion(), cliente=ClienteFalso())
    ruta = generar_reporte_diario(cuenta, tmp_path)
    texto = ruta.read_text(encoding="utf-8")
    assert "PAPER" in texto and "+1.00%" in texto and "| SPY |" in texto
