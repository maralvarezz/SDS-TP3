"""Punto 1.2: arreglo tipo "embudo hacia los arcos" (una de las metodologias
sugeridas en el enunciado): un circulo grande centrado en la mesa (x=L/2,
y=W/2), con el mejor radio ya encontrado en radius_comparison.py (R=0.335),
mas dos circulos iguales a los costados, tangentes al circulo grande y
centrados tambien en y=W/2, cerca de cada arco.

Se barre el radio r de los dos circulos chicos (iguales entre si) para ver
si mejora <t90> respecto de usar solo el circulo grande. Restricciones:

i.  K=3 obstaculos integramente dentro del dominio y sin solaparse entre si.
    Con el circulo grande tangente a las paredes horizontales y centrado en
    x=L/2, los circulos chicos tangentes a el quedan en
    x = L/2 -+ (R_big + r); la restriccion de contencion (Rk<=xk<=L-Rk) fija
    el maximo geometrico: r <= (L/2 - R_big) / 2.
ii. Rk >= r_particula y que permita generar las N particulas (se verifica
    empiricamente antes de correr el experimento completo).

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
BIG_RADIUS = 0.335  # mejor radio encontrado en radius_comparison.py
SMALL_RADII = [0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.13]
MARGIN = 1.001  # separa apenas mas que la tangencia exacta, evita solapar por redondeo
REALIZATIONS = 10
BASE_SEED = 20261500
RETRIES = 5


def layout(small_radius, length, width):
    y = width / 2
    x_big = length / 2
    gap = (BIG_RADIUS + small_radius) * MARGIN
    return [
        {"x": x_big, "y": y, "radius": BIG_RADIUS},
        {"x": x_big - gap, "y": y, "radius": small_radius},
        {"x": x_big + gap, "y": y, "radius": small_radius},
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

    max_small = (length / 2 - BIG_RADIUS) / 2
    print(f"Radio maximo geometrico para los circulos chicos: {max_small:.4f} m")

    results = {"empty": []}
    for i in range(REALIZATIONS):
        seed = BASE_SEED + i
        print(f"mesa vacia realizacion {i + 1}/{REALIZATIONS} seed={seed}")
        metadata, directory = run_with_retries(base, [], seed)
        results["empty"].append(metadata)
        print(f"  t90={metadata['t90']}")
        if i == 0:
            fu_curves.save_curve("mesa_vacia", directory, metadata)

    for r in SMALL_RADII:
        obstacles = layout(r, length, width)
        validate_layout(obstacles, length, width, particle_radius)
        print(f"r_small={r}: obstaculos={obstacles}")
        runs = []
        for i in range(REALIZATIONS):
            seed = BASE_SEED + int(round(r * 10000)) + i
            print(f"r_small={r} realizacion {i + 1}/{REALIZATIONS} seed={seed}")
            metadata, directory = run_with_retries(base, obstacles, seed)
            runs.append(metadata)
            print(f"  t90={metadata['t90']}")
            if i == 0:
                fu_curves.save_curve(f"embudo_r={r}", directory, metadata)
        results[r] = runs
    return results


def plot(results):
    empty_mean, empty_std, empty_n = t90_stats(results["empty"], "mesa vacia")
    rs, means, stds, counts = [], [], [], []
    for r in SMALL_RADII:
        m, s, n = t90_stats(results[r], f"r_small={r}")
        if m is None:
            continue
        rs.append(r)
        means.append(m)
        stds.append(s)
        counts.append(n)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.errorbar(rs, means, yerr=stds, fmt="o-", capsize=4, color="tab:green",
                label=f"Circulo grande (R={BIG_RADIUS}) + 2 circulos iguales")
    if empty_mean is not None:
        ax.axhline(empty_mean, color="tab:blue", linestyle="--", label=f"Mesa vacia (<t90>={empty_mean:.2f} s)")
        ax.axhspan(empty_mean - empty_std, empty_mean + empty_std, color="tab:blue", alpha=0.15)
    ax.set(xlabel="Radio de los circulos chicos [m]", ylabel="<t90> [s]",
           title=f"Punto 1.2 - Embudo: circulo grande + 2 chicos (N={N})")
    ax.grid(alpha=0.25)
    ax.legend()
    folder = OUTPUT / "experiment_1_2_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"flanking_circles_comparison_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    for r, m, s, n in zip(rs, means, stds, counts):
        print(f"r_small={r}: <t90>={m:.3f} s, std={s:.3f} s, n={n}")
    if empty_mean is not None:
        print(f"mesa vacia: <t90>={empty_mean:.3f} s, std={empty_std:.3f} s, n={empty_n}")
    if rs:
        best = min(range(len(rs)), key=lambda i: means[i])
        print(f"Mejor radio chico explorado: r_small={rs[best]} con <t90>={means[best]:.3f} s")
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
