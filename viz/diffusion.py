import csv
import argparse
import json
import re
import secrets
import subprocess
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

import flanking_position_comparison as flanking_pos_exp
import fu_curves
from filler_layout import goal_semicircle_layout
from observables import t90_from_goals
from obstacle_layouts import validate_layout

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"


def fmt2sf(x):
    return f"{x:.2g}"


N = 100
MAX_TIME = 100.0
EVERY_EVENTS = 25
BASE_SEED = 20270000

REALIZATIONS = 5

FIT_LOW_FRACTION = 0.0
FIT_HIGH_FRACTION = 0.50
PLATEAU_TAIL_FRACTION = 0.20

BEST_RADIUS = 0.339
BEST_FREE_RADIUS = 0.30

BUILDERS = {
    "mesa_vacia": lambda length, width, goal: [],
    "R=0.339": lambda length, width, goal: [
        {"x": length / 2, "y": width / 2, "radius": BEST_RADIUS}],
    "embudo_gap=0.45": lambda length, width, goal: flanking_pos_exp.layout(0.45, length, width),
    "competencia_R=0.3": lambda length, width, goal: goal_semicircle_layout(BEST_FREE_RADIUS, length, width),
}
CONFIGS = list(BUILDERS)


def build_config(base, obstacles, seed):
    cfg = json.loads(json.dumps(base))
    cfg.pop("obstaclesFile", None)
    cfg.pop("initialPositionsFile", None)
    cfg["simulation"]["maxTime"] = MAX_TIME
    cfg["simulation"]["seed"] = seed
    cfg["particles"]["count"] = N
    cfg["output"] = {"everyEvents": EVERY_EVENTS, "writeStates": True,
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
    return directory, metadata


def msd_curve(directory):
    states_files = list(directory.glob("states_*.csv"))
    if len(states_files) != 1:
        raise ValueError(f"Se esperaba un unico states_*.csv en {directory}")
    with states_files[0].open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    grouped = groupby(rows, key=lambda row: (float(row["time"]), int(row["event"])))
    times, msd = [], []
    initial = None
    for (time, _event), group in grouped:
        particles = {int(row["id"]): (float(row["x"]), float(row["y"])) for row in group}
        if len(particles) != N:
            raise ValueError(f"Frame incompleto en t={time}: {len(particles)}/{N} particulas")
        if initial is None:
            initial = particles
        displacement = sum((particles[i][0] - initial[i][0]) ** 2 + (particles[i][1] - initial[i][1]) ** 2
                            for i in particles) / N
        times.append(time)
        msd.append(displacement)
    return np.array(times), np.array(msd)


def diffusion_coefficient(times, msd):
    tail = times >= (1 - PLATEAU_TAIL_FRACTION) * times[-1]
    plateau = msd[tail].mean()
    lo_value, hi_value = FIT_LOW_FRACTION * plateau, FIT_HIGH_FRACTION * plateau
    mask = (msd >= lo_value) & (msd <= hi_value)
    if mask.sum() < 2:
        raise ValueError(f"Ventana de ajuste sin suficientes puntos (plateau={plateau})")
    t_window, msd_window = times[mask], msd[mask]
    slope = np.sum(t_window * msd_window) / np.sum(t_window ** 2)
    d = slope / 4
    return d, slope, 0.0, (times[mask][0], times[mask][-1])


def run_config(base, label, obstacles, config_index, random_seeds=False):
    ds, t90s = [], []
    curve = None
    for i in range(REALIZATIONS):
        if random_seeds:
            seed = secrets.randbits(63)
        else:
            seed = BASE_SEED + config_index if i == 0 else BASE_SEED + config_index * 1000 + i
        directory, metadata = run_once(base, obstacles, seed)
        times, msd = msd_curve(directory)
        if times[-1] < MAX_TIME:
            raise ValueError(f"{label} seed={seed}: la corrida no llego a maxTime")
        if metadata["t90"] is None:
            raise ValueError(f"{label} seed={seed}: no alcanzo t90 antes de maxTime")
        d, slope, intercept, window = diffusion_coefficient(times, msd)
        print(f"  seed={seed} t90={metadata['t90']:.3f} D={fmt2sf(d)} m^2/s frames={len(times)}")
        ds.append(d)
        t90s.append(metadata["t90"])
        if i == 0:
            curve = {"times": times, "msd": msd, "d": d, "slope": slope,
                     "intercept": intercept, "window": window, "t90": metadata["t90"]}
    curve["d_mean"] = float(np.mean(ds))
    curve["d_std"] = float(np.std(ds)) if len(ds) > 1 else 0.0
    curve["t90_mean"] = float(np.mean(t90s))
    curve["t90_std"] = float(np.std(t90s)) if len(t90s) > 1 else 0.0
    curve["n"] = len(ds)
    return curve


def slug(label):
    return re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_")


def plot_msd_all(results):
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    for label in CONFIGS:
        r = results[label]
        color = fu_curves.CONFIG_COLORS[label]
        display_name = fu_curves.DISPLAY_NAMES.get(label, label)
        ax.plot(r["times"], r["msd"], color=color, linewidth=1.8,
                 label=display_name)
        _, hi = r["window"]
        fit_ts = np.array([0.0, hi])
        ax.plot(fit_ts, r["slope"] * fit_ts + r["intercept"], color=color,
                 linestyle="--", linewidth=2.2, alpha=0.75, zorder=1)
    XLIM_MAX = 10.0
    ax.set_xlim(0, XLIM_MAX)
    ymax = max(r["msd"][r["times"] <= XLIM_MAX].max() for r in results.values())
    ax.set_ylim(0, ymax * 1.08)
    ax.set(xlabel="Tiempo simulado (s)", ylabel="DCM (m^2)")
    ax.yaxis.set_major_locator(MaxNLocator(nbins=12))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    folder = OUTPUT / "experiment_1_3_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"msd_all_{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    return path


def plot_correlation(results):
    fig, ax = plt.subplots(figsize=(7, 4.8))
    for label in CONFIGS:
        r = results[label]
        color = fu_curves.CONFIG_COLORS[label]
        ax.errorbar(r["t90_mean"], r["d_mean"], xerr=r["t90_std"], yerr=r["d_std"],
                    fmt="o", color=color, markersize=8, capsize=4,
                    label=fu_curves.DISPLAY_NAMES.get(label, label))
    ax.set(xlabel="t90 (s)", ylabel="D (m^2/s)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    folder = OUTPUT / "experiment_1_3_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"diffusion_vs_t90_{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    return path


def main():
    parser = argparse.ArgumentParser(description="Grafica DCM y D vs t90")
    parser.add_argument("--random-seeds", action="store_true",
                        help="Genera semillas nuevas para cada realizacion en cada ejecucion")
    args = parser.parse_args()
    if not JAR.exists():
        raise FileNotFoundError(f"No se encontro el jar compilado: {JAR}. Ejecutar 'mvn -q clean package' primero")
    base = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    length = base["simulation"]["length"]
    width = base["simulation"]["width"]
    goal = base["simulation"]["goalSize"]
    particle_radius = base["particles"]["radius"]
    original = CONFIG_PATH.read_text(encoding="utf-8")
    results = {}
    try:
        for c, label in enumerate(CONFIGS):
            obstacles = BUILDERS[label](length, width, goal)
            validate_layout(obstacles, length, width, particle_radius)
            print(f"{label}: obstaculos={obstacles}")
            results[label] = run_config(base, label, obstacles, c, random_seeds=args.random_seeds)
            r = results[label]
            print(f"  DCM(t)/ajuste (1 realizacion): D={fmt2sf(r['d'])} m^2/s "
                  f"(ventana {r['window'][0]:.1f}-{r['window'][1]:.1f} s), t90={r['t90']:.3f} s")
            print(f"  correlacion ({r['n']} realizaciones): "
                  f"D={fmt2sf(r['d_mean'])}+/-{fmt2sf(r['d_std'])} m^2/s, "
                  f"t90={r['t90_mean']:.3f}+/-{r['t90_std']:.3f} s")
        plot_msd_all(results)
        plot_correlation(results)
        ds = [results[label]["d_mean"] for label in CONFIGS]
        ts = [results[label]["t90_mean"] for label in CONFIGS]
        print("\nResumen:")
        for label in CONFIGS:
            r = results[label]
            print(f"  {label}: D={fmt2sf(r['d_mean'])}+/-{fmt2sf(r['d_std'])} m^2/s, "
                  f"t90={r['t90_mean']:.3f}+/-{r['t90_std']:.3f} s "
                  f"({r['n']} realizaciones)")
        print(f"Correlacion de Pearson D vs t90 ({len(CONFIGS)} configuraciones, "
              f"sobre las medias de {REALIZATIONS} realizaciones c/u): "
              f"r={np.corrcoef(ds, ts)[0, 1]:.3f}")
    finally:
        CONFIG_PATH.write_text(original, encoding="utf-8")
        print("input/config.json restaurado a su contenido original")


if __name__ == "__main__":
    main()
