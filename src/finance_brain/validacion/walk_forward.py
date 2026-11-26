"""Walk-forward: optimizar en una ventana in-sample (IS) y medir fuera de muestra (OOS).

Las señales se calculan una vez sobre toda la serie; como las estrategias son
causales (la señal en t solo usa datos <= t), recortarlas a cada ventana no
introduce información futura. El test `test_estrategias_son_causales` lo verifica.

Importante: el número de combinaciones probadas se reporta porque, cuantas más
se prueban, más probable es encontrar algo "bueno" por azar (sobreajuste).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ..investigacion.estrategias import Estrategia
from .backtest import ModeloCostos, backtest, comprar_y_mantener, metricas_de_retornos


@dataclass
class Ventana:
    is_inicio: pd.Timestamp
    is_fin: pd.Timestamp
    oos_inicio: pd.Timestamp
    oos_fin: pd.Timestamp
    mejores_params: dict[str, Any] | None
    metricas_is: dict[str, float]
    metricas_oos: dict[str, float]


@dataclass
class ResultadoWalkForward:
    estrategia: str
    ventanas: list[Ventana]
    metricas_oos: dict[str, float]
    metricas_benchmark_oos: dict[str, float]
    n_combinaciones_probadas: int
    ratio_degradacion: float
    retornos_oos: pd.Series = field(repr=False)

    def resumen(self) -> pd.DataFrame:
        filas = []
        for v in self.ventanas:
            filas.append({
                "oos_inicio": v.oos_inicio.date(), "oos_fin": v.oos_fin.date(),
                "params": v.mejores_params,
                "sharpe_is": v.metricas_is.get("sharpe"),
                "sharpe_oos": v.metricas_oos.get("sharpe"),
                "ret_oos": v.metricas_oos.get("retorno_total"),
                "ops_oos": v.metricas_oos.get("n_operaciones"),
            })
        return pd.DataFrame(filas)


def particiones(n: int, n_ventanas: int = 5, frac_is: float = 0.7, anclado: bool = False,
                embargo: int = 0) -> list[tuple[slice, slice]]:
    """Devuelve pares (slice_IS, slice_OOS) por posición. OOS nunca se solapan entre sí
    y siempre empiezan después del fin de su IS (+ `embargo` barras)."""
    if not 0 < frac_is < 1:
        raise ValueError("frac_is debe estar entre 0 y 1")
    if n_ventanas < 1:
        raise ValueError("n_ventanas >= 1")
    largo_oos = int((n - embargo) / (n_ventanas + frac_is / (1 - frac_is)))
    largo_is = n - embargo - n_ventanas * largo_oos
    if largo_oos < 20 or largo_is < 20:
        raise ValueError(f"Datos insuficientes: {n} barras para {n_ventanas} ventanas")
    pares = []
    for k in range(n_ventanas):
        oos_ini = largo_is + embargo + k * largo_oos
        oos_fin = oos_ini + largo_oos if k < n_ventanas - 1 else n
        is_fin = oos_ini - embargo
        is_ini = 0 if anclado else is_fin - largo_is
        pares.append((slice(is_ini, is_fin), slice(oos_ini, oos_fin)))
    return pares


def _metrica(m: dict[str, float], nombre: str) -> float:
    v = m.get(nombre, float("nan"))
    return -np.inf if math.isnan(v) else v  # NaN -> peor posible


def walk_forward(
    estrategia: Estrategia,
    barras: pd.DataFrame,
    costos: ModeloCostos = ModeloCostos(),
    n_ventanas: int = 5,
    frac_is: float = 0.7,
    anclado: bool = False,
    embargo: int = 0,
    metrica: str = "sharpe",
    min_operaciones_is: int = 3,
    freq: str = "1D",
) -> ResultadoWalkForward:
    combos = estrategia.combinaciones()
    if not combos:
        raise ValueError("La estrategia no tiene combinaciones válidas de parámetros")
    senales = {i: estrategia.senales(barras, **c) for i, c in enumerate(combos)}
    ventanas: list[Ventana] = []
    trozos_oos, trozos_bh = [], []

    for s_is, s_oos in particiones(len(barras), n_ventanas, frac_is, anclado, embargo):
        b_is, b_oos = barras.iloc[s_is], barras.iloc[s_oos]
        mejor, mejor_val, mejor_m = None, -np.inf, {}
        for i, _c in enumerate(combos):
            e, x = senales[i]
            r = backtest(b_is, e.iloc[s_is], x.iloc[s_is], costos, freq=freq)
            if r.metricas["n_operaciones"] < min_operaciones_is:
                continue
            val = _metrica(r.metricas, metrica)
            if val > mejor_val:
                mejor, mejor_val, mejor_m = i, val, r.metricas
        if mejor is None:
            m_oos = {"retorno_total": 0.0, "sharpe": float("nan"), "n_operaciones": 0.0}
            r_oos = pd.Series(0.0, index=b_oos.index)
        else:
            e, x = senales[mejor]
            res = backtest(b_oos, e.iloc[s_oos], x.iloc[s_oos], costos, freq=freq)
            m_oos, r_oos = res.metricas, res.retornos
        trozos_oos.append(r_oos)
        trozos_bh.append(comprar_y_mantener(b_oos, costos, freq=freq).retornos)
        ventanas.append(Ventana(
            is_inicio=b_is.index[0], is_fin=b_is.index[-1],
            oos_inicio=b_oos.index[0], oos_fin=b_oos.index[-1],
            mejores_params=combos[mejor] if mejor is not None else None,
            metricas_is=mejor_m, metricas_oos=m_oos,
        ))

    retornos_oos = pd.concat(trozos_oos)
    m_total = metricas_de_retornos(retornos_oos)
    m_total["n_operaciones"] = float(sum(v.metricas_oos.get("n_operaciones", 0) for v in ventanas))
    sh_is = [v.metricas_is.get("sharpe") for v in ventanas if v.metricas_is]
    sh_oos = [v.metricas_oos.get("sharpe") for v in ventanas if v.metricas_is]
    sh_is = [s for s in sh_is if s is not None and not math.isnan(s)]
    sh_oos = [s for s in sh_oos if s is not None and not math.isnan(s)]
    media_is = float(np.mean(sh_is)) if sh_is else float("nan")
    ratio = float(np.mean(sh_oos) / media_is) if sh_oos and media_is and media_is > 0 else float("nan")
    return ResultadoWalkForward(
        estrategia=estrategia.nombre,
        ventanas=ventanas,
        metricas_oos=m_total,
        metricas_benchmark_oos=metricas_de_retornos(pd.concat(trozos_bh)),
        n_combinaciones_probadas=len(combos) * len(ventanas),
        ratio_degradacion=ratio,
        retornos_oos=retornos_oos,
    )
