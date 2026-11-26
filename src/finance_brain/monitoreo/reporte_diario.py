"""Reporte diario en Markdown de la cuenta Alpaca (posiciones y órdenes del día)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from ..ejecucion.alpaca_cuenta import CuentaAlpaca


def _tabla(df: pd.DataFrame) -> str:
    if df.empty:
        return "_(sin registros)_"
    cab = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "| " + " | ".join("---" for _ in df.columns) + " |"
    filas = ["| " + " | ".join("" if pd.isna(v) else str(v) for v in fila) + " |"
             for fila in df.itertuples(index=False)]
    return "\n".join([cab, sep, *filas])


def generar_reporte_diario(cuenta: CuentaAlpaca, carpeta: str | Path) -> Path:
    ahora = datetime.now(UTC)
    r = cuenta.resumen_cuenta()
    try:
        var_dia = float(r["equity"]) / float(r["last_equity"]) - 1
        var_txt = f"{var_dia:+.2%}"
    except (TypeError, ValueError, ZeroDivisionError):
        var_txt = "n/d"
    texto = "\n\n".join([
        f"# Reporte diario Alpaca ({'PAPER' if cuenta.paper else 'REAL'}) — {ahora:%Y-%m-%d}",
        f"Generado: {ahora:%Y-%m-%d %H:%M} UTC",
        "## Cuenta\n" + "\n".join(f"- **{k}**: {v}" for k, v in r.items())
        + f"\n- **variación del día**: {var_txt}",
        "## Posiciones\n" + _tabla(cuenta.posiciones()),
        "## Órdenes (últimas 24 h)\n" + _tabla(cuenta.ordenes(dias=1)),
    ])
    ruta = Path(carpeta) / "reportes" / f"reporte_{ahora:%Y-%m-%d}.md"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto + "\n", encoding="utf-8")
    return ruta
