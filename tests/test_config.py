import pytest

from finance_brain.config import cargar_configuracion


def test_por_defecto_paper_y_sin_claves(tmp_path):
    cfg = cargar_configuracion(tmp_path / "no_existe.env")
    assert cfg.alpaca_paper is True
    assert not cfg.tiene_claves_alpaca
    with pytest.raises(RuntimeError):
        cfg.exigir_claves_alpaca()


def test_lee_env_y_no_muestra_secretos(tmp_path):
    env = tmp_path / ".env"
    env.write_text("ALPACA_API_KEY=clave\nALPACA_SECRET_KEY=secreto\nALPACA_PAPER=false\nFB_FEES=0.001\n")
    cfg = cargar_configuracion(env)
    assert cfg.tiene_claves_alpaca and cfg.alpaca_paper is False and cfg.fees == 0.001
    assert "secreto" not in repr(cfg) and "clave" not in repr(cfg)


def test_env_example_no_tiene_valores_de_claves():
    from pathlib import Path

    texto = (Path(__file__).parents[1] / ".env.example").read_text(encoding="utf-8")
    for linea in texto.splitlines():
        if linea.endswith("_KEY=") or "KEY=" not in linea:
            continue
        pytest.fail(f".env.example contiene un valor de clave: {linea}")
