"""Punto 1.4 (competencia): busca el mejor radio para un obstaculo unico
centrado (x=L/2, y=W/2), extendiendo la exploracion sistematica del punto 1.2
(configuration_comparison.py encontro que x=L/2 es la mejor posicion para
R=0.15; este script barre R con esa posicion fija).

Usa los parametros fijos de la competencia: N=100, v0=1 m/s, r=0.0175 m,
m=0.025 kg, L=1.20 m, W=0.68 m, d=0.20 m, tmax=100 s.

Java no conoce este experimento ni recibe argumentos por linea de comando:
cada corrida se dispara reescribiendo la unica fuente de verdad,
input/config.json, y ejecutando el jar sin argumentos. El config original se
restaura al final.
"""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from observables import t90_from_goals

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"

N = 100
V0 = 1.0
PARTICLE_RADIUS = 0.0175
MASS = 0.025
LENGTH = 1.20
WIDTH = 0.68
GOAL_SIZE = 0.20
MAX_TIME = 100.0

R_VALUES = [0.30, 0.31, 0.32, 0.33]
REALIZATIONS = 5  # minimo del enunciado para el punto 1.2
BASE_SEED = 20261940
RETRIES = 5


def build_config(r, seed):
    return {
        "simulation": {"length": LENGTH, "width": WIDTH, "goalSize": GOAL_SIZE,
                        "maxTime": MAX_TIME, "seed": seed},
        "particles": {"count": N, "radius": PARTICLE_RADIUS, "mass": MASS, "initialSpeed": V0},
        "output": {"everyEvents": 1_000_000, "writeStates": False,
                   "writeGoals": True, "writeCollisions": False},
        "obstacles": [{"x": LENGTH / 2, "y": WIDTH / 2, "radius": r}],
    }


def run_once(r, seed):
    CONFIG_PATH.write_text(json.dumps(build_config(r, seed)), encoding="utf-8")
    result = subprocess.run(["java", "-jar", str(JAR)], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Corrida fallida (R={r}, seed={seed}): "
                            f"{result.stderr.strip() or result.stdout.strip()}")
    directory = None
    for line in result.stdout.splitlines():
        if line.startswith("Archivos: "):
            directory = Path(line[len("Archivos: "):].strip())
    metadata_files = list(directory.glob("metadata_*.json"))
    metadata = json.loads(metadata_files[0].read_text(encoding="utf-8"))
    if metadata.get("status") != "COMPLETED":
        raise RuntimeError(f"Corrida no completada: {directory}")
    metadata["t90"] = t90_from_goals(directory)
    return metadata


def run_with_retries(r, seed):
    last_error = None
    for attempt in range(RETRIES):
        try:
            return run_once(r, seed + attempt * 7919)
        except RuntimeError as error:
            last_error = error
            print(f"  intento {attempt + 1}/{RETRIES} fallo: {error}")
    raise last_error


def t90_stats(metadatas):
    values = [m["t90"] for m in metadatas if m.get("t90") is not None]
    missed = len(metadatas) - len(values)
    if missed:
        print(f"  aviso: {missed}/{len(metadatas)} corridas no alcanzaron Fu>=0.9 en tmax")
    if not values:
        goals = [m["totalGoals"] for m in metadatas]
        return None, None, len(metadatas), mean(goals)
    return mean(values), (pstdev(values) if len(values) > 1 else 0.0), len(values), None


def main():
    if not JAR.exists():
        raise FileNotFoundError(f"No se encontro el jar compilado: {JAR}. Ejecutar 'mvn -q clean package' primero")
    original = CONFIG_PATH.read_text(encoding="utf-8")
    results = {}
    try:
        for r in R_VALUES:
            runs = []
            for i in range(REALIZATIONS):
                seed = BASE_SEED + int(round(r * 1000)) + i
                metadata = run_with_retries(r, seed)
                runs.append(metadata)
                print(f"R={r} realizacion {i + 1}/{REALIZATIONS} seed={seed} t90={metadata['t90']}")
            results[r] = t90_stats(runs)

        print("\nResumen:")
        best_r, best_mean = None, None
        for r in R_VALUES:
            m, s, n, goals = results[r]
            if m is None:
                print(f"  R={r}: no alcanzo t90 en ninguna corrida, goles promedio={goals:.1f}/{N}")
                continue
            print(f"  R={r}: <t90>={m:.3f} s, std={s:.3f} s, n={n}")
            if best_mean is None or m < best_mean:
                best_mean, best_r = m, r

        rs = [r for r in R_VALUES if results[r][0] is not None]
        means = [results[r][0] for r in rs]
        stds = [results[r][1] for r in rs]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.errorbar(rs, means, yerr=stds, fmt="o-", capsize=4, color="tab:blue")
        ax.set(xlabel="Radio del obstaculo unico centrado [m]", ylabel="<t90> [s]",
               title="Punto 1.4 - Busqueda de competencia: <t90> vs R (K=1, x=L/2, y=W/2)")
        ax.grid(alpha=0.25)
        folder = OUTPUT / "competition_search_plots"
        folder.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        path = folder / f"competition_search_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        print(path)

        if best_r is not None:
            print(f"\nMejor R encontrado: {best_r} con <t90>={best_mean:.3f} s")
    finally:
        CONFIG_PATH.write_text(original, encoding="utf-8")
        print("input/config.json restaurado a su contenido original")


if __name__ == "__main__":
    main()
