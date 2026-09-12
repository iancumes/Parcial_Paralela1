#!/usr/bin/env python3
"""
Calcula speedup y eficiencia a partir de los tiempos crudos del barrido y
genera las figuras del reporte.

Entradas : resultados_<etiqueta>/metricas_crudas_matrices.csv
           resultados_<etiqueta>/metricas_crudas_riemann.csv
Salidas  : resultados_<etiqueta>/metricas_{matrices,riemann}.csv
           img_<etiqueta>/{matrices,riemann}_*.png

En AMBOS problemas se reportan DOS speedups, porque el pragma cambia lo que gcc
puede optimizar y la version paralela con 1 hilo no equivale al secuencial:

  - matrices: el pragma INHIBE la vectorizacion SIMD del ciclo secuencial, asi
    que el paralelo con 1 hilo arranca ~2.4x mas lento.
  - riemann : al reves. reduction(+:) autoriza reasociar la suma, lo que HABILITA
    una vectorizacion que el secuencial tiene prohibida (la suma flotante no es
    asociativa), asi que el paralelo con 1 hilo arranca ~1.4x mas rapido.

Medir contra el secuencial da el speedup formal (contra el mejor algoritmo
serial); medir contra el paralelo con 1 hilo aisla la escalabilidad de OpenMP.
La brecha entre ambas curvas es el efecto de la vectorizacion, en un sentido o
en el otro.
"""
import argparse
import getpass
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, NullFormatter, NullLocator

RAIZ = Path(__file__).resolve().parent.parent

# Las salidas se separan por etiqueta para que los tres integrantes puedan
# medir en su propia maquina sin pisarse los resultados. Prioridad:
#   --etiqueta  >  $ETIQUETA  >  usuario del sistema
RESULTADOS = IMG = None  # se resuelven en main()


def resolver_rutas(etiqueta):
    global RESULTADOS, IMG
    RESULTADOS = RAIZ / f"resultados_{etiqueta}"
    IMG = RAIZ / f"img_{etiqueta}"


def crudas(problema):
    return RESULTADOS / f"metricas_crudas_{problema}.csv"


def resumen_csv(problema):
    return RESULTADOS / f"metricas_{problema}.csv"

# Cada integrante puede indicar la topologia de su maquina sin modificar el
# script. Se conserva 8 como valor predeterminado por compatibilidad con las
# mediciones originales de Ricardo.
NUCLEOS_FISICOS = int(os.environ.get("NUCLEOS_FISICOS", "8"))

# ------------------------------------------------------------------- estilo
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_MUTE = "#898781"
REJILLA = "#e1e0d9"
EJE = "#c3c2b7"

# El tamano de la matriz es una magnitud ordenada, no categorias sueltas:
# rampa de un solo tono, claro -> oscuro (validada con validate_palette.js
# --ordinal: monotona, saltos de L suficientes, extremo claro sobre 2:1).
RAMPA = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
RAMPA3 = ["#86b6ef", "#2a78d6", "#104281"]   # misma rampa, 3 pasos
MARCAS = ["o", "s", "^", "D"]
NARANJA = "#eb6834"  # slot categorico 2: el secuencial, que no es parte de la rampa

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE,
    "axes.facecolor": SUPERFICIE,
    "savefig.facecolor": SUPERFICIE,
    "font.size": 10,
    "text.color": TINTA,
    "axes.labelcolor": TINTA_2,
    "axes.edgecolor": EJE,
    "xtick.color": TINTA_MUTE,
    "ytick.color": TINTA_MUTE,
    "xtick.labelcolor": TINTA_2,
    "ytick.labelcolor": TINTA_2,
    "axes.linewidth": 1.0,
    "lines.linewidth": 2.0,
    "lines.solid_capstyle": "round",
    "lines.solid_joinstyle": "round",
})

ESTILO_MARCA = dict(markersize=5.5, markeredgecolor=SUPERFICIE, markeredgewidth=1.2)


def entero(v, _pos=None):
    return f"{v:g}"


def preparar(ax, titulo=None):
    ax.set_axisbelow(True)
    ax.grid(True, color=REJILLA, linewidth=1.0, linestyle="-")
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    if titulo:
        ax.set_title(titulo, color=TINTA, fontsize=11, pad=10, loc="left")


def eje_hilos(ax, hilos):
    ax.set_xscale("log", base=2)
    ax.set_xticks(hilos)
    ax.xaxis.set_major_formatter(FuncFormatter(entero))
    ax.set_xlabel("Hilos")
    ax.axvline(NUCLEOS_FISICOS, color=EJE, linewidth=1.0, linestyle=(0, (2, 3)), zorder=1)


