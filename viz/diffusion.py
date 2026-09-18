"""Punto 1.3: desplazamiento cuadratico medio (DCM) y coeficiente de difusion (D).

Enunciado: calcular el DCM promediando sobre todas las particulas moviles
(frescas y usadas), ajustar linealmente segun Teorica 0 para obtener D,
reportar D para la mesa vacia y para las otras configuraciones estudiadas, y
verificar si hay correlacion entre D y <t90>.

Configuraciones estudiadas: las mejores de cada metodologia del punto 1.2
(mismas etiquetas y colores que el grafico conjunto de Fu(t), ver
fu_curves.CONFIG_COLORS). Sus obstaculos se toman de los propios scripts de
1.2 para no duplicar las definiciones.

Metodologia segun docs/Teorica_0.pdf (slide 38, "Difusion: Random Walk"):

- El sistema es 2D, por lo que la convencion de la catedra es <z^2> = 4 D t.
- "Para calcular ese coeficiente, no alcanza una trayectoria. Se deben
  simular muchas y promediar el desplazamiento cuadratico." Por eso cada
  configuracion se corre REALIZATIONS veces (seeds distintas) y se promedia el
  desplazamiento cuadratico sobre todas las particulas y todas las
  realizaciones:

    DCM(t) = (1/N) * sum_i |r_i(t) - r_i(0)|^2      (por realizacion)

  Como los eventos caen en instantes distintos en cada corrida, cada DCM_run(t)
  se interpola sobre una grilla temporal comun antes de promediar.
- Ajuste lineal sobre el tramo de crecimiento: D = pendiente / 4.

La mesa (L=1.20 x W=0.68 m) es chica: el DCM satura por confinamiento en
pocos segundos, muy antes de cualquier fraccion fija del tiempo total. Teorica_0
no especifica una ventana de ajuste, asi que se la define en funcion del valor
del DCM: entre FIT_LOW y FIT_HIGH fracciones del valor de saturacion (media del
DCM sobre el ultimo PLATEAU_TAIL_FRACTION del tiempo simulado), evitando el
arranque balistico y la zona ya saturada.

<t90> de cada configuracion = promedio de t90 sobre las mismas REALIZATIONS
corridas usadas para el DCM (no se usan valores copiados de otros scripts).

Java no conoce este experimento ni recibe argumentos por linea de comando: cada
corrida se dispara reescribiendo la unica fuente de verdad, input/config.json,
y ejecutando el jar sin argumentos. El config original se restaura al final.
"""
import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path
from statistics import mean, pstdev

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import configuration_comparison as position_exp
import corridor_comparison as corridor_exp
import flanking_circles_comparison as flanking_exp
import fu_curves
import goal_bumpers_comparison as bumpers_exp
import radius_comparison as radius_exp
from obstacle_layouts import validate_layout

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"

N = 100
MAX_TIME = 100.0
EVERY_EVENTS = 25
REALIZATIONS = 10
BASE_SEED = 20270000
GRID_POINTS = 500

FIT_LOW_FRACTION = 0.15
FIT_HIGH_FRACTION = 0.65
PLATEAU_TAIL_FRACTION = 0.20

BEST_RADIUS = 0.339

BUILDERS = {
    "mesa_vacia": lambda length, width, goal: [],
    "x=0.6": lambda length, width, goal: [
        {"x": radius_exp.BEST_X, "y": width / 2, "radius": position_exp.OBSTACLE_RADIUS}],
    "embudo_r=0.02": lambda length, width, goal: flanking_exp.layout(0.02, length, width),
    "R=0.339": lambda length, width, goal: [
        {"x": length / 2, "y": width / 2, "radius": BEST_RADIUS}],
    "paragolpes_r=0.02": lambda length, width, goal: bumpers_exp.layout(0.02, length, width, goal),
    "pasillo_r=0.03": lambda length, width, goal: corridor_exp.layout(0.03, length, width),
}
CONFIGS = list(BUILDERS)


def build_config(base, obstacles, seed):
    cfg = json.loads(json.dumps(base))
    cfg.pop("obstaclesFile", None)  # esta corrida fija sus propios obstaculos inline
    cfg.pop("initialPositionsFile", None)  # esta corrida usa colocacion aleatoria por defecto
    cfg["simulation"]["maxTime"] = MAX_TIME
    cfg["simulation"]["seed"] = seed
    cfg["particles"]["count"] = N
    cfg["output"] = {"everyEvents": EVERY_EVENTS, "writeStates": True,
                      "writeGoals": False, "writeCollisions": False}
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


