from types import SimpleNamespace

import pandas as pd

from finance_brain.config import Configuracion
from finance_brain.datos import AlmacenParquet, revisar_barras
from finance_brain.datos.alpaca_datos import AlpacaDatos


def _df_alpaca(barras, simbolo="SPY"):
    df = barras.copy()
    df.index = pd.MultiIndex.from_product([[simbolo], df.index], names=["symbol", "timestamp"])
    return df


def test_descarga_con_cliente_simulado(barras):
    capturado = {}

    class Falso:
        def get_stock_bars(self, req):
            capturado["req"] = req
            return SimpleNamespace(df=_df_alpaca(barras.iloc[::-1]))  # desordenado a propósito

    datos = AlpacaDatos(Configuracion(), cliente=Falso())
    df = datos.descargar_barras(["spy"], "2015-01-01", "2020-01-01")
    assert capturado["req"].symbol_or_symbols == ["SPY"]
    assert df.index.is_monotonic_increasing
    assert str(df.index.get_level_values("timestamp").tz) == "UTC"


def test_almacen_fusiona_sin_duplicar(tmp_path, barras):
    alm = AlmacenParquet(tmp_path)
    alm.guardar(_df_alpaca(barras.iloc[:800]))
    alm.guardar(_df_alpaca(barras.iloc[700:]))
    df = alm.cargar("SPY")
    assert len(df) == len(barras) and not df.index.duplicated().any()
    assert alm.simbolos() == ["SPY"]


def test_calidad_detecta_problemas(barras):
    assert revisar_barras(barras).ok
    malo = barras.copy()
    malo.iloc[10, malo.columns.get_loc("close")] = -1
    malo.iloc[20, malo.columns.get_loc("high")] = malo["low"].iloc[20] * 0.5
    rep = revisar_barras(malo)
    assert not rep.ok and any("<= 0" in p for p in rep.problemas)
    assert any("incoherentes" in p for p in rep.problemas)
