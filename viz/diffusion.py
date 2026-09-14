"""Punto 1.3: desplazamiento cuadratico medio (DCM) y coeficiente de difusion (D).

Metodologia segun docs/Teorica_0.pdf (slide 38, "Difusion: Random Walk"):

- Nuestro sistema es 2D (plano x, y), por lo que la convencion de la catedra es
  <z^2> = 4 D t  (no 2 D t, que es el caso 1D).
- "Para calcular ese coeficiente, no alcanza una trayectoria. Se deben simular
  muchas y promediar el desplazamiento cuadratico." Por eso, para cada
  configuracion se corren REALIZATIONS corridas independientes (no una sola) y
  se promedia el desplazamiento cuadratico sobre TODAS las particulas moviles
  (frescas y usadas, segun el enunciado) Y sobre todas las realizaciones.

Para cada configuracion (mesa vacia y las estudiadas en el punto 1.2: K=1, K=2,
K=3 con area total fija, ver obstacle_layouts.py):

1. Se corren REALIZATIONS corridas con N=100 y distinta seed.
2. En cada corrida se calcula, por particula, el desplazamiento cuadratico
   respecto de t=0 y se promedia sobre las N particulas -> DCM_run(t).
3. Cada DCM_run(t) se interpola sobre una grilla temporal comun (los eventos
   caen en instantes distintos en cada corrida, al ser dirigida por eventos).
4. Se promedian las REALIZATIONS curvas interpoladas -> DCM(t) final.
5. Se ajusta linealmente: D = pendiente / 4.

No se ajusta sobre todo el rango temporal: se descarta el 10% inicial
(regimen balistico, dominado por v0 y no por difusion) y todo lo posterior al
60% del tiempo total (donde el DCM se satura por el tamano finito del
dominio). Esta ventana es una eleccion razonable y documentada, ya que
Teorica_0 no especifica una ventana exacta de ajuste.

La mesa (L=1.20 x W=0.68 m) es chica: el DCM satura por confinamiento en unos
pocos segundos (verificado empiricamente: para la mesa vacia el plateau se
alcanza ya en t~10 s sobre un tmax=100 s), muy antes de cualquier fraccion fija
del tiempo total. Por eso la ventana de ajuste no se define como fraccion de
tmax, sino en funcion del propio valor del DCM: se ajusta sobre el tramo de
crecimiento, entre FIT_LOW y FIT_HIGH fracciones del plateau (el valor medio
del DCM sobre el ultimo PLATEAU_TAIL_FRACTION del tiempo simulado), evitando
tanto el arranque balistico (DCM~0) como la zona ya saturada (DCM~plateau).

Se reporta D por configuracion y se lo compara contra el <t90> promedio de
cada una (obtenido en el punto 1.2, con obstacle_count_comparison.py), para
verificar si existe o no correlacion, tal como pide el enunciado.

Java no conoce este experimento ni recibe argumentos por linea de comando: cada
corrida se dispara reescribiendo la unica fuente de verdad, input/config.json,
y ejecutando el jar sin argumentos. El config original se restaura al final.
"""
import csv
import json
import subprocess
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from obstacle_layouts import layout, validate_layout

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
JAR = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
OUTPUT = ROOT / "output"

N = 100
MAX_TIME = 100.0
EVERY_EVENTS = 25
REALIZATIONS = 5
BASE_SEED = 20260930
GRID_POINTS = 500

# Ventana de ajuste lineal como fraccion del plateau (ver docstring del modulo).
FIT_LOW_FRACTION = 0.15
FIT_HIGH_FRACTION = 0.65
PLATEAU_TAIL_FRACTION = 0.20

# <t90> promedio de cada configuracion, calculado en el punto 1.2
# (obstacle_count_comparison.py) sobre 5 realizaciones.
MEAN_T90 = {
    "mesa_vacia": 22.166,
    "K1": 18.018,
    "K2": 21.702,
    "K3": 24.079,
}

CONFIGS = ["mesa_vacia", "K1", "K2", "K3"]


def obstacles_for(name, length, width, particle_radius):
    if name == "mesa_vacia":
        return []
    k = int(name[1:])
    obstacles = layout(k, length, width)
    validate_layout(obstacles, length, width, particle_radius)
    return obstacles


def build_config(base, obstacles, seed):
    cfg = json.loads(json.dumps(base))
    cfg.pop("obstaclesFile", None)  # esta corrida fija sus propios obstaculos inline
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


