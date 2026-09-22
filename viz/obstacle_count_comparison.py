"""Punto 1.2: metodologia "n obstaculos de area total fija con n creciente".

Compara <t90> para K=1, K=2 y K=3 obstaculos que en conjunto conservan la misma
area total que el mejor obstaculo unico encontrado en configuration_comparison.py
(R=0.15 m, centrado en x=L/2). Se ubican simetricamente sobre el eje longitudinal,
centrados en y=W/2, respetando las restricciones del enunciado:

i.  K obstaculos integramente dentro del dominio y sin solaparse entre si.
ii. Rk >= r y tal que permita la generacion de las N particulas.

La mesa vacia (K=0) es solo la referencia de comparacion, no una configuracion
explorada (esas requieren K>0).

Java no conoce este experimento ni recibe argumentos por linea de comando: cada
corrida se dispara reescribiendo la unica fuente de verdad, input/config.json, y
ejecutando el jar sin argumentos. El config original se restaura al final.
"""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from obstacle_layouts import TOTAL_AREA_RADIUS, layout, validate_layout
import fu_curves
from observables import t90_from_goals

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"

N = 100
MAX_TIME = 100.0
K_VALUES = [1, 2, 3]
REALIZATIONS = 5
BASE_SEED = 20260920
RETRIES = 5


def build_config(base, obstacles, seed):
    cfg = json.loads(json.dumps(base))
    cfg.pop("obstaclesFile", None)  # esta corrida fija sus propios obstaculos inline
    cfg.pop("initialPositionsFile", None)  # esta corrida usa colocacion aleatoria por defecto
    cfg["simulation"]["maxTime"] = MAX_TIME
    cfg["simulation"]["seed"] = seed
    cfg["particles"]["count"] = N
    cfg["output"] = {"everyEvents": 1_000_000, "writeStates": False,
                      "writeGoals": True, "writeCollisions": False}
    cfg["obstacles"] = obstacles
    return cfg


def run_once(base, obstacles, seed):
    CONFIG_PATH.write_text(json.dumps(build_config(base, obstacles, seed)), encoding="utf-8")
    result = subprocess.run(["java", "-jar", str(JAR)], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Corrida fallida (obstacles={obstacles}, seed={seed}): "
                            f"{result.stderr.strip() or result.stdout.strip()}")
    directory = None
    for line in result.stdout.splitlines():
        if line.startswith("Archivos: "):
            directory = Path(line[len("Archivos: "):].strip())
    if directory is None:
        raise RuntimeError(f"No se pudo determinar el directorio de salida: {result.stdout}")
    metadata_files = list(directory.glob("metadata_*.json"))
    if len(metadata_files) != 1:
        raise RuntimeError(f"Metadata inesperada en {directory}")
    metadata = json.loads(metadata_files[0].read_text(encoding="utf-8"))
    if metadata.get("status") != "COMPLETED":
        raise RuntimeError(f"Corrida no completada: {directory}")
    metadata["t90"] = t90_from_goals(directory)
    return metadata, directory


def run_with_retries(base, obstacles, seed):
    last_error = None
    for attempt in range(RETRIES):
        try:
            return run_once(base, obstacles, seed + attempt * 7919)
        except RuntimeError as error:
            last_error = error
            print(f"  intento {attempt + 1}/{RETRIES} fallo: {error}")
    raise last_error


def t90_stats(metadatas, label):
    values = [m["t90"] for m in metadatas if m.get("t90") is not None]
    missed = len(metadatas) - len(values)
    if missed:
        print(f"  aviso: {missed}/{len(metadatas)} corridas de '{label}' no alcanzaron Fu>=0.9 en tmax")
    if not values:
        return None, None, 0
    return mean(values), (pstdev(values) if len(values) > 1 else 0.0), len(values)


def realize():
    base = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    length = base["simulation"]["length"]
    width = base["simulation"]["width"]
    particle_radius = base["particles"]["radius"]

    results = {"empty": [], "k": {}}
    for i in range(REALIZATIONS):
        seed = BASE_SEED + i
        print(f"mesa vacia realizacion {i + 1}/{REALIZATIONS} seed={seed}")
        metadata, directory = run_with_retries(base, [], seed)
        results["empty"].append(metadata)
        print(f"  t90={metadata['t90']}")
        if i == 0:
            fu_curves.save_curve("mesa_vacia", directory, metadata)

    for k in K_VALUES:
        obstacles = layout(k, length, width)
        validate_layout(obstacles, length, width, particle_radius)
        print(f"K={k}: R={obstacles[0]['radius']:.4f} m, centros x={[round(o['x'], 4) for o in obstacles]}")
        runs = []
        for i in range(REALIZATIONS):
            seed = BASE_SEED + k * 1000 + i
            print(f"K={k} realizacion {i + 1}/{REALIZATIONS} seed={seed}")
            metadata, directory = run_with_retries(base, obstacles, seed)
            runs.append(metadata)
            print(f"  t90={metadata['t90']}")
            if i == 0:
                fu_curves.save_curve(f"K={k}", directory, metadata)
        results["k"][k] = runs
    return results


def plot(results):
    empty_mean, empty_std, empty_n = t90_stats(results["empty"], "mesa vacia")
    ks, means, stds, counts = [], [], [], []
    for k in K_VALUES:
        m, s, n = t90_stats(results["k"][k], f"K={k}")
        if m is None:
            continue
        ks.append(k)
        means.append(m)
        stds.append(s)
        counts.append(n)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.errorbar(ks, means, yerr=stds, fmt="o-", capsize=4, color="tab:blue",
                label=f"K obstaculos, area total fija (pi*{TOTAL_AREA_RADIUS}^2 m^2)")
    if empty_mean is not None:
        ax.axhline(empty_mean, color="0.4", linestyle="--", label=f"Mesa vacia (<t90>={empty_mean:.2f} s)")
        ax.axhspan(empty_mean - empty_std, empty_mean + empty_std, color="0.4", alpha=0.15)
    ax.set(xlabel="K (numero de obstaculos)", ylabel="<t90> [s]",
           title=f"Punto 1.2 - <t90> vs K, area total fija (N={N})")
    ax.set_xticks(ks)
    ax.grid(alpha=0.25)
    ax.legend()
    folder = OUTPUT / "experiment_1_2_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"obstacle_count_comparison_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    for k, m, s, n in zip(ks, means, stds, counts):
        print(f"K={k}: <t90>={m:.3f} s, std={s:.3f} s, n={n}")
    if empty_mean is not None:
        print(f"mesa vacia: <t90>={empty_mean:.3f} s, std={empty_std:.3f} s, n={empty_n}")
    return path


def main():
    if not JAR.exists():
        raise FileNotFoundError(f"No se encontro el jar compilado: {JAR}. Ejecutar 'mvn -q clean package' primero")
    original = CONFIG_PATH.read_text(encoding="utf-8")
    try:
        results = realize()
        plot(results)
    finally:
        CONFIG_PATH.write_text(original, encoding="utf-8")
        print("input/config.json restaurado a su contenido original")


if __name__ == "__main__":
    main()
