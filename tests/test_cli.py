import json

from finance_brain.cli import main


def test_demo_guarda_experimento_reproducible(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FB_RESULTS_DIR", str(tmp_path))
    main(["demo", "--ventanas", "3"])
    salida = capsys.readouterr().out
    assert "VEREDICTO" in salida
    archivos = list((tmp_path / "experimentos").glob("*.json"))
    assert len(archivos) == 1
    reg = json.loads(archivos[0].read_text(encoding="utf-8"))
    for clave in ("entorno", "costos", "grid", "metricas_oos", "n_combinaciones_probadas", "veredicto"):
        assert clave in reg