def linear_fit(xs, ys):
    slope, intercept = np.polyfit(xs, ys, 1)
    return slope, intercept


def diffusion_coefficient(grid, msd):
    tail = grid >= (1 - PLATEAU_TAIL_FRACTION) * grid[-1]
    plateau = msd[tail].mean()
    lo_value, hi_value = FIT_LOW_FRACTION * plateau, FIT_HIGH_FRACTION * plateau
    mask = (msd >= lo_value) & (msd <= hi_value)
    if mask.sum() < 2:
        raise ValueError(f"Ventana de ajuste sin suficientes puntos (plateau={plateau})")
    slope, intercept = linear_fit(grid[mask], msd[mask])
    d = slope / 4  # convencion 2D: <z^2> = 4 D t (Teorica_0, slide 38)
    lo_t, hi_t = grid[mask][0], grid[mask][-1]
    return d, slope, intercept, (lo_t, hi_t), plateau


def plot_msd(name, grid, msd, runs, fit):
    d, slope, intercept, (lo, hi), plateau = fit
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for times, run_msd in runs:
        ax.plot(times, run_msd, color="0.75", linewidth=0.8)
    ax.plot(grid, msd, color="tab:blue", label=f"DCM(t) promedio ({len(runs)} realizaciones)")
    fit_ts = np.array([lo, hi])
    ax.plot(fit_ts, slope * fit_ts + intercept, color="tab:red", linestyle="--",
            label=f"ajuste [{lo:.1f}, {hi:.1f}] s: D={d:.6f} m^2/s")
    ax.set(xlabel="Tiempo simulado [s]", ylabel="DCM [m^2]", title=f"Punto 1.3 - DCM - {name}")
    ax.grid(alpha=0.25)
    ax.legend()
    folder = OUTPUT / "experiment_1_3_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"msd_{name}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)


def plot_correlation(diffusion_by_config):
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for name, d in diffusion_by_config.items():
        ax.scatter(MEAN_T90[name], d, label=name)
        ax.annotate(name, (MEAN_T90[name], d), textcoords="offset points", xytext=(6, 4))
    ax.set(xlabel="<t90> [s] (punto 1.2)", ylabel="D [m^2/s]",
           title="Punto 1.3 - Correlacion D vs <t90>")
    ax.grid(alpha=0.25)
    folder = OUTPUT / "experiment_1_3_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"diffusion_vs_t90_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)


def main():
    if not JAR.exists():
        raise FileNotFoundError(f"No se encontro el jar compilado: {JAR}. Ejecutar 'mvn -q clean package' primero")
    base = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    length = base["simulation"]["length"]
    width = base["simulation"]["width"]
    particle_radius = base["particles"]["radius"]
    original = CONFIG_PATH.read_text(encoding="utf-8")
    diffusion_by_config = {}
    try:
        for c, name in enumerate(CONFIGS):
            obstacles = obstacles_for(name, length, width, particle_radius)
            print(f"{name}: obstaculos={obstacles}")
            grid = np.linspace(0.0, MAX_TIME, GRID_POINTS)
            runs = []
            for i in range(REALIZATIONS):
                seed = BASE_SEED + c * 1000 + i
                directory, metadata = run_once(base, obstacles, seed)
                times, msd = msd_curve(directory)
                if times[-1] < MAX_TIME:
                    raise ValueError(f"{name} seed={seed}: la corrida no llego a maxTime")
                runs.append((times, msd))
                print(f"  seed={seed} t90={metadata['t90']} frames={len(times)}")
            interpolated = np.stack([np.interp(grid, times, msd) for times, msd in runs])
            msd_mean = interpolated.mean(axis=0)
            fit = diffusion_coefficient(grid, msd_mean)
            d = fit[0]
            diffusion_by_config[name] = d
            plot_msd(name, grid, msd_mean, runs, fit)
            print(f"  D={d:.6f} m^2/s (ventana {fit[3][0]:.1f}-{fit[3][1]:.1f} s, plateau={fit[4]:.4f} m^2)")
        plot_correlation(diffusion_by_config)
        print("\nResumen:")
        for name in CONFIGS:
            print(f"  {name}: D={diffusion_by_config[name]:.6f} m^2/s, <t90>={MEAN_T90[name]} s")
    finally:
        CONFIG_PATH.write_text(original, encoding="utf-8")
        print("input/config.json restaurado a su contenido original")


if __name__ == "__main__":
    main()
