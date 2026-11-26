"""Registro reproducible de experimentos: cada validación se guarda como JSON con
parámetros, costos, rango de datos y versiones de librerías."""

from __future__ import annotations

import json
import math
import platform
import subprocess
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path


def _version(pkg: str) -> str | None:
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return None


def _commit_git() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, timeout=5, check=True).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _a_json(o):
    if is_dataclass(o):
        return asdict(o)
    if hasattr(o, "isoformat"):
        return o.isoformat()
    if isinstance(o, float) and math.isnan(o):
        return None
    return str(o)


def guardar_experimento(carpeta: str | Path, nombre: str, contenido: dict) -> Path:
    ahora = datetime.now(UTC)
    registro = {
        "nombre": nombre,
        "fecha_utc": ahora.isoformat(),
        "git_commit": _commit_git(),
        "entorno": {
            "python": platform.python_version(),
            "sistema": platform.platform(),
            **{p: _version(p) for p in ("finance-brain", "vectorbt", "pandas", "numpy",
                                        "alpaca-py", "tradingagents")},
        },
        **contenido,
    }
    ruta = Path(carpeta) / "experimentos" / f"{ahora:%Y%m%dT%H%M%S}_{nombre}.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(registro, indent=2, ensure_ascii=False, default=_a_json),
                    encoding="utf-8")
    return ruta