def diffusion_coefficient(grid, msd):
    tail = grid >= (1 - PLATEAU_TAIL_FRACTION) * grid[-1]
    plateau = msd[tail].mean()
    lo_value, hi_value = FIT_LOW_FRACTION * plateau, FIT_HIGH_FRACTION * plateau
    mask = (msd >= lo_value) & (msd <= hi_value)
    if mask.sum() < 2:
        raise ValueError(f"Ventana de ajuste sin suficientes puntos (plateau={plateau})")
    slope, intercept = np.polyfit(grid[mask], msd[mask], 1)
    d = slope / 4
    return d, slope, intercept, (grid[mask][0], grid[mask][-1])


def run_config(base, label, obstacles, config_index):
    grid = np.linspace(0.0, MAX_TIME, GRID_POINTS)
    runs, t90s = [], []
    for i in range(REALIZATIONS):
        seed = BASE_SEED + config_index * 1000 + i
        directory, metadata = run_once(base, obstacles, seed)
        times, msd = msd_curve(directory)
        if times[-1] < MAX_TIME:
            raise ValueError(f"{label} seed={seed}: la corrida no llego a maxTime")
        if metadata["t90"] is None:
            raise ValueError(f"{label} seed={seed}: no alcanzo t90 antes de maxTime")
        runs.append((times, msd))
        t90s.append(metadata["t90"])
        print(f"  seed={seed} t90={metadata['t90']:.3f} frames={len(times)}")
    msd_mean = np.stack([np.interp(grid, times, msd) for times, msd in runs]).mean(axis=0)
    d, slope, intercept, window = diffusion_coefficient(grid, msd_mean)
    return {"grid": grid, "msd": msd_mean, "runs": runs, "d": d, "slope": slope,
            "intercept": intercept, "window": window,
            "t90_mean": mean(t90s), "t90_std": pstdev(t90s)}


def slug(label):
    return re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_")


def plot_msd(label, result, empty):
    color = fu_curves.CONFIG_COLORS[label]
    lo, hi = result["window"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for times, run_msd in result["runs"]:
        ax.plot(times, run_msd, color="0.8", linewidth=0.8, zorder=1)
    if label != "mesa_vacia":
        ax.plot(empty["grid"], empty["msd"], color=fu_curves.CONFIG_COLORS["mesa_vacia"], alpha=0.5,
                linewidth=1.6, zorder=2, label="Mesa vacia (DCM promedio)")
    ax.plot(result["grid"], result["msd"], color=color, linewidth=1.8, zorder=3,
            label=f"DCM(t) promedio ({len(result['runs'])} realizaciones)")
    fit_ts = np.array([lo, hi])
    ax.plot(fit_ts, result["slope"] * fit_ts + result["intercept"], color="black", linestyle="--",
            linewidth=1.6, zorder=4, label=f"ajuste [{lo:.1f}, {hi:.1f}] s: D={result['d']:.6f} m^2/s")
    ax.set(xlabel="Tiempo simulado [s]", ylabel="DCM [m^2]", title=f"Punto 1.3 - DCM - {label}")
    ax.grid(alpha=0.25)
    ax.legend()
    folder = OUTPUT / "experiment_1_3_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"msd_{slug(label)}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)


def plot_correlation(results):
    fig, ax = plt.subplots(figsize=(7, 4.8))
    for label in CONFIGS:
        r = results[label]
        color = fu_curves.CONFIG_COLORS[label]
        ax.errorbar(r["t90_mean"], r["d"], xerr=r["t90_std"], fmt="o", color=color, capsize=3,
                    markersize=7, label=label)
    ax.set(xlabel="<t90> [s]", ylabel="D [m^2/s]", title="Punto 1.3 - Correlacion D vs <t90>")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    folder = OUTPUT / "experiment_1_3_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"diffusion_vs_t90_{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)


def main():
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
            results[label] = run_config(base, label, obstacles, c)
            r = results[label]
            print(f"  D={r['d']:.6f} m^2/s (ventana {r['window'][0]:.1f}-{r['window'][1]:.1f} s), "
                  f"<t90>={r['t90_mean']:.3f} +- {r['t90_std']:.3f} s")
        for label in CONFIGS:
            plot_msd(label, results[label], results["mesa_vacia"])
        plot_correlation(results)
        ds = [results[label]["d"] for label in CONFIGS]
        ts = [results[label]["t90_mean"] for label in CONFIGS]
        print("\nResumen:")
        for label in CONFIGS:
            r = results[label]
            print(f"  {label}: D={r['d']:.6f} m^2/s, <t90>={r['t90_mean']:.3f} +- {r['t90_std']:.3f} s")
        print(f"Correlacion de Pearson D vs <t90> ({len(CONFIGS)} configuraciones): "
              f"r={np.corrcoef(ds, ts)[0, 1]:.3f}")
    finally:
        CONFIG_PATH.write_text(original, encoding="utf-8")
        print("input/config.json restaurado a su contenido original")


if __name__ == "__main__":
    main()