def colocar_etiquetas(ax, items, separacion=11.0):
    """Etiquetas directas en el extremo de cada serie, separadas si se enciman.

    La tinta es de texto, nunca el color de la serie: la identidad la carga la
    marca al lado. Son ademas el 'relief' que exige el paso mas claro de la
    rampa, que queda por debajo de 3:1 contra la superficie.

    Dos series pueden terminar casi en el mismo valor (a 16 hilos, n=500 y
    n=2000 quedan a 0.1x de diferencia), asi que las posiciones se calculan en
    coordenadas de pantalla y se empujan hacia arriba hasta dejar `separacion`
    puntos entre etiquetas consecutivas.
    """
    if not items:
        return
    ppp = ax.figure.dpi / 72.0  # pixeles por punto

    colocados = sorted(
        ((ax.transData.transform((x, y))[1], x, y, texto) for x, y, texto in items),
        key=lambda t: t[0],
    )

    previo = None
    for i, (y_px, x, y, texto) in enumerate(colocados):
        destino = y_px if previo is None else max(y_px, previo + separacion * ppp)
        previo = destino
        ax.annotate(
            texto, xy=(x, y), xytext=(7, (destino - y_px) / ppp),
            textcoords="offset points", va="center", ha="left",
            fontsize=8.5, color=TINTA_2, clip_on=False,
        )


def leyenda_figura(fig, handles, etiquetas, y=0.885, ncol=None):
    fig.legend(
        handles, etiquetas, loc="upper center", bbox_to_anchor=(0.5, y),
        ncol=ncol or len(etiquetas), frameon=False, handlelength=1.8,
        columnspacing=1.6, fontsize=9, labelcolor=TINTA_2,
    )


def guardar(fig, nombre):
    fig.savefig(IMG / nombre, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {IMG.name}/{nombre}")


# --------------------------------------------------------------------- datos
# El minimo, no el promedio: los tiempos varian ~25% entre corridas identicas
# por turbo y scheduling del SO. El minimo es la estimacion menos contaminada
# por ruido externo al programa.

def derivar(t_sec, t_par_1, t_par, p):
    """Las dos referencias de speedup y sus eficiencias."""
    speedup_real = t_sec / t_par
    speedup_omp = t_par_1 / t_par
    return {
        "t_sec": round(t_sec, 6), "t_par": round(t_par, 6),
        "speedup_real": round(speedup_real, 4),
        "speedup_omp": round(speedup_omp, 4),
        "eficiencia_real": round(speedup_real / p, 4),
        "eficiencia_omp": round(speedup_omp / p, 4),
    }


def cargar_matrices():
    t = (pd.read_csv(crudas("matrices"))
           .groupby(["programa", "n", "hilos"])["tiempo"].min().reset_index())

    sec = t[t.programa == "secuencial"].set_index("n")["tiempo"]
    par = t[t.programa == "paralelo"].pivot(index="n", columns="hilos", values="tiempo")

    filas = [
        {"n": n, "hilos": p, **derivar(sec[n], par.loc[n, 1], par.loc[n, p], p)}
        for n in par.index for p in par.columns
    ]
    resumen = pd.DataFrame(filas).sort_values(["n", "hilos"])
    resumen.to_csv(resumen_csv("matrices"), index=False)
    return sec, par, resumen


def cargar_riemann():
    crudo = pd.read_csv(crudas("riemann"))
    t = (crudo.groupby(["programa", "funcion", "n", "hilos"])["tiempo"]
              .min().reset_index())

    sec = t[t.programa == "secuencial"].set_index(["funcion", "n"])["tiempo"]
    par = (t[t.programa == "paralelo"]
             .pivot(index=["funcion", "n"], columns="hilos", values="tiempo"))

    filas = [
        {"funcion": f, "n": n, "hilos": p,
         **derivar(sec[(f, n)], par.loc[(f, n), 1], par.loc[(f, n), p], p)}
        for f, n in par.index for p in par.columns
    ]
    resumen = pd.DataFrame(filas).sort_values(["funcion", "n", "hilos"])
    resumen.to_csv(resumen_csv("riemann"), index=False)
    return sec, par, resumen


# ------------------------------------------------------- figuras: matrices
PANELES_BASE = [
    ("speedup_real", "eficiencia_real", "Contra el secuencial"),
    ("speedup_omp", "eficiencia_omp", "Contra el paralelo con 1 hilo"),
]


def leyenda_tamanos(fig, tamanos, rampa, extra_handles=(), extra_etiquetas=(), ncol=None):
    handles = [Line2D([], [], color=rampa[i], marker=MARCAS[i], **ESTILO_MARCA)
               for i in range(len(tamanos))]
    handles.append(Line2D([], [], color=EJE, linewidth=1.0, linestyle=(0, (2, 3))))
    etiquetas = list(tamanos) + [f"{NUCLEOS_FISICOS} nucleos fisicos"]
    handles += list(extra_handles)
    etiquetas += list(extra_etiquetas)
    leyenda_figura(fig, handles, etiquetas, y=0.90, ncol=ncol or len(etiquetas))


def fig_matrices_speedup(resumen, tamanos, hilos):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    fig.suptitle("Speedup de la multiplicacion de matrices con OpenMP",
                 fontsize=13, color=TINTA, y=1.0)

    for ax, (columna, _, titulo) in zip(axes, PANELES_BASE):
        preparar(ax, titulo)
        eje_hilos(ax, hilos)
        ax.plot(hilos, hilos, color=EJE, linewidth=1.5, linestyle=(0, (4, 3)), zorder=2)
        ax.annotate("speedup ideal", xy=(hilos[-1], hilos[-1]), xytext=(-4, 6),
                    textcoords="offset points", ha="right", fontsize=8, color=TINTA_MUTE)

        etiquetas = []
        for i, n in enumerate(tamanos):
            d = resumen[resumen.n == n]
            ax.plot(d.hilos, d[columna], color=RAMPA[i], marker=MARCAS[i],
                    zorder=3, **ESTILO_MARCA)
            etiquetas.append((d.hilos.iloc[-1], d[columna].iloc[-1], f"{n}"))

        ax.set_yscale("log", base=2)
        ax.set_yticks([0.25, 0.5, 1, 2, 4, 8, 16])
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}x"))
        ax.set_xlim(0.85, 22)
        colocar_etiquetas(ax, etiquetas)

    axes[0].set_ylabel("Speedup")
    leyenda_tamanos(fig, [f"n = {n}" for n in tamanos], RAMPA)
    fig.subplots_adjust(top=0.74, wspace=0.12)
    guardar(fig, "matrices_speedup_vs_hilos.png")


