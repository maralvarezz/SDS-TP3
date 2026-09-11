"""Punto 1.1: orquesta corridas de mesa vacia variando N y grafica tiempo de ejecucion.

Java no conoce este experimento ni recibe argumentos por linea de comando: cada
corrida se dispara reescribiendo la unica fuente de verdad, input/config.json,
y ejecutando el jar sin argumentos. El config original se restaura al final.
"""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"

# Parametros del punto 1.1: mesa vacia (K=0), tf=30s, N variable, >=10 realizaciones por N.
N_VALUES = [25, 50, 100, 150, 200, 250, 300]
REALIZATIONS = 10
MAX_TIME = 30.0
BASE_SEED = 20260911
RETRIES = 5


def build_config(base, n, seed):
    cfg = json.loads(json.dumps(base))
    cfg.pop("obstaclesFile", None)  # esta corrida fija sus propios obstaculos inline (mesa vacia)
    cfg["simulation"]["maxTime"] = MAX_TIME
    cfg["simulation"]["seed"] = seed
    cfg["particles"]["count"] = n
    cfg["output"] = {"everyEvents": 1_000_000, "writeStates": False,
                      "writeGoals": False, "writeCollisions": False}
    cfg["obstacles"] = []
    return cfg


def run_once(n, seed):
    CONFIG_PATH.write_text(json.dumps(build_config(json.loads(CONFIG_PATH.read_text(encoding="utf-8")), n, seed)),
                            encoding="utf-8")
    result = subprocess.run(["java", "-jar", str(JAR)], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Corrida fallida (N={n}, seed={seed}): {result.stderr.strip() or result.stdout.strip()}")
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
    return metadata["runtimeMilliseconds"]


def run_with_retries(n, seed):
    last_error = None
    for attempt in range(RETRIES):
        try:
            return run_once(n, seed + attempt * 7919)
        except RuntimeError as error:
            last_error = error
            print(f"  intento {attempt + 1}/{RETRIES} fallo: {error}")
    raise last_error


def realize():
    runtimes = {n: [] for n in N_VALUES}
    for n in N_VALUES:
        for r in range(REALIZATIONS):
            seed = BASE_SEED + n * 1000 + r
            runtime = run_with_retries(n, seed)
            runtimes[n].append(runtime)
            print(f"N={n} realizacion {r + 1}/{REALIZATIONS} seed={seed} runtime={runtime} ms")
    return runtimes


def plot(runtimes):
    ns = [n for n in N_VALUES if runtimes[n]]
    if not ns:
        raise ValueError("No hay corridas completadas para graficar")
    means = [mean(runtimes[n]) for n in ns]
    stds = [pstdev(runtimes[n]) if len(runtimes[n]) > 1 else 0.0 for n in ns]
    for n, m, s in zip(ns, means, stds):
        print(f"N={n}: {len(runtimes[n])} corridas, media={m:.1f} ms, std={s:.1f} ms")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.errorbar(ns, means, yerr=stds, fmt="o-", capsize=4, color="tab:blue")
    ax.set(xlabel="N (particulas)", ylabel="Tiempo de ejecucion [ms]",
           title="Punto 1.1 - Tiempo de ejecucion vs N (mesa vacia, tf=30s)")
    ax.grid(alpha=0.25)
    folder = OUTPUT / "experiment_1_1_plots"
    folder.mkdir(exist_ok=True)
    fig.tight_layout()
    path = folder / f"execution_time_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    return path


def main():
    if not JAR.exists():
        raise FileNotFoundError(f"No se encontro el jar compilado: {JAR}. Ejecutar 'mvn -q clean package' primero")
    original = CONFIG_PATH.read_text(encoding="utf-8")
    try:
        runtimes = realize()
        plot(runtimes)
    finally:
        CONFIG_PATH.write_text(original, encoding="utf-8")
        print(f"input/config.json restaurado a su contenido original")


if __name__ == "__main__":
    main()
