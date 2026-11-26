"""Línea de comandos: `finance-brain <departamento> ...`. Ejecuta `finance-brain -h`."""

from __future__ import annotations

import argparse
import contextlib
import sys

import numpy as np
import pandas as pd

from .config import cargar_configuracion


def _imprimir_metricas(titulo: str, m: dict) -> None:
    print(f"\n{titulo}")
    for k, v in m.items():
        if isinstance(v, float) and k in ("retorno_total", "cagr", "volatilidad", "max_drawdown",
                                          "tasa_acierto", "exposicion"):
            print(f"  {k:<16} {v:>10.2%}")
        elif isinstance(v, float):
            print(f"  {k:<16} {v:>10.2f}")
        else:
            print(f"  {k:<16} {v!s:>10}")


def _validar(barras, estrategia_nombre, args, cfg, etiqueta):
    from .experimentos import guardar_experimento
    from .investigacion import CATALOGO
    from .validacion import Criterios, ModeloCostos, evaluar, walk_forward

    if estrategia_nombre not in CATALOGO:
        sys.exit(f"Estrategia desconocida: {estrategia_nombre}. Opciones: {list(CATALOGO)}")
    estrategia = CATALOGO[estrategia_nombre]()
    costos = ModeloCostos(comision=cfg.fees, deslizamiento=cfg.slippage)
    res = walk_forward(estrategia, barras, costos, n_ventanas=args.ventanas,
                       frac_is=args.frac_is, anclado=args.anclado)
    criterios = Criterios()
    ver = evaluar(res, criterios)
    with pd.option_context("display.width", 140, "display.max_columns", 20):
        print(f"\nWalk-forward de '{estrategia.nombre}' sobre {etiqueta} "
              f"({barras.index[0].date()} → {barras.index[-1].date()}, {len(barras)} barras)")
        print(res.resumen().to_string(index=False))
    _imprimir_metricas("OOS combinado (con costos):", res.metricas_oos)
    _imprimir_metricas("Referencia comprar y mantener (mismos tramos OOS):",
                       res.metricas_benchmark_oos)
    print(f"\n  combinaciones probadas: {res.n_combinaciones_probadas}")
    print(f"  ratio degradación IS→OOS: {res.ratio_degradacion:.2f}")
    print(f"\nVEREDICTO: {ver.estado}")
    for r in ver.razones:
        print(f"  - {r}")
    ruta = guardar_experimento(cfg.results_dir, f"wf_{etiqueta}_{estrategia.nombre}", {
        "datos": {"etiqueta": etiqueta, "inicio": barras.index[0], "fin": barras.index[-1],
                  "barras": len(barras), "feed": cfg.alpaca_data_feed},
        "estrategia": estrategia.nombre, "grid": estrategia.grid,
        "costos": costos, "criterios": criterios,
        "walk_forward": {"ventanas": args.ventanas, "frac_is": args.frac_is,
                         "anclado": args.anclado},
        "resumen_ventanas": res.resumen().to_dict(orient="records"),
        "metricas_oos": res.metricas_oos, "benchmark_oos": res.metricas_benchmark_oos,
        "n_combinaciones_probadas": res.n_combinaciones_probadas,
        "ratio_degradacion": res.ratio_degradacion,
        "veredicto": ver,
    })
    print(f"\nExperimento guardado en {ruta}")
    return ver


def barras_sinteticas(n: int = 2520, semilla: int = 7) -> pd.DataFrame:
    """Paseo aleatorio sin ventaja real: una estrategia NO debería 'aprobar' aquí."""
    rng = np.random.default_rng(semilla)
    r = rng.normal(0.0003, 0.012, n)
    close = 100 * np.exp(np.cumsum(r))
    open_ = close * np.exp(rng.normal(0, 0.003, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.004, n)))
    idx = pd.bdate_range("2015-01-01", periods=n, tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.integers(1e5, 1e6, n)}, index=idx)


def cmd_demo(args, cfg):
    print("DEMO con datos sintéticos (paseo aleatorio, no requiere claves).")
    _validar(barras_sinteticas(), args.estrategia, args, cfg, "SINTETICO")


def cmd_descargar(args, cfg):
    from .datos import AlmacenParquet, revisar_barras
    from .datos.alpaca_datos import AlpacaDatos

    barras = AlpacaDatos(cfg).descargar_barras(args.simbolos, args.desde, args.hasta, args.timeframe)
    if barras.empty:
        sys.exit("Alpaca no devolvió datos. Revisa símbolos, fechas y el feed (ALPACA_DATA_FEED).")
    almacen = AlmacenParquet(cfg.data_dir)
    for ruta in almacen.guardar(barras, args.timeframe):
        print(f"Guardado: {ruta}")
    for simbolo in barras.index.get_level_values("symbol").unique():
        rep = revisar_barras(almacen.cargar(simbolo, args.timeframe))
        estado = "OK" if rep.ok else "; ".join(rep.problemas)
        print(f"Calidad {simbolo}: {rep.filas} filas — {estado}")


def cmd_validar(args, cfg):
    from .datos import AlmacenParquet

    barras = AlmacenParquet(cfg.data_dir).cargar(args.simbolo, args.timeframe)
    _validar(barras, args.estrategia, args, cfg, args.simbolo.upper())


