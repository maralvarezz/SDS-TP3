"""Punto 1.2: familia "competencia" -- dos semicirculos libres frente a cada
arco (centrados en (0, W/2) y (L, W/2)) y el resto de la mesa cubierto por un
relleno de obstaculos chicos empaquetados hexagonalmente (ver
filler_layout.py para el detalle geometrico y la justificacion de por que
esto alcanza para bloquear la generacion de particulas fuera de los
semicirculos, via el propio RSA de InitialStateGenerator.java).

Se barre el radio de los semicirculos libres (free_radius): a mayor
free_radius, menos relleno hace falta y mas area queda disponible para las
N=100 particulas; a menor free_radius, el relleno crece y el RSA tarda mas
en poder ubicar a todas las particulas (o directamente no puede).

Rango de free_radius usado: se corrio un chequeo de factibilidad en Python
puro (replicando el algoritmo de RSA de Java sin necesitar el motor) para
elegir el rango sin necesidad de gastar corridas Java en configuraciones
que fueran a fallar:
  - free_radius <= 0.22 m: el RSA no siempre logra ubicar las 100 particulas
    dentro del limite de 100_000 intentos por particula (falla tipicamente
    entre la particula 60 y 95 de 100).
  - free_radius >= 0.24 m: el RSA ubica las 100 particulas de forma holgada
    (unos pocos miles de intentos totales como mucho, muy por debajo del
    limite).
  - free_radius <= 0.32 m: el semicirculo se mantiene a mas de 0.02 m de las
    paredes horizontales (W/2 = 0.34 m), sin tocarlas.
Por eso el barrido usa el rango [0.24, 0.32] m.

Restriccion (ii) (Rk >= r y permite generar las N particulas) verificada
para filler_radius=0.02 y todo el rango de free_radius de este script; ver
docstring de filler_layout.py.

N=100, maxTime=100s (mismos parametros que el resto de los scripts de 1.2).
Cada configuracion tiene ~300-400 obstaculos de relleno, mucho mas que el
resto de las familias de 1.2, asi que cada corrida Java es bastante mas
lenta por la cantidad de eventos particula-obstaculo. Se usa el minimo de
5 realizaciones del enunciado (en vez de mas) para no alargar demasiado el
tiempo de corrida.

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
from filler_layout import goal_semicircle_layout, FILLER_RADIUS

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"

N = 100
MAX_TIME = 100.0
FREE_RADII = [0.24, 0.26, 0.28, 0.30, 0.32]
REALIZATIONS = 5  # minimo del enunciado para el punto 1.2
BASE_SEED = 20261700
RETRIES = 5


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
        raise RuntimeError(f"Corrida fallida (K={len(obstacles)} obstaculos, seed={seed}): "
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

    results = {"empty": [], "free_radius": {}}
    for i in range(REALIZATIONS):
        seed = BASE_SEED + i
        print(f"mesa vacia realizacion {i + 1}/{REALIZATIONS} seed={seed}")
        metadata, directory = run_with_retries(base, [], seed)
        results["empty"].append(metadata)
        print(f"  t90={metadata['t90']}")
        if i == 0:
            fu_curves.save_curve("mesa_vacia", directory, metadata)

    for r in FREE_RADII:
        obstacles = goal_semicircle_layout(r, length, width)
        validate_layout(obstacles, length, width, particle_radius)
        print(f"free_radius={r}: K={len(obstacles)} obstaculos de relleno (radio {FILLER_RADIUS} c/u)")
        runs = []
        for i in range(REALIZATIONS):
            seed = BASE_SEED + int(round(r * 10000)) + i
            print(f"free_radius={r} realizacion {i + 1}/{REALIZATIONS} seed={seed}")
            metadata, directory = run_with_retries(base, obstacles, seed)
            runs.append(metadata)
            print(f"  t90={metadata['t90']}")
            if i == 0:
                fu_curves.save_curve(f"competencia_R={r}", directory, metadata)
        results["free_radius"][r] = runs
    return results


def plot(results):
    empty_mean, empty_std, empty_n = t90_stats(results["empty"], "mesa vacia")
    rs, means, stds, counts = [], [], [], []
    for r in sorted(results["free_radius"]):
        m, s, n = t90_stats(results["free_radius"][r], f"free_radius={r}")
        if m is None:
            continue
        rs.append(r)
        means.append(m)
        stds.append(s)
        counts.append(n)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.errorbar(rs, means, yerr=stds, fmt="o-", capsize=4, color="tab:brown",
                label="Competencia: relleno + 2 semicirculos libres frente a los arcos")
    if empty_mean is not None:
        ax.axhline(empty_mean, color="tab:blue", linestyle="--", label=f"Mesa vacia (<t90>={empty_mean:.2f} s)")
        ax.axhspan(empty_mean - empty_std, empty_mean + empty_std, color="tab:blue", alpha=0.15)
    ax.set(xlabel="Radio de los semicirculos libres frente a los arcos [m]", ylabel="<t90> [s]",
           title=f"Punto 1.2 - Competencia: <t90> vs radio libre frente a los arcos (N={N})")
    ax.grid(alpha=0.25)
    ax.legend()
    folder = OUTPUT / "experiment_1_2_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"goal_semicircle_comparison_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    for r, m, s, n in zip(rs, means, stds, counts):
        print(f"free_radius={r}: <t90>={m:.3f} s, std={s:.3f} s, n={n}")
    if empty_mean is not None:
        print(f"mesa vacia: <t90>={empty_mean:.3f} s, std={empty_std:.3f} s, n={empty_n}")
    if rs:
        best = min(range(len(rs)), key=lambda i: means[i])
        print(f"Mejor radio libre explorado: free_radius={rs[best]} con <t90>={means[best]:.3f} s")
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