def fig_matrices_eficiencia(resumen, tamanos, hilos):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    fig.suptitle("Eficiencia paralela de matrices  E(p) = S(p) / p",
                 fontsize=13, color=TINTA, y=1.0)

    for ax, (_, columna, titulo) in zip(axes, PANELES_BASE):
        preparar(ax, titulo)
        eje_hilos(ax, hilos)
        ax.axhline(100, color=EJE, linewidth=1.5, linestyle=(0, (4, 3)), zorder=2)
        ax.annotate("eficiencia ideal (100%)", xy=(hilos[-1], 100), xytext=(-4, 6),
                    textcoords="offset points", ha="right", fontsize=8, color=TINTA_MUTE)

        etiquetas = []
        for i, n in enumerate(tamanos):
            d = resumen[resumen.n == n]
            ax.plot(d.hilos, d[columna] * 100, color=RAMPA[i], marker=MARCAS[i],
                    zorder=3, **ESTILO_MARCA)
            etiquetas.append((d.hilos.iloc[-1], d[columna].iloc[-1] * 100, f"{n}"))

        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
        ax.set_ylim(0, 118)
        ax.set_xlim(0.85, 22)
        colocar_etiquetas(ax, etiquetas)

    axes[0].set_ylabel("Eficiencia")
    leyenda_tamanos(fig, [f"n = {n}" for n in tamanos], RAMPA)
    fig.subplots_adjust(top=0.74, wspace=0.12)
    guardar(fig, "matrices_eficiencia_vs_hilos.png")


