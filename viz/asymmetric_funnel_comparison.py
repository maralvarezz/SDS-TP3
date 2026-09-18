"""Punto 1.2: variante asimetrica del embudo de flanking_circles_comparison.py.

Toma la misma estructura (circulo grande R_big + 2 circulos iguales r_small,
tangentes a el, centrados en y=W/2) pero desplaza todo el conjunto sobre el
eje x, acercandolo al arco de x=0 en vez de mantenerlo centrado. El objetivo
es ver si romper la simetria (favorecer un arco sobre el otro) ayuda o
perjudica <t90> cuando la estructura es la del "canal angosto" (R_big grande)
en vez del obstaculo chico usado en configuration_comparison.py (R=0.15),
donde ya se vio que alejarse del centro empeora.

Restriccion (i): con R_big=0.335 y r_small=0.02 (mejores valores encontrados
en radius_comparison.py y flanking_circles_comparison.py), el circulo chico
cercano al arco desplazado queda en x_big - (R_big+r_small)*margen; la
contencion (Rk<=xk) fija el desplazamiento maximo desde el centro en
~0.2246 m (calculado antes de correr el experimento). El barrido no supera
ese limite.

N=100, maxTime=100s (mismos parametros que el resto de los scripts de 1.2).

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

import fu_curves
from obstacle_layouts import validate_layout

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"

N = 100
MAX_TIME = 100.0
BIG_RADIUS = 0.335
SMALL_RADIUS = 0.02
MARGIN = 1.001
SHIFTS = [0.0, 0.05, 0.10, 0.15, 0.20]  # desplazamiento hacia el arco x=0, desde el centro
REALIZATIONS = 10
BASE_SEED = 20267000
RETRIES = 5


def layout(shift, length, width):
    y = width / 2
    x_big = length / 2 - shift
    gap = (BIG_RADIUS + SMALL_RADIUS) * MARGIN
    return [
        {"x": x_big, "y": y, "radius": BIG_RADIUS},
        {"x": x_big - gap, "y": y, "radius": SMALL_RADIUS},
        {"x": x_big + gap, "y": y, "radius": SMALL_RADIUS},
    ]


def build_config(base, obstacles, seed, write_goals=False):
    cfg = json.loads(json.dumps(base))
    cfg.pop("obstaclesFile", None)
    cfg.pop("initialPositionsFile", None)
    cfg["simulation"]["maxTime"] = MAX_TIME
    cfg["simulation"]["seed"] = seed
    cfg["particles"]["count"] = N
    cfg["output"] = {"everyEvents": 1_000_000, "writeStates": False,
                      "writeGoals": write_goals, "writeCollisions": False}
    cfg["obstacles"] = obstacles
    return cfg


def run_once(base, obstacles, seed, write_goals=False):
    CONFIG_PATH.write_text(json.dumps(build_config(base, obstacles, seed, write_goals)), encoding="utf-8")
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
    return metadata, directory


def run_with_retries(base, obstacles, seed, write_goals=False):
    last_error = None
    for attempt in range(RETRIES):
        try:
            return run_once(base, obstacles, seed + attempt * 7919, write_goals)
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

    results = {"empty": []}
    for i in range(REALIZATIONS):
        seed = BASE_SEED + i
        print(f"mesa vacia realizacion {i + 1}/{REALIZATIONS} seed={seed}")
        metadata, directory = run_with_retries(base, [], seed, write_goals=(i == 0))
        results["empty"].append(metadata)
        print(f"  t90={metadata['t90']}")
        if i == 0:
            fu_curves.save_curve("mesa_vacia", directory, metadata)

    for shift in SHIFTS:
        obstacles = layout(shift, length, width)
        validate_layout(obstacles, length, width, particle_radius)
        print(f"shift={shift}: obstaculos={obstacles}")
        runs = []
        for i in range(REALIZATIONS):
            seed = BASE_SEED + int(round(shift * 10000)) + i
            print(f"shift={shift} realizacion {i + 1}/{REALIZATIONS} seed={seed}")
            metadata, directory = run_with_retries(base, obstacles, seed, write_goals=(i == 0))
            runs.append(metadata)
            print(f"  t90={metadata['t90']}")
            if i == 0:
                fu_curves.save_curve(f"embudo_asimetrico_shift={shift}", directory, metadata)
        results[shift] = runs
    return results


def plot(results):
    empty_mean, empty_std, empty_n = t90_stats(results["empty"], "mesa vacia")
    shifts, means, stds, counts = [], [], [], []
    for shift in SHIFTS:
        m, s, n = t90_stats(results[shift], f"shift={shift}")
        if m is None:
            continue
        shifts.append(shift)
        means.append(m)
        stds.append(s)
        counts.append(n)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.errorbar(shifts, means, yerr=stds, fmt="o-", capsize=4, color="tab:purple",
                label=f"Embudo desplazado (R={BIG_RADIUS}, r={SMALL_RADIUS})")
    if empty_mean is not None:
        ax.axhline(empty_mean, color="tab:blue", linestyle="--", label=f"Mesa vacia (<t90>={empty_mean:.2f} s)")
        ax.axhspan(empty_mean - empty_std, empty_mean + empty_std, color="tab:blue", alpha=0.15)
    ax.set(xlabel="Desplazamiento hacia el arco x=0 [m]", ylabel="<t90> [s]",
           title=f"Punto 1.2 - Embudo asimetrico vs desplazamiento (N={N})")
    ax.grid(alpha=0.25)
    ax.legend()
    folder = OUTPUT / "experiment_1_2_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"asymmetric_funnel_comparison_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    for shift, m, s, n in zip(shifts, means, stds, counts):
        print(f"shift={shift}: <t90>={m:.3f} s, std={s:.3f} s, n={n}")
    if empty_mean is not None:
        print(f"mesa vacia: <t90>={empty_mean:.3f} s, std={empty_std:.3f} s, n={empty_n}")
    if shifts:
        best = min(range(len(shifts)), key=lambda i: means[i])
        print(f"Mejor desplazamiento explorado: shift={shifts[best]} con <t90>={means[best]:.3f} s")
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
