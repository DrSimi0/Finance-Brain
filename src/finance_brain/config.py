"""Configuración central leída de variables de entorno / archivo .env.

Los secretos nunca se escriben en código ni en el repo: se leen de `.env`
(ignorado por git). Ver `.env.example`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_VERDADERO = {"1", "true", "yes", "si", "sí", "on"}


def _bool(valor: str | None, defecto: bool) -> bool:
    if valor is None or valor.strip() == "":
        return defecto
    return valor.strip().lower() in _VERDADERO


def _float(valor: str | None, defecto: float) -> float:
    if valor is None or valor.strip() == "":
        return defecto
    return float(valor)


@dataclass(frozen=True)
class Configuracion:
    alpaca_api_key: str | None = field(default=None, repr=False)
    alpaca_secret_key: str | None = field(default=None, repr=False)
    alpaca_paper: bool = True
    alpaca_data_feed: str = "iex"
    data_dir: Path = Path("data")
    results_dir: Path = Path("resultados")
    fees: float = 0.0005
    slippage: float = 0.0005

    @property
    def tiene_claves_alpaca(self) -> bool:
        return bool(self.alpaca_api_key and self.alpaca_secret_key)

    def exigir_claves_alpaca(self) -> None:
        if not self.tiene_claves_alpaca:
            raise RuntimeError(
                "Faltan ALPACA_API_KEY / ALPACA_SECRET_KEY. Copia .env.example a .env "
                "y rellena tus claves (empieza por las de paper)."
            )


def cargar_configuracion(env_file: str | os.PathLike | None = ".env") -> Configuracion:
    """Carga `.env` (si existe) y construye la configuración.

    Las variables ya presentes en el entorno tienen prioridad sobre `.env`.
    """
    if env_file is not None and Path(env_file).exists():
        load_dotenv(env_file, override=False)
    e = os.environ.get
    return Configuracion(
        alpaca_api_key=e("ALPACA_API_KEY") or None,
        alpaca_secret_key=e("ALPACA_SECRET_KEY") or None,
        alpaca_paper=_bool(e("ALPACA_PAPER"), True),
        alpaca_data_feed=(e("ALPACA_DATA_FEED") or "iex").strip().lower(),
        data_dir=Path(e("FB_DATA_DIR") or "data"),
        results_dir=Path(e("FB_RESULTS_DIR") or "resultados"),
        fees=_float(e("FB_FEES"), 0.0005),
        slippage=_float(e("FB_SLIPPAGE"), 0.0005),
    )