def fig_matrices_tiempo_hilos(sec, par, tamanos, hilos):
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    fig.suptitle("Matrices: tiempo de calculo segun el numero de hilos",
                 fontsize=13, color=TINTA, y=1.0)
    preparar(ax)
    eje_hilos(ax, hilos)

    etiquetas = []
    for i, n in enumerate(tamanos):
        ax.plot(hilos, [par.loc[n, p] for p in hilos], color=RAMPA[i],
                marker=MARCAS[i], zorder=3, **ESTILO_MARCA)
        # el secuencial del mismo tamano, como referencia horizontal
        ax.axhline(sec[n], color=RAMPA[i], linewidth=1.3,
                   linestyle=(0, (5, 4)), alpha=0.85, zorder=2)
        etiquetas.append((hilos[-1], par.loc[n, hilos[-1]], f"{n}"))

    ax.set_yscale("log")
    ax.set_ylabel("Tiempo (s, escala log)")
    ax.set_xlim(0.85, 20)
    colocar_etiquetas(ax, etiquetas)

    leyenda_tamanos(fig, [f"n = {n}" for n in tamanos], RAMPA,
                    [Line2D([], [], color=TINTA_MUTE, linewidth=1.3, linestyle=(0, (5, 4)))],
                    ["secuencial"], ncol=6)
    fig.subplots_adjust(top=0.80)
    guardar(fig, "matrices_tiempo_vs_hilos.png")


def fig_matrices_tiempo_tamano(sec, par, tamanos):
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    fig.suptitle("Matrices: crecimiento del tiempo con el tamano",
                 fontsize=13, color=TINTA, y=1.0)
    preparar(ax)

    # El secuencial no es un paso de la rampa: es la referencia, en otro tono.
    series = [(sec.loc[tamanos].values, NARANJA, "o", "secuencial", "secuencial")]
    for p, color, marca in zip((1, 8, 16), RAMPA3, ("s", "^", "D")):
        hilo = "hilo" if p == 1 else "hilos"
        series.append(([par.loc[n, p] for n in tamanos], color, marca,
                       f"paralelo, {p} {hilo}", f"{p} {hilo}"))

    etiquetas = []
    for valores, color, marca, _, corta in series:
        ax.plot(tamanos, valores, color=color, marker=marca, zorder=3, **ESTILO_MARCA)
        etiquetas.append((tamanos[-1], valores[-1], corta))

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(tamanos)
    ax.xaxis.set_major_formatter(FuncFormatter(entero))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("Tamano de la matriz (n)")
    ax.set_ylabel("Tiempo (s, escala log)")
    ax.set_xlim(tamanos[0] * 0.9, tamanos[-1] * 1.12)
    colocar_etiquetas(ax, etiquetas)

    handles = [Line2D([], [], color=c, marker=m, **ESTILO_MARCA)
               for _, c, m, _, _ in series]
    leyenda_figura(fig, handles, [e for *_, e, _ in series], y=0.90, ncol=4)
    fig.subplots_adjust(top=0.80)
    guardar(fig, "matrices_tiempo_vs_tamano.png")


# -------------------------------------------------------- figuras: riemann
NOMBRE_FUNCION = {1: "f(x) = x$^2$", 2: "f(x) = x$^3$", 3: "f(x) = sin(x)",
                  4: "f(x) = cos(x)", 5: "f(x) = e$^{-x^2}$"}


def fmt_rect(n):
    """10^8, 5x10^8, 10^9 -- en notacion matematica, no 100000000."""
    exponente = len(str(int(n))) - 1
    mantisa = n / 10 ** exponente
    if abs(mantisa - 1) < 1e-9:
        return rf"$10^{{{exponente}}}$"
    return rf"${mantisa:g}{{\times}}10^{{{exponente}}}$"


def rejilla_riemann(titulo, funciones, alto=8.4):
    """Grid funcion x linea base: Riemann tiene tres dimensiones (rectangulos,
    funcion, referencia de speedup) y no caben como series en un solo panel."""
    fig, axes = plt.subplots(len(funciones), 2, figsize=(11, alto),
                             sharey="row", sharex=True)
    fig.suptitle(titulo, fontsize=13, color=TINTA, y=1.0)
    return fig, axes


def fig_riemann_speedup(resumen, rects, hilos, funciones):
    fig, axes = rejilla_riemann("Speedup de la suma de Riemann con OpenMP", funciones)

    for fila, f in enumerate(funciones):
        for col, (columna, _, base) in enumerate(PANELES_BASE):
            ax = axes[fila][col]
            preparar(ax, f"{NOMBRE_FUNCION[f]}  ·  {base}")
            eje_hilos(ax, hilos)
            ax.plot(hilos, hilos, color=EJE, linewidth=1.5, linestyle=(0, (4, 3)), zorder=2)

            etiquetas = []
            for i, n in enumerate(rects):
                d = resumen[(resumen.funcion == f) & (resumen.n == n)]
                ax.plot(d.hilos, d[columna], color=RAMPA3[i], marker=MARCAS[i],
                        zorder=3, **ESTILO_MARCA)
                etiquetas.append((d.hilos.iloc[-1], d[columna].iloc[-1], fmt_rect(n)))

            ax.set_yscale("log", base=2)
            ax.set_yticks([0.5, 1, 2, 4, 8, 16, 32])
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}x"))
            ax.set_xlim(0.85, 24)
            colocar_etiquetas(ax, etiquetas)
            if col == 0:
                ax.set_ylabel("Speedup")
            if fila == 0:
                ax.set_xlabel("")

    leyenda_tamanos(fig, [fmt_rect(n) for n in rects], RAMPA3,
                    [Line2D([], [], color=EJE, linewidth=1.5, linestyle=(0, (4, 3)))],
                    ["speedup ideal"])
    fig.subplots_adjust(top=0.82, hspace=0.30, wspace=0.10)
    guardar(fig, "riemann_speedup_vs_hilos.png")


