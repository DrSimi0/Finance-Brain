from datetime import UTC, datetime, timedelta

import pandas as pd

from finance_brain.agentes import IdeaPropuesta, RegistroIdeas, evaluar_ideas_prospectivas
from finance_brain.agentes.tradingagents_puente import PuenteTradingAgents


class GrafoFalso:
    def propagate(self, ticker, fecha):
        return {"final_trade_decision": f"Rating: Buy para {ticker}"}, "Buy"


def test_puente_devuelve_idea_con_grafo_inyectado():
    idea = PuenteTradingAgents(grafo=GrafoFalso()).proponer("nvda")
    assert idea.ticker == "NVDA" and idea.rating == "Buy"
    assert "Rating: Buy" in idea.decision
    assert idea.evaluable_prospectivamente


def test_idea_historica_queda_contaminada():
    idea = PuenteTradingAgents(grafo=GrafoFalso()).proponer("NVDA", "2023-01-03")
    assert not idea.evaluable_prospectivamente


def test_registro_es_append_only(tmp_path):
    reg = RegistroIdeas(tmp_path / "ideas.jsonl")
    reg.agregar(IdeaPropuesta("AAA", "2026-01-01", "Buy"))
    reg.agregar(IdeaPropuesta("BBB", "2026-01-01", "Sell"))
    assert [i.ticker for i in reg.leer()] == ["AAA", "BBB"]


def test_evaluacion_usa_solo_precios_posteriores_al_registro():
    creada = datetime(2026, 1, 5, 15, 0, tzinfo=UTC)
    idx = pd.bdate_range("2026-01-01", periods=40, tz="UTC") + timedelta(hours=14, minutes=30)
    precios = pd.DataFrame({"open": range(100, 140), "close": range(101, 141)}, index=idx,
                           dtype=float)
    buena = IdeaPropuesta("AAA", "2026-01-05", "Buy", creada_en=creada.isoformat())
    venta = IdeaPropuesta("AAA", "2026-01-05", "Sell", creada_en=creada.isoformat())
    vieja = IdeaPropuesta("AAA", "2025-06-01", "Buy", creada_en=creada.isoformat())
    larga = IdeaPropuesta("AAA", "2026-01-05", "Buy", creada_en=creada.isoformat())
    t = evaluar_ideas_prospectivas([buena, venta, vieja], {"AAA": precios}, horizonte=5)
    # primera barra posterior a 2026-01-05 15:00 es la del 2026-01-06 (open=103)
    assert t.loc[0, "estado"] == "evaluada"
    assert t.loc[0, "retorno"] == (precios["close"].iloc[3 + 5] / 103.0 - 1)
    assert t.loc[1, "retorno_con_signo"] < 0
    assert t.loc[2, "estado"] == "contaminada"
    pend = evaluar_ideas_prospectivas([larga], {"AAA": precios}, horizonte=100)
    assert pend.loc[0, "estado"] == "pendiente"
