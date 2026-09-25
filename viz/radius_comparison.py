"""Punto 1.2: continua la exploracion de configuration_comparison.py.

Esa corrida barrio la posicion x de un unico obstaculo (K=1) con R=0.15 fijo,
y encontro que x=L/2=0.60 m (centrado) minimiza <t90>. Este script fija esa
posicion (x=L/2, y=W/2) y barre el radio R, para ver si el resultado mejora
mas variando el tamano del obstaculo.

Restriccion (ii) del enunciado: Rk >= r y tal que permita la generacion de
las N particulas. r=0.0175 m (input/config.json). Se verifica ademas, para
cada R candidato, la restriccion (i) de contencion: con el obstaculo
centrado en y=W/2, la cota "Rk <= yk <= W - Rk" exige R <= W/2 = 0.34 m; por
eso el barrido no llega a ese valor (se detiene en R=0.335, ya verificado
empiricamente que sigue permitiendo generar las 100 particulas).

N=100, maxTime=100s (mismos parametros que configuration_comparison.py, ver
ese script para la justificacion de tmax). La mesa vacia se recalcula en esta
misma corrida (no se reutiliza el valor de otro script) para que la
comparacion sea internamente consistente.

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

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"

N = 100
MAX_TIME = 100.0
BEST_X = 0.60  # encontrado en configuration_comparison.py (x-sweep con R=0.15)
R_VALUES = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.325, 0.335]
REALIZATIONS = 5  # minimo del enunciado para el punto 1.2
BASE_SEED = 20261200
RETRIES = 5


def validate_radius(r, length, width, x, y, particle_radius):
    # Restriccion (ii): Rk >= r.
    if r < particle_radius:
        raise ValueError(f"Restriccion (ii) violada: R={r} < r={particle_radius}")
    # Restriccion (i): obstaculo integramente dentro del dominio.
    if not (r <= x <= length - r and r <= y <= width - r):
        raise ValueError(f"Restriccion (i) violada (fuera de dominio): x={x}, y={y}, R={r}")


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
    y = width / 2

    results = {"empty": [], "radii": {}}
    for i in range(REALIZATIONS):
        seed = BASE_SEED + i
        print(f"mesa vacia realizacion {i + 1}/{REALIZATIONS} seed={seed}")
        metadata, directory = run_with_retries(base, [], seed)
        results["empty"].append(metadata)
        print(f"  t90={metadata['t90']}")
        if i == 0:
            fu_curves.save_curve("mesa_vacia", directory, metadata)

    for r in R_VALUES:
        validate_radius(r, length, width, BEST_X, y, particle_radius)
        obstacles = [{"x": BEST_X, "y": y, "radius": r}]
        runs = []
        for i in range(REALIZATIONS):
            seed = BASE_SEED + int(round(r * 10000)) + i
            print(f"R={r} realizacion {i + 1}/{REALIZATIONS} seed={seed}")
            metadata, directory = run_with_retries(base, obstacles, seed)
            runs.append(metadata)
            print(f"  t90={metadata['t90']}")
            if i == 0:
                fu_curves.save_curve(f"R={r}", directory, metadata)
        results["radii"][r] = runs
    return results


def plot(results):
    empty_mean, empty_std, empty_n = t90_stats(results["empty"], "mesa vacia")
    rs, means, stds, counts = [], [], [], []
    for r in R_VALUES:
        m, s, n = t90_stats(results["radii"][r], f"R={r}")
        if m is None:
            continue
        rs.append(r)
        means.append(m)
        stds.append(s)
        counts.append(n)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.errorbar(rs, means, yerr=stds, fmt="o-", capsize=4, color="tab:red",
                label=f"Obstaculo unico (K=1, x={BEST_X} m, y=W/2)")
    if empty_mean is not None:
        ax.axhline(empty_mean, color="tab:blue", linestyle="--", label=f"Mesa vacia (<t90>={empty_mean:.2f} s)")
        ax.axhspan(empty_mean - empty_std, empty_mean + empty_std, color="tab:blue", alpha=0.15)
    ax.set(xlabel="Radio del obstaculo R [m]", ylabel="<t90> [s]",
           title=f"Punto 1.2 - <t90> vs radio del obstaculo (x={BEST_X} m fijo, N={N})")
    ax.grid(alpha=0.25)
    ax.legend()
    folder = OUTPUT / "experiment_1_2_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"radius_comparison_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    for r, m, s, n in zip(rs, means, stds, counts):
        print(f"R={r}: <t90>={m:.3f} s, std={s:.3f} s, n={n}")
    if empty_mean is not None:
        print(f"mesa vacia: <t90>={empty_mean:.3f} s, std={empty_std:.3f} s, n={empty_n}")
    if rs:
        best = min(range(len(rs)), key=lambda i: means[i])
        print(f"Mejor radio explorado: R={rs[best]} con <t90>={means[best]:.3f} s")
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