def fig_riemann_eficiencia(resumen, rects, hilos, funciones):
    fig, axes = rejilla_riemann("Eficiencia paralela de Riemann  E(p) = S(p) / p",
                                funciones)

    for fila, f in enumerate(funciones):
        for col, (_, columna, base) in enumerate(PANELES_BASE):
            ax = axes[fila][col]
            preparar(ax, f"{NOMBRE_FUNCION[f]}  ·  {base}")
            eje_hilos(ax, hilos)
            ax.axhline(100, color=EJE, linewidth=1.5, linestyle=(0, (4, 3)), zorder=2)

            etiquetas = []
            for i, n in enumerate(rects):
                d = resumen[(resumen.funcion == f) & (resumen.n == n)]
                ax.plot(d.hilos, d[columna] * 100, color=RAMPA3[i], marker=MARCAS[i],
                        zorder=3, **ESTILO_MARCA)
                etiquetas.append((d.hilos.iloc[-1], d[columna].iloc[-1] * 100, fmt_rect(n)))

            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
            ax.set_ylim(0, 175)
            ax.set_xlim(0.85, 24)
            colocar_etiquetas(ax, etiquetas)
            if col == 0:
                ax.set_ylabel("Eficiencia")
            if fila == 0:
                ax.set_xlabel("")

    leyenda_tamanos(fig, [fmt_rect(n) for n in rects], RAMPA3,
                    [Line2D([], [], color=EJE, linewidth=1.5, linestyle=(0, (4, 3)))],
                    ["eficiencia ideal (100%)"])
    fig.subplots_adjust(top=0.82, hspace=0.30, wspace=0.10)
    guardar(fig, "riemann_eficiencia_vs_hilos.png")


def fig_riemann_tiempo_hilos(sec, par, rects, hilos, funciones):
    fig, axes = plt.subplots(1, len(funciones), figsize=(11, 4.8), sharey=True)
    fig.suptitle("Riemann: tiempo de calculo segun el numero de hilos",
                 fontsize=13, color=TINTA, y=1.0)

    for ax, f in zip(axes, funciones):
        preparar(ax, NOMBRE_FUNCION[f])
        eje_hilos(ax, hilos)

        etiquetas = []
        for i, n in enumerate(rects):
            ax.plot(hilos, [par.loc[(f, n), p] for p in hilos], color=RAMPA3[i],
                    marker=MARCAS[i], zorder=3, **ESTILO_MARCA)
            ax.axhline(sec[(f, n)], color=RAMPA3[i], linewidth=1.3,
                       linestyle=(0, (5, 4)), alpha=0.85, zorder=2)
            etiquetas.append((hilos[-1], par.loc[(f, n), hilos[-1]], fmt_rect(n)))

        ax.set_yscale("log")
        ax.set_xlim(0.85, 22)
        colocar_etiquetas(ax, etiquetas)

    axes[0].set_ylabel("Tiempo (s, escala log)")
    leyenda_tamanos(fig, [fmt_rect(n) for n in rects], RAMPA3,
                    [Line2D([], [], color=TINTA_MUTE, linewidth=1.3, linestyle=(0, (5, 4)))],
                    ["secuencial"], ncol=5)
    fig.subplots_adjust(top=0.74, wspace=0.12)
    guardar(fig, "riemann_tiempo_vs_hilos.png")


