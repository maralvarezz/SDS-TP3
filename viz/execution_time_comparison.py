"""Punto 1.1: compara en un unico grafico el tiempo de ejecucion vs N entre
las dos estrategias de colocacion inicial ya implementadas por separado:

- colocacion aleatoria por rechazo secuencial (RSA), en execution_time.py;
- empaquetado hexagonal, en hexagonal_execution_time.py.

Este script no duplica logica de corrida: reutiliza tal cual las funciones
`realize()` de esos dos modulos (mismos N, REALIZATIONS, seeds y
reintentos que cada uno ya tenia) y unicamente las orquesta una detras de
la otra y las grafica juntas, para poder comparar en el mismo eje hasta
donde llega cada metodo de colocacion (ver docstring de
hexagonal_execution_time.py: la hipotesis es que el empaquetado hexagonal
llega a N mas altos que la colocacion aleatoria).

Java no conoce este experimento ni recibe argumentos por linea de comando:
cada corrida se dispara reescribiendo la unica fuente de verdad,
input/config.json, y ejecutando el jar sin argumentos. El config original se
restaura al final.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from tempfile import TemporaryDirectory

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import execution_time as rsa_exp
import hexagonal_execution_time as hex_exp

OUTPUT = rsa_exp.OUTPUT


def _series(runtimes, n_values):
    ns = [n for n in n_values if runtimes.get(n)]
    means = [mean(runtimes[n]) for n in ns]
    stds = [pstdev(runtimes[n]) if len(runtimes[n]) > 1 else 0.0 for n in ns]
    return ns, means, stds


def plot(rsa_runtimes, hex_runtimes):
    fig, ax = plt.subplots(figsize=(7.5, 4.8))

    ns, means, stds = _series(rsa_runtimes, rsa_exp.N_VALUES)
    for n, m, s in zip(ns, means, stds):
        print(f"RSA N={n}: {len(rsa_runtimes[n])} corridas, media={m:.1f} ms, std={s:.1f} ms")
    ax.errorbar(ns, means, yerr=stds, fmt="o-", capsize=4, color="tab:blue",
                label="Colocacion aleatoria (RSA)")

    ns_h, means_h, stds_h = _series(hex_runtimes, hex_exp.N_VALUES)
    for n, m, s in zip(ns_h, means_h, stds_h):
        print(f"Hexagonal N={n}: {len(hex_runtimes[n])} corridas, media={m:.1f} ms, std={s:.1f} ms")
    ax.errorbar(ns_h, means_h, yerr=stds_h, fmt="o-", capsize=4, color="tab:green",
                label="Empaquetado hexagonal")

    ax.set(xlabel="N (particulas)", ylabel="Tiempo de ejecucion [ms]",
           title="Punto 1.1 - Tiempo de ejecucion vs N (mesa vacia, tf=30s)")
    ax.set_yscale("log")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    folder = OUTPUT / "experiment_1_1_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"execution_time_comparison_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    return path


def main():
    if not rsa_exp.JAR.exists():
        raise FileNotFoundError(f"No se encontro el jar compilado: {rsa_exp.JAR}. Ejecutar 'mvn -q clean package' primero")
    original = rsa_exp.CONFIG_PATH.read_text(encoding="utf-8")
    try:
        print("=== Colocacion aleatoria (RSA) ===")
        rsa_runtimes = rsa_exp.realize()
        base = json.loads(rsa_exp.CONFIG_PATH.read_text(encoding="utf-8"))
        print("=== Empaquetado hexagonal ===")
        with TemporaryDirectory() as tmp:
            hex_runtimes = hex_exp.realize(base, Path(tmp))
        plot(rsa_runtimes, hex_runtimes)
    finally:
        rsa_exp.CONFIG_PATH.write_text(original, encoding="utf-8")
        print("input/config.json restaurado a su contenido original")


if __name__ == "__main__":
    main()
