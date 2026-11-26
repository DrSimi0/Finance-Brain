import numpy as np
import pandas as pd
import pytest

from finance_brain.investigacion import CATALOGO
from finance_brain.validacion import (
    Criterios,
    ModeloCostos,
    backtest,
    evaluar,
    particiones,
    walk_forward,
)


@pytest.mark.parametrize("nombre", list(CATALOGO))
def test_estrategias_son_causales(barras, nombre):
    """La señal en t no puede cambiar si se eliminan los datos posteriores a t."""
    est = CATALOGO[nombre]()
    params = est.combinaciones()[0]
    corte = 900
    e_full, x_full = est.senales(barras, **params)
    e_cut, x_cut = est.senales(barras.iloc[:corte], **params)
    pd.testing.assert_series_equal(e_full.iloc[:corte], e_cut, check_names=False)
    pd.testing.assert_series_equal(x_full.iloc[:corte], x_cut, check_names=False)


def test_ejecucion_en_barra_siguiente():
    """Una señal en la barra 5 debe ejecutarse a la apertura de la barra 6."""
    idx = pd.bdate_range("2024-01-01", periods=10, tz="UTC")
    close = pd.Series(np.arange(100, 110, dtype=float), index=idx)
    barras = pd.DataFrame({"open": close + 0.5, "high": close + 1, "low": close - 1,
                           "close": close, "volume": 1000}, index=idx)
    entradas = pd.Series(False, index=idx)
    entradas.iloc[5] = True
    res = backtest(barras, entradas, pd.Series(False, index=idx), ModeloCostos(0, 0))
    ordenes = res.portafolio.orders.records_readable
    assert ordenes["Timestamp"].iloc[0] == idx[6]
    assert ordenes["Price"].iloc[0] == pytest.approx(barras["open"].iloc[6])


def test_costos_reducen_el_resultado(barras):
    e, x = CATALOGO["reversion_rsi"]().senales(barras, periodo=2, sobreventa=10, salida=50)
    sin = backtest(barras, e, x, ModeloCostos(0, 0)).metricas["retorno_total"]
    con = backtest(barras, e, x, ModeloCostos(0.001, 0.001)).metricas["retorno_total"]
    assert con < sin


@pytest.mark.parametrize("anclado", [False, True])
def test_particiones_sin_solapamiento_y_oos_posterior(anclado):
    pares = particiones(1000, n_ventanas=4, frac_is=0.6, anclado=anclado, embargo=5)
    fin_oos_previo = -1
    for s_is, s_oos in pares:
        assert s_is.stop + 5 == s_oos.start          # embargo respetado
        assert s_oos.start > fin_oos_previo - 1        # OOS consecutivos sin solapar
        fin_oos_previo = s_oos.stop
    assert pares[-1][1].stop == 1000
    if anclado:
        assert all(s_is.start == 0 for s_is, _ in pares)


def test_particiones_datos_insuficientes():
    with pytest.raises(ValueError):
        particiones(50, n_ventanas=5)


def test_walk_forward_en_paseo_aleatorio_no_aprueba(barras):
    """Sobre ruido sin ventaja, el sistema no debe declarar éxito."""
    res = walk_forward(CATALOGO["cruce_medias"](), barras, n_ventanas=3, frac_is=0.7)
    assert len(res.ventanas) == 3
    assert res.n_combinaciones_probadas == len(CATALOGO["cruce_medias"]().combinaciones()) * 3
    assert evaluar(res, Criterios()).estado != "APROBADA_PARA_PAPER"
    for v in res.ventanas:
        assert v.oos_inicio > v.is_fin
