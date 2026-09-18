"""Punto 1.2: "paragolpes" de arco. Idea nueva, no probada todavia: en vez de
poner los circulos chicos sobre la linea media (que si crecen tapan el
arco, ver flanking_circles_comparison.py), se colocan 4 circulos chicos
(radio r_end, iguales entre si) justo por fuera de los bordes superior e
inferior de cada arco, cerca de cada pared corta. La idea es imitar los
paragolpes de una mesa de metegol real: desvian la trayectoria hacia adentro
del arco en vez de bloquearlo, porque quedan fuera del ancho del arco
(d=0.20 m centrado en W/2), no delante de el.

Geometria (con el circulo grande centrado, R_big=0.335, ya establecido como
buena base): para cada arco, a una distancia x_e de la pared corta, un
circulo con centro en y = (W/2 - d/2) - r_end (por debajo del arco) y otro
en y = (W/2 + d/2) + r_end (por encima), ambos tangentes al borde del arco
desde afuera.

Restricciones verificadas para cada r_end antes de correr: (i) contencion
(r_end <= x_e, r_end <= y <= W-r_end) y no solapamiento con el circulo
grande ni entre si; (ii) r_end >= r_particula.

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
X_END = 0.10  # distancia de los paragolpes a cada pared corta
END_RADII = [0.02, 0.04, 0.06, 0.08, 0.10]
REALIZATIONS = 10
BASE_SEED = 20268000
RETRIES = 5


def layout(r_end, length, width, goal_size):
    y_center = width / 2
    x_big = length / 2
    y_low = (y_center - goal_size / 2) - r_end
    y_high = (y_center + goal_size / 2) + r_end
    obstacles = [{"x": x_big, "y": y_center, "radius": BIG_RADIUS}]
    for x_e in (X_END, length - X_END):
        obstacles.append({"x": x_e, "y": y_low, "radius": r_end})
        obstacles.append({"x": x_e, "y": y_high, "radius": r_end})
    return obstacles


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
    goal_size = base["simulation"]["goalSize"]
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

    for r_end in END_RADII:
        obstacles = layout(r_end, length, width, goal_size)
        validate_layout(obstacles, length, width, particle_radius)
        print(f"r_end={r_end}: obstaculos={obstacles}")
        runs = []
        for i in range(REALIZATIONS):
            seed = BASE_SEED + int(round(r_end * 10000)) + i
            print(f"r_end={r_end} realizacion {i + 1}/{REALIZATIONS} seed={seed}")
            metadata, directory = run_with_retries(base, obstacles, seed, write_goals=(i == 0))
            runs.append(metadata)
            print(f"  t90={metadata['t90']}")
            if i == 0:
                fu_curves.save_curve(f"paragolpes_r={r_end}", directory, metadata)
        results[r_end] = runs
    return results


def plot(results):
    empty_mean, empty_std, empty_n = t90_stats(results["empty"], "mesa vacia")
    rs, means, stds, counts = [], [], [], []
    for r_end in END_RADII:
        m, s, n = t90_stats(results[r_end], f"r_end={r_end}")
        if m is None:
            continue
        rs.append(r_end)
        means.append(m)
        stds.append(s)
        counts.append(n)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.errorbar(rs, means, yerr=stds, fmt="o-", capsize=4, color="tab:brown",
                label=f"Circulo grande (R={BIG_RADIUS}) + 4 paragolpes de arco")
    if empty_mean is not None:
        ax.axhline(empty_mean, color="tab:blue", linestyle="--", label=f"Mesa vacia (<t90>={empty_mean:.2f} s)")
        ax.axhspan(empty_mean - empty_std, empty_mean + empty_std, color="tab:blue", alpha=0.15)
    ax.set(xlabel="Radio de los paragolpes [m]", ylabel="<t90> [s]",
           title=f"Punto 1.2 - Paragolpes de arco (N={N})")
    ax.grid(alpha=0.25)
    ax.legend()
    folder = OUTPUT / "experiment_1_2_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"goal_bumpers_comparison_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    for r_end, m, s, n in zip(rs, means, stds, counts):
        print(f"r_end={r_end}: <t90>={m:.3f} s, std={s:.3f} s, n={n}")
    if empty_mean is not None:
        print(f"mesa vacia: <t90>={empty_mean:.3f} s, std={empty_std:.3f} s, n={empty_n}")
    if rs:
        best = min(range(len(rs)), key=lambda i: means[i])
        print(f"Mejor radio de paragolpes explorado: r_end={rs[best]} con <t90>={means[best]:.3f} s")
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
