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
from filler_layout import goal_semicircle_layout, goal_ellipse_layout, ELLIPSE_B

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"

N = 100
MAX_TIME = 100.0
REFINED_RADII = [0.29, 0.30, 0.31]
ELLIPSE_A_VALUES = [0.40, 0.45, 0.50]
REALIZATIONS = 5
BASE_SEED = 20267100
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


def configs():
    items = []
    for r in REFINED_RADII:
        items.append((f"R={r}", "semicircle", r))
    for a in ELLIPSE_A_VALUES:
        items.append((f"elipse a={a}", "ellipse", a))
    return items


def realize():
    base = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    length = base["simulation"]["length"]
    width = base["simulation"]["width"]
    particle_radius = base["particles"]["radius"]

    results = {"empty": [], "configs": {}}
    for i in range(REALIZATIONS):
        seed = BASE_SEED + i
        print(f"mesa vacia realizacion {i + 1}/{REALIZATIONS} seed={seed}")
        metadata, directory = run_with_retries(base, [], seed)
        results["empty"].append(metadata)
        print(f"  t90={metadata['t90']}")
        if i == 0:
            fu_curves.save_curve("mesa_vacia", directory, metadata)

    for c_index, (label, kind, param) in enumerate(configs()):
        if kind == "semicircle":
            obstacles = goal_semicircle_layout(param, length, width)
        else:
            obstacles = goal_ellipse_layout(param, length, width, b=ELLIPSE_B)
        validate_layout(obstacles, length, width, particle_radius)
        print(f"{label}: K={len(obstacles)} obstaculos")
        runs = []
        for i in range(REALIZATIONS):
            seed = BASE_SEED + 100_000 * (c_index + 1) + i
            print(f"{label} realizacion {i + 1}/{REALIZATIONS} seed={seed}")
            metadata, directory = run_with_retries(base, obstacles, seed)
            runs.append(metadata)
            print(f"  t90={metadata['t90']}")
            if i == 0:
                curve_label = f"competencia_{'semicircle' if kind == 'semicircle' else 'ellipse'}_{param}"
                fu_curves.save_curve(curve_label, directory, metadata)
        results["configs"][label] = runs
    return results


def plot(results):
    empty_mean, empty_std, empty_n = t90_stats(results["empty"], "mesa vacia")
    labels = [label for label, _, _ in configs()]
    means, stds, counts = [], [], []
    for label in labels:
        m, s, n = t90_stats(results["configs"][label], label)
        means.append(m if m is not None else float("nan"))
        stds.append(s if s is not None else 0.0)
        counts.append(n)

    colors = ["tab:brown"] * len(REFINED_RADII) + ["tab:purple"] * len(ELLIPSE_A_VALUES)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    xs = range(len(labels))
    ax.bar(xs, means, yerr=stds, capsize=5, color=colors, alpha=0.75)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, fontsize=9)
    if empty_mean is not None:
        ax.axhline(empty_mean, color="tab:blue", linestyle="--", label=f"Mesa vacia (<t90>={empty_mean:.2f} s)")
        ax.axhspan(empty_mean - empty_std, empty_mean + empty_std, color="tab:blue", alpha=0.15)
    ax.set(ylabel="<t90> (s)", title=f"Punto 1.2 - Competencia: semicirculo fino + elipse (N={N})")
    ax.grid(alpha=0.25, axis="y")
    ax.legend()
    folder = OUTPUT / "experiment_1_2_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"goal_ellipse_comparison_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    for label, m, s, n in zip(labels, means, stds, counts):
        print(f"{label}: <t90>={m:.3f} s, std={s:.3f} s, n={n}")
    if empty_mean is not None:
        print(f"mesa vacia: <t90>={empty_mean:.3f} s, std={empty_std:.3f} s, n={empty_n}")
    best = min(range(len(labels)), key=lambda i: means[i])
    print(f"Mejor de esta ronda: {labels[best]} con <t90>={means[best]:.3f} s")
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
