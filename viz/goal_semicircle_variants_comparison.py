"""Punto 1.2: familia "competencia", variantes de la geometria de la zona
libre. Sigue a goal_semicircle_comparison.py (que barrio el radio del
semicirculo libre y encontro un minimo en free_radius=0.30 m,
<t90>=13.16 s, bastante por debajo de mesa vacia pero con una meseta ancha
entre 0.28 y 0.32).

Hipotesis de por que un free_radius mas chico daba peor <t90> en vez de
mejor: con menos area, las 100 particulas quedan mas apretadas y las
colisiones particula-particula las traban entre si antes de que lleguen a
la pared (el "narrow escape problem" clasico predice lo contrario -- cavidad
mas chica con salida fija deberia drenar mas rapido -- asi que el
apinamiento parece dominar sobre la ventaja de apuntado). Estas variantes
atacan el "apuntado" sin volver a reducir el area (ver filler_layout.py):

- "semicircle": el mejor caso ya medido (free_radius=0.30), como base de
  comparacion.
- "funnel": la zona libre es un embudo que calza exactamente con el ancho
  del arco en la pared (elimina la "pared muerta" del semicirculo) y tiene
  MAS area total que el semicirculo (0.36 m^2 vs 0.2827 m^2), para no volver
  a apianar.
- "semicircle_guides": semicirculo R=0.30 + 2 obstaculos guia por arco justo
  afuera de sus bordes (misma idea que el "paragolpes" descartado de la
  familia B), para desviar particulas hacia el arco.
- "funnel_guides": combina las dos ideas anteriores.

N=100, maxTime=100s, 5 realizaciones por configuracion (el minimo del
enunciado, para no alargar demasiado el tiempo de corrida, para comparar en igualdad de condiciones -- ver
goal_semicircle_comparison.py).

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
from filler_layout import family_c_layout

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"

N = 100
MAX_TIME = 100.0
VARIANTS = ["semicircle", "funnel", "semicircle_guides", "funnel_guides"]
VARIANT_LABELS = {
    "semicircle": "Semicirculo\n(R=0.30, base)",
    "funnel": "Embudo\n(ancho=arco)",
    "semicircle_guides": "Semicirculo\n+ guias",
    "funnel_guides": "Embudo\n+ guias",
}
REALIZATIONS = 5  # minimo del enunciado para el punto 1.2
BASE_SEED = 20265100
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
    goal_size = base["simulation"]["goalSize"]
    particle_radius = base["particles"]["radius"]

    results = {"empty": [], "variants": {}}
    for i in range(REALIZATIONS):
        seed = BASE_SEED + i
        print(f"mesa vacia realizacion {i + 1}/{REALIZATIONS} seed={seed}")
        metadata, directory = run_with_retries(base, [], seed)
        results["empty"].append(metadata)
        print(f"  t90={metadata['t90']}")
        if i == 0:
            fu_curves.save_curve("mesa_vacia", directory, metadata)

    for v_index, variant in enumerate(VARIANTS):
        obstacles = family_c_layout(variant, length, width, goal_size)
        validate_layout(obstacles, length, width, particle_radius)
        print(f"variante={variant}: K={len(obstacles)} obstaculos")
        runs = []
        for i in range(REALIZATIONS):
            seed = BASE_SEED + 100_000 * (v_index + 1) + i
            print(f"variante={variant} realizacion {i + 1}/{REALIZATIONS} seed={seed}")
            metadata, directory = run_with_retries(base, obstacles, seed)
            runs.append(metadata)
            print(f"  t90={metadata['t90']}")
            if i == 0:
                fu_curves.save_curve(f"competencia_{variant}", directory, metadata)
        results["variants"][variant] = runs
    return results


def plot(results):
    empty_mean, empty_std, empty_n = t90_stats(results["empty"], "mesa vacia")
    labels, means, stds, counts = [], [], [], []
    for variant in VARIANTS:
        m, s, n = t90_stats(results["variants"][variant], variant)
        labels.append(VARIANT_LABELS[variant])
        means.append(m if m is not None else float("nan"))
        stds.append(s if s is not None else 0.0)
        counts.append(n)

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    xs = range(len(labels))
    ax.bar(xs, means, yerr=stds, capsize=5, color="tab:brown", alpha=0.75)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, fontsize=9)
    if empty_mean is not None:
        ax.axhline(empty_mean, color="tab:blue", linestyle="--", label=f"Mesa vacia (<t90>={empty_mean:.2f} s)")
        ax.axhspan(empty_mean - empty_std, empty_mean + empty_std, color="tab:blue", alpha=0.15)
    ax.set(ylabel="<t90> [s]", title=f"Punto 1.2 - Competencia: variantes de zona libre (N={N})")
    ax.grid(alpha=0.25, axis="y")
    ax.legend()
    folder = OUTPUT / "experiment_1_2_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"goal_semicircle_variants_comparison_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    for variant, m, s, n in zip(VARIANTS, means, stds, counts):
        print(f"{variant}: <t90>={m:.3f} s, std={s:.3f} s, n={n}")
    if empty_mean is not None:
        print(f"mesa vacia: <t90>={empty_mean:.3f} s, std={empty_std:.3f} s, n={empty_n}")
    best = min(range(len(VARIANTS)), key=lambda i: means[i])
    print(f"Mejor variante: {VARIANTS[best]} con <t90>={means[best]:.3f} s")
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
