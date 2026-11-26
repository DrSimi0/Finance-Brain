"""Backtest con costos sobre vectorbt.

Regla anti look-ahead: una señal calculada con el cierre de la barra t se
ejecuta en la barra t+1 (por defecto a la APERTURA de t+1). Nunca se ejecuta en
la misma barra que la generó.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

DIAS_HABILES = 252


@dataclass(frozen=True)
class ModeloCostos:
    """Costos como fracción del nocional por operación (0.0005 = 5 pb)."""

    comision: float = 0.0005
    deslizamiento: float = 0.0005

    def __post_init__(self):
        if self.comision < 0 or self.deslizamiento < 0:
            raise ValueError("Los costos no pueden ser negativos")


@dataclass
class ResultadoBacktest:
    metricas: dict[str, float]
    retornos: pd.Series = field(repr=False)
    portafolio: object = field(default=None, repr=False)


def _alinear(barras: pd.DataFrame, s: pd.Series) -> pd.Series:
    return s.reindex(barras.index).fillna(False).astype(bool)


def backtest(
    barras: pd.DataFrame,
    entradas: pd.Series,
    salidas: pd.Series,
    costos: ModeloCostos = ModeloCostos(),
    ejecucion: str = "apertura_siguiente",
    capital: float = 100_000.0,
    freq: str = "1D",
) -> ResultadoBacktest:
    """Ejecuta un backtest solo-largos.

    ejecucion: "apertura_siguiente" (por defecto) o "cierre_siguiente".
    """
    import vectorbt as vbt

    if ejecucion not in ("apertura_siguiente", "cierre_siguiente"):
        raise ValueError("ejecucion debe ser 'apertura_siguiente' o 'cierre_siguiente'")
    ent = _alinear(barras, entradas).shift(1, fill_value=False)
    sal = _alinear(barras, salidas).shift(1, fill_value=False)
    precio = barras["open"] if ejecucion == "apertura_siguiente" else barras["close"]
    pf = vbt.Portfolio.from_signals(
        close=barras["close"],
        entries=ent,
        exits=sal,
        price=precio,
        fees=costos.comision,
        slippage=costos.deslizamiento,
        init_cash=capital,
        freq=freq,
    )
    retornos = pf.returns()
    m = metricas_de_retornos(retornos)
    m["n_operaciones"] = float(pf.trades.count())
    m["tasa_acierto"] = float(pf.trades.win_rate()) if m["n_operaciones"] > 0 else float("nan")
    m["exposicion"] = float((pf.assets() > 0).mean())
    return ResultadoBacktest(metricas=m, retornos=retornos, portafolio=pf)


def comprar_y_mantener(barras: pd.DataFrame, costos: ModeloCostos = ModeloCostos(),
                       freq: str = "1D") -> ResultadoBacktest:
    """Referencia: comprar en la primera apertura disponible y mantener."""
    entradas = pd.Series(False, index=barras.index)
    entradas.iloc[0] = True  # se ejecuta en la barra 1 (siguiente apertura)
    return backtest(barras, entradas, pd.Series(False, index=barras.index), costos, freq=freq)


def metricas_de_retornos(retornos: pd.Series, periodos_anio: int = DIAS_HABILES) -> dict[str, float]:
    r = retornos.dropna()
    if r.empty:
        return {k: float("nan") for k in
                ("retorno_total", "cagr", "volatilidad", "sharpe", "max_drawdown")}
    equity = (1 + r).cumprod()
    total = float(equity.iloc[-1] - 1)
    anios = len(r) / periodos_anio
    cagr = float(equity.iloc[-1] ** (1 / anios) - 1) if anios > 0 and equity.iloc[-1] > 0 else float("nan")
    std = float(r.std(ddof=1)) if len(r) > 1 else float("nan")
    vol = std * np.sqrt(periodos_anio) if not math.isnan(std) else float("nan")
    sharpe = float(r.mean() / std * np.sqrt(periodos_anio)) if not math.isnan(std) and std > 0 else float("nan")
    dd = float((equity / equity.cummax() - 1).min())
    return {"retorno_total": total, "cagr": cagr, "volatilidad": vol, "sharpe": sharpe,
            "max_drawdown": dd}