def fig_riemann_tiempo_tamano(sec, par, rects, funciones):
    fig, axes = plt.subplots(1, len(funciones), figsize=(11, 4.8), sharey=True)
    fig.suptitle("Riemann: crecimiento del tiempo con el numero de rectangulos",
                 fontsize=13, color=TINTA, y=1.0)

    for ax, f in zip(axes, funciones):
        preparar(ax, NOMBRE_FUNCION[f])

        series = [([sec[(f, n)] for n in rects], NARANJA, "o", "secuencial", "sec.")]
        for p, color, marca in zip((1, 8, 16), RAMPA3, ("s", "^", "D")):
            hilo = "hilo" if p == 1 else "hilos"
            series.append(([par.loc[(f, n), p] for n in rects], color, marca,
                           f"paralelo, {p} {hilo}", f"{p} {hilo}"))

        etiquetas = []
        for valores, color, marca, _, corta in series:
            ax.plot(rects, valores, color=color, marker=marca, zorder=3, **ESTILO_MARCA)
            etiquetas.append((rects[-1], valores[-1], corta))

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xticks(rects)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: fmt_rect(v)))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xlabel("Rectangulos")
        ax.set_xlim(rects[0] * 0.85, rects[-1] * 1.30)
        colocar_etiquetas(ax, etiquetas)

    axes[0].set_ylabel("Tiempo (s, escala log)")
    handles = [Line2D([], [], color=c, marker=m, **ESTILO_MARCA)
               for _, c, m, _, _ in series]
    leyenda_figura(fig, handles, [e for *_, e, _ in series], y=0.90, ncol=4)
    fig.subplots_adjust(top=0.74, wspace=0.12)
    guardar(fig, "riemann_tiempo_vs_tamano.png")


# ----------------------------------------------------------------- reporte
def reportar(titulo, resumen, agrupar):
    """Resumen en texto con el maximo de hilos, mas la razon t_par(1)/t_sec:
    si no es ~1, el pragma cambio lo que el compilador puede optimizar."""
    print(f"\n{titulo}")
    p_max = resumen.hilos.max()
    for clave, g in resumen.groupby(agrupar):
        fila = g[g.hilos == p_max].iloc[0]
        base = g[g.hilos == 1].iloc[0]
        etiqueta = ", ".join(f"{k}={v}" for k, v in zip(agrupar, clave)) \
            if isinstance(clave, tuple) else f"{agrupar[0]}={clave}"
        print(f"  {etiqueta:<22} speedup vs sec {fila.speedup_real:5.2f}x"
              f"   vs par-1hilo {fila.speedup_omp:5.2f}x"
              f"   eficiencia {fila.eficiencia_omp * 100:3.0f}%"
              f"   |  t_par(1)/t_sec = {base.t_par / base.t_sec:.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--etiqueta", default=os.environ.get("ETIQUETA") or getpass.getuser(),
                    help="separa las salidas por maquina/persona "
                         "(resultados_<etiqueta>/ e img_<etiqueta>/). "
                         "Por defecto: $ETIQUETA o el usuario del sistema")
    args = ap.parse_args()
    resolver_rutas(args.etiqueta)

    disponibles = [pr for pr in ("matrices", "riemann") if crudas(pr).exists()]
    if not disponibles:
        sys.exit(f"No hay datos en {RESULTADOS.name}/.\n"
                 f"Corre primero:  ETIQUETA={args.etiqueta} ./scripts/benchmark.sh")

    RESULTADOS.mkdir(exist_ok=True)
    IMG.mkdir(exist_ok=True)
    print("Figuras:")

    if "matrices" in disponibles:
        sec, par, resumen = cargar_matrices()
        tamanos = sorted(par.index.tolist())
        hilos = sorted(par.columns.tolist())
        fig_matrices_speedup(resumen, tamanos, hilos)
        fig_matrices_eficiencia(resumen, tamanos, hilos)
        fig_matrices_tiempo_hilos(sec, par, tamanos, hilos)
        fig_matrices_tiempo_tamano(sec, par, tamanos)
        matrices = resumen

    if "riemann" in disponibles:
        sec, par, resumen = cargar_riemann()
        funciones = sorted({f for f, _ in par.index})
        rects = sorted({n for _, n in par.index})
        hilos = sorted(par.columns.tolist())
        fig_riemann_speedup(resumen, rects, hilos, funciones)
        fig_riemann_eficiencia(resumen, rects, hilos, funciones)
        fig_riemann_tiempo_hilos(sec, par, rects, hilos, funciones)
        fig_riemann_tiempo_tamano(sec, par, rects, funciones)
        riemann = resumen

    if "matrices" in disponibles:
        reportar("MATRICES, con el maximo de hilos:", matrices, ["n"])
    if "riemann" in disponibles:
        reportar("RIEMANN, con el maximo de hilos:", riemann, ["funcion", "n"])


if __name__ == "__main__":
    main()
