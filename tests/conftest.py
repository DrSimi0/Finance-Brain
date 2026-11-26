import pandas as pd
import pytest

from finance_brain.cli import barras_sinteticas


@pytest.fixture
def barras() -> pd.DataFrame:
    return barras_sinteticas(n=1500, semilla=3)


@pytest.fixture(autouse=True)
def _sin_entorno(monkeypatch):
    """Ningún test debe depender de claves reales."""
    for var in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY", "ALPACA_PAPER", "ALPACA_DATA_FEED",
                "FB_FEES", "FB_SLIPPAGE", "FB_DATA_DIR", "FB_RESULTS_DIR"):
        monkeypatch.delenv(var, raising=False)
