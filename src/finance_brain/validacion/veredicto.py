"""Criterios explícitos para decidir si una estrategia pasa a paper trading.

"APROBADA_PARA_PAPER" NO significa que la estrategia sea rentable: solo que no
fue descartada con estos datos y criterios. Significancia ≠ rentabilidad.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .walk_forward import ResultadoWalkForward


@dataclass(frozen=True)
class Criterios:
    min_operaciones_oos: int = 30
    sharpe_oos_min: float = 0.5
    max_drawdown_max: float = 0.30      # en valor absoluto
    ratio_degradacion_min: float = 0.3  # sharpe OOS medio / sharpe IS medio
    exigir_superar_benchmark: bool = False


@dataclass
class Veredicto:
    estado: str  # APROBADA_PARA_PAPER | RECHAZADA | EVIDENCIA_INSUFICIENTE
    razones: list[str] = field(default_factory=list)


def evaluar(res: ResultadoWalkForward, c: Criterios = Criterios()) -> Veredicto:
    m = res.metricas_oos
    if m.get("n_operaciones", 0) < c.min_operaciones_oos:
        return Veredicto("EVIDENCIA_INSUFICIENTE", [
            (f"{int(m.get('n_operaciones', 0))} operaciones OOS < {c.min_operaciones_oos}: "
             "muestra demasiado pequeña para concluir nada.")])
    fallos = []
    sh = m.get("sharpe", float("nan"))
    if math.isnan(sh) or sh < c.sharpe_oos_min:
        fallos.append(f"Sharpe OOS {sh:.2f} < {c.sharpe_oos_min}")
    dd = abs(m.get("max_drawdown", 0.0))
    if dd > c.max_drawdown_max:
        fallos.append(f"Max drawdown OOS {dd:.1%} > {c.max_drawdown_max:.0%}")
    rd = res.ratio_degradacion
    if math.isnan(rd) or rd < c.ratio_degradacion_min:
        fallos.append(f"Ratio de degradación IS→OOS {rd:.2f} < {c.ratio_degradacion_min} "
                      "(posible sobreajuste)")
    if c.exigir_superar_benchmark:
        bh = res.metricas_benchmark_oos.get("sharpe", float("nan"))
        if not math.isnan(bh) and not math.isnan(sh) and sh <= bh:
            fallos.append(f"No supera a comprar y mantener (Sharpe {sh:.2f} vs {bh:.2f})")
    if fallos:
        return Veredicto("RECHAZADA", fallos)
    return Veredicto("APROBADA_PARA_PAPER", [
        ("Pasa los criterios OOS con costos. Siguiente paso: paper trading y seguimiento; "
         f"recuerda que se probaron {res.n_combinaciones_probadas} combinaciones.")])