def cmd_idea(args, cfg):
    from .agentes import RegistroIdeas
    from .agentes.tradingagents_puente import PuenteTradingAgents

    idea = PuenteTradingAgents(debug=args.debug).proponer(args.simbolo, args.fecha)
    if not idea.evaluable_prospectivamente:
        print("AVISO: fecha de análisis en el pasado. El LLM puede 'conocer' lo que pasó "
              "después; esta idea queda marcada como contaminada y no cuenta en la evaluación.")
    if args.validar:
        from .datos import AlmacenParquet

        barras = AlmacenParquet(cfg.data_dir).cargar(args.simbolo)
        ver = _validar(barras, args.validar, args, cfg, args.simbolo.upper())
        idea.validacion = {"regla": args.validar, "estado": ver.estado, "razones": ver.razones}
    RegistroIdeas(cfg.results_dir / "ideas.jsonl").agregar(idea)
    print(f"\nIdea registrada: {idea.ticker} {idea.fecha_analisis} → {idea.rating}")
    print(idea.decision[:2000])


def cmd_evaluar_ideas(args, cfg):
    from .agentes import RegistroIdeas, evaluar_ideas_prospectivas
    from .datos import AlmacenParquet

    ideas = RegistroIdeas(cfg.results_dir / "ideas.jsonl").leer()
    if not ideas:
        sys.exit("No hay ideas registradas todavía (usa `finance-brain idea TICKER`).")
    almacen = AlmacenParquet(cfg.data_dir)
    precios = {}
    for t in {i.ticker for i in ideas}:
        with contextlib.suppress(FileNotFoundError):
            precios[t] = almacen.cargar(t)
    tabla = evaluar_ideas_prospectivas(ideas, precios, args.horizonte)
    print(tabla.to_string(index=False))
    ev = tabla[tabla["estado"] == "evaluada"]
    if len(ev):
        print(f"\nIdeas evaluadas: {len(ev)} | acierto direccional: "
              f"{(ev['retorno_con_signo'] > 0).mean():.0%} | retorno con signo medio: "
              f"{ev['retorno_con_signo'].mean():+.2%}")
        if len(ev) < 30:
            print("Muestra pequeña (<30): no saques conclusiones todavía.")


def cmd_reporte(args, cfg):
    from .ejecucion import CuentaAlpaca
    from .monitoreo import generar_reporte_diario

    ruta = generar_reporte_diario(CuentaAlpaca(cfg), cfg.results_dir)
    print(ruta.read_text(encoding="utf-8"))
    print(f"\nGuardado en {ruta}")


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="finance-brain", description="Finance Lab — cerebro cuantitativo")
    sub = p.add_subparsers(dest="comando", required=True)

    def opciones_wf(sp):
        sp.add_argument("--estrategia", default="cruce_medias")
        sp.add_argument("--ventanas", type=int, default=5)
        sp.add_argument("--frac-is", type=float, default=0.7)
        sp.add_argument("--anclado", action="store_true", help="IS anclado al inicio")

    d = sub.add_parser("demo", help="Prueba la instalación con datos sintéticos")
    opciones_wf(d)
    d.set_defaults(func=cmd_demo)

    datos = sub.add_parser("datos", help="Departamento de Datos").add_subparsers(dest="sub", required=True)
    dd = datos.add_parser("descargar", help="Descarga barras de Alpaca a Parquet")
    dd.add_argument("simbolos", nargs="+")
    dd.add_argument("--desde", default="2016-01-01")
    dd.add_argument("--hasta", default=None)
    dd.add_argument("--timeframe", default="1Day")
    dd.set_defaults(func=cmd_descargar)

    v = sub.add_parser("validar", help="Walk-forward con costos de una estrategia del catálogo")
    v.add_argument("simbolo")
    v.add_argument("--timeframe", default="1Day")
    opciones_wf(v)
    v.set_defaults(func=cmd_validar)

    i = sub.add_parser("idea", help="Pide una idea a TradingAgents y la registra")
    i.add_argument("simbolo")
    i.add_argument("--fecha", default=None, help="YYYY-MM-DD (por defecto hoy)")
    i.add_argument("--validar", default=None, help="Regla del catálogo a validar en ese ticker")
    i.add_argument("--debug", action="store_true")
    i.add_argument("--ventanas", type=int, default=5)
    i.add_argument("--frac-is", type=float, default=0.7)
    i.add_argument("--anclado", action="store_true")
    i.set_defaults(func=cmd_idea)

    e = sub.add_parser("evaluar-ideas", help="Evaluación prospectiva de las ideas registradas")
    e.add_argument("--horizonte", type=int, default=20)
    e.set_defaults(func=cmd_evaluar_ideas)

    r = sub.add_parser("reporte", help="Reporte diario de la cuenta Alpaca (solo lectura)")
    r.set_defaults(func=cmd_reporte)
    return p


def main(argv: list[str] | None = None) -> None:
    args = construir_parser().parse_args(argv)
    args.func(args, cargar_configuracion())


if __name__ == "__main__":
    main()
