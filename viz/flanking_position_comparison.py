"""Punto 1.2: familia "objeto centrado + 2 pelotas iguales a los costados"
(embudo), variando ahora la posicion de los dos circulos chicos en vez de su
radio. Se fija el radio chico en el mejor valor ya encontrado en
flanking_circles_comparison.py (r=0.02, el que dio menor <t90>) y se separa
simetricamente ambos circulos chicos del circulo grande a lo largo del eje x,
manteniendolos siempre centrados en y=W/2.

Se parametriza la posicion por la distancia (gap) entre el centro del
circulo grande (x=L/2) y el centro de cada circulo chico: los chicos quedan
en x = L/2 -+ gap. El minimo geometrico es la tangencia con el circulo
grande (gap = R_big + r_small); se barre gap desde ahi hasta cerca de la
pared, dejando un margen para no solapar ni tocar el borde exactamente.

Restricciones (mismas que el resto de 1.2):
i.  K=3 obstaculos integramente dentro del dominio y sin solaparse entre si.
    Contencion: r_small <= x_small <= L - r_small, es decir
    gap <= L/2 - r_small.
ii. Rk >= r_particula y que permita generar las N particulas (ya validado
    para R_big y r_small en radius_comparison.py / flanking_circles_comparison.py).

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
from observables import t90_from_goals
from obstacle_layouts import validate_layout

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"

N = 100
MAX_TIME = 100.0
BIG_RADIUS = 0.335  # mismo radio grande que flanking_circles_comparison.py
SMALL_RADIUS = 0.02  # mejor radio chico encontrado en flanking_circles_comparison.py
GAPS = [0.36, 0.39, 0.42, 0.45, 0.48, 0.51]  # distancia centro-a-centro (circulo grande -> chico)
WALL_MARGIN = 0.05  # se evita tocar exactamente la pared para no generar casos limite
REALIZATIONS = 5  # minimo del enunciado para el punto 1.2
BASE_SEED = 20261600
RETRIES = 5


def layout(gap, length, width):
    y = width / 2
    x_big = length / 2
    return [
        {"x": x_big, "y": y, "radius": BIG_RADIUS},
        {"x": x_big - gap, "y": y, "radius": SMALL_RADIUS},
        {"x": x_big + gap, "y": y, "radius": SMALL_RADIUS},
    ]


def build_config(base, obstacles, seed):
    cfg = json.loads(json.dumps(base))
    cfg.pop("obstaclesFile", None)
    cfg.pop("initialPositionsFile", None)
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

    tangent_gap = BIG_RADIUS + SMALL_RADIUS
    max_gap = length / 2 - SMALL_RADIUS - WALL_MARGIN
    print(f"Gap minimo (tangencia): {tangent_gap:.4f} m; gap maximo geometrico: {max_gap:.4f} m")
    for gap in GAPS:
        if gap < tangent_gap:
            raise ValueError(f"gap={gap} < tangencia={tangent_gap:.4f} (solaparia con el circulo grande)")
        if gap > max_gap:
            raise ValueError(f"gap={gap} > maximo geometrico={max_gap:.4f} (saldria del dominio)")

    results = {"empty": [], "gaps": {}}
    for i in range(REALIZATIONS):
        seed = BASE_SEED + i
        print(f"mesa vacia realizacion {i + 1}/{REALIZATIONS} seed={seed}")
        metadata, directory = run_with_retries(base, [], seed)
        results["empty"].append(metadata)
        print(f"  t90={metadata['t90']}")
        if i == 0:
            fu_curves.save_curve("mesa_vacia", directory, metadata)

    for gap in GAPS:
        obstacles = layout(gap, length, width)
        validate_layout(obstacles, length, width, particle_radius)
        print(f"gap={gap}: obstaculos={obstacles}")
        runs = []
        for i in range(REALIZATIONS):
            seed = BASE_SEED + int(round(gap * 10000)) + i
            print(f"gap={gap} realizacion {i + 1}/{REALIZATIONS} seed={seed}")
            metadata, directory = run_with_retries(base, obstacles, seed)
            runs.append(metadata)
            print(f"  t90={metadata['t90']}")
            if i == 0:
                fu_curves.save_curve(f"embudo_gap={gap}", directory, metadata)
        results["gaps"][gap] = runs
    return results


def plot(results):
    empty_mean, empty_std, empty_n = t90_stats(results["empty"], "mesa vacia")
    gaps, means, stds, counts = [], [], [], []
    for gap in sorted(results["gaps"]):
        m, s, n = t90_stats(results["gaps"][gap], f"gap={gap}")
        if m is None:
            continue
        gaps.append(gap)
        means.append(m)
        stds.append(s)
        counts.append(n)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.errorbar(gaps, means, yerr=stds, fmt="o-", capsize=4, color="tab:purple",
                label=f"Circulo grande (R={BIG_RADIUS}) + 2 chicos (r={SMALL_RADIUS}), separacion variable")
    if empty_mean is not None:
        ax.axhline(empty_mean, color="tab:blue", linestyle="--", label=f"Mesa vacia (<t90>={empty_mean:.2f} s)")
        ax.axhspan(empty_mean - empty_std, empty_mean + empty_std, color="tab:blue", alpha=0.15)
    ax.set(xlabel="Distancia centro-a-centro circulo grande -> circulos chicos [m]", ylabel="<t90> [s]",
           title=f"Punto 1.2 - Embudo: <t90> vs posicion de los circulos chicos (N={N})")
    ax.grid(alpha=0.25)
    ax.legend()
    folder = OUTPUT / "experiment_1_2_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"flanking_position_comparison_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    for gap, m, s, n in zip(gaps, means, stds, counts):
        print(f"gap={gap}: <t90>={m:.3f} s, std={s:.3f} s, n={n}")
    if empty_mean is not None:
        print(f"mesa vacia: <t90>={empty_mean:.3f} s, std={empty_std:.3f} s, n={empty_n}")
    if gaps:
        best = min(range(len(gaps)), key=lambda i: means[i])
        print(f"Mejor separacion explorada: gap={gaps[best]} con <t90>={means[best]:.3f} s")
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
