"""Punto 1.2: explora el espacio de configuraciones de obstaculos y compara <t90>.

Metodologia elegida (una de las sugeridas en el enunciado): un unico obstaculo
grande (K=1) que se desplaza sobre el eje longitudinal (x), centrado en y=W/2.
Se reporta <t90> con barra de error (desvio estandar) vs la posicion x del
obstaculo, y se compara contra la mesa vacia (K=0), que es solo una referencia
y no una de las configuraciones exploradas (esas deben cumplir K>0 segun la
restriccion (i) del enunciado).

N=100 (fijo, segun el enunciado para el punto 1.2 en adelante). maxTime=100s,
igual que los parametros fijos de la competencia (el enunciado no fija un tf
propio para 1.2; se usa el mismo tmax que en el resto de los puntos posteriores
para poder alcanzar Fu>=0.9 de forma consistente).

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

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"

N = 100
MAX_TIME = 100.0
# Restriccion (ii): Rk >= r y que permita generar las N particulas. r=0.0175 m
# en input/config.json; R=0.15 m es "grande" pero deja area suficiente para 100
# particulas (se valido empiricamente antes de correr el experimento completo).
OBSTACLE_RADIUS = 0.15
REALIZATIONS = 5
BASE_SEED = 20260912
RETRIES = 5


def x_positions(length):
    # Restriccion (i): Rk <= xk <= L - Rk, obstaculo integramente dentro del dominio.
    low, high = OBSTACLE_RADIUS, length - OBSTACLE_RADIUS
    margin = 0.05  # se evita tocar exactamente la pared para no generar casos limite
    step = 0.10
    values = []
    x = low + margin
    while x <= high - margin + 1e-9:
        values.append(round(x, 4))
        x += step
    return values


def build_config(base, obstacles, seed, write_goals=False):
    cfg = json.loads(json.dumps(base))
    cfg.pop("obstaclesFile", None)  # esta corrida fija sus propios obstaculos inline
    cfg.pop("initialPositionsFile", None)  # esta corrida usa colocacion aleatoria por defecto
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
    y = width / 2  # centrado, simetrico respecto de los arcos en x=0 y x=L

    results = {"empty": [], "positions": {}}
    for i in range(REALIZATIONS):
        seed = BASE_SEED + i
        print(f"mesa vacia realizacion {i + 1}/{REALIZATIONS} seed={seed}")
        metadata, directory = run_with_retries(base, [], seed, write_goals=(i == 0))
        results["empty"].append(metadata)
        print(f"  t90={metadata['t90']}")
        if i == 0:
            fu_curves.save_curve("mesa_vacia", directory, metadata)

    for x in x_positions(length):
        obstacles = [{"x": x, "y": y, "radius": OBSTACLE_RADIUS}]
        runs = []
        for i in range(REALIZATIONS):
            seed = BASE_SEED + int(round(x * 1000)) + i
            print(f"x={x} realizacion {i + 1}/{REALIZATIONS} seed={seed}")
            metadata, directory = run_with_retries(base, obstacles, seed, write_goals=(i == 0))
            runs.append(metadata)
            print(f"  t90={metadata['t90']}")
            if i == 0:
                fu_curves.save_curve(f"x={x}", directory, metadata)
        results["positions"][x] = runs
    return results


def plot(results):
    empty_mean, empty_std, empty_n = t90_stats(results["empty"], "mesa vacia")
    xs, means, stds, counts = [], [], [], []
    for x in sorted(results["positions"]):
        m, s, n = t90_stats(results["positions"][x], f"x={x}")
        if m is None:
            continue
        xs.append(x)
        means.append(m)
        stds.append(s)
        counts.append(n)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.errorbar(xs, means, yerr=stds, fmt="o-", capsize=4, color="tab:blue",
                label=f"Obstaculo unico (K=1, R={OBSTACLE_RADIUS} m)")
    if empty_mean is not None:
        ax.axhline(empty_mean, color="0.4", linestyle="--", label=f"Mesa vacia (<t90>={empty_mean:.2f} s)")
        ax.axhspan(empty_mean - empty_std, empty_mean + empty_std, color="0.4", alpha=0.15)
    ax.set(xlabel="Posicion x del obstaculo [m]", ylabel="<t90> [s]",
           title=f"Punto 1.2 - <t90> vs posicion longitudinal del obstaculo (N={N})")
    ax.grid(alpha=0.25)
    ax.legend()
    folder = OUTPUT / "experiment_1_2_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"configuration_comparison_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    for x, m, s, n in zip(xs, means, stds, counts):
        print(f"x={x}: <t90>={m:.3f} s, std={s:.3f} s, n={n}")
    if empty_mean is not None:
        print(f"mesa vacia: <t90>={empty_mean:.3f} s, std={empty_std:.3f} s, n={empty_n}")
    if xs:
        best = min(range(len(xs)), key=lambda i: means[i])
        print(f"Mejor posicion explorada: x={xs[best]} con <t90>={means[best]:.3f} s")
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
