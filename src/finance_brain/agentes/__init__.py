"""Capa de agentes IA (TradingAgents). PROPONE ideas; la validación es de otro departamento.

Por qué las decisiones del LLM no se backtestean: el modelo fue entrenado con
datos que incluyen el "futuro" de cualquier fecha histórica que le pidas
analizar. Un backtest de sus decisiones pasadas tiene look-ahead imposible de
eliminar. Solo se pueden evaluar de forma PROSPECTIVA: registrar la idea hoy y
medirla con precios posteriores a la fecha de registro (ver registro_ideas.py).
"""

from .registro_ideas import IdeaPropuesta, RegistroIdeas, evaluar_ideas_prospectivas

__all__ = ["IdeaPropuesta", "RegistroIdeas", "evaluar_ideas_prospectivas"]
