"""Punto 1.3: desplazamiento cuadratico medio (DCM) y coeficiente de difusion (D).

Enunciado (verificado via Projects.project_search sobre el PDF): "Calcular el
desplazamiento cuadratico medio (DCM) promediando sobre todas las particulas
moviles del sistema (frescas y usadas) PARA UNA REALIZACION. Luego ajustar
linealmente siguiendo las indicaciones del metodo mostrado en la clase
Teorica 0 para obtener el coeficiente de difusion (D). Reportar D para la
mesa vacia y para las otras configuraciones estudiadas, y verificar si
existe o no alguna correlacion entre D y t90."

Correccion de la catedra (devolucion sobre una entrega previa): el punto 1.3
debe presentarse con UNA sola realizacion por configuracion (nada de
promediar el DCM sobre varias corridas, a diferencia del punto 1.2) y con
TODAS las configuraciones en un unico grafico de DCM(t) en vez de un PNG
separado por configuracion. Este script fue corregido para reflejar eso: ya
no promedia entre realizaciones (antes se corrian REALIZATIONS=10 seeds por
config y se promediaba el DCM sobre una grilla temporal comun), y el DCM se
promedia unicamente sobre las N particulas de esa unica corrida, como pide
el enunciado. t90 tambien pasa a ser el valor de esa misma corrida (sin
promedio ni barra de error entre realizaciones, que solo tiene sentido en
1.2/1.4 donde el enunciado si pide "al menos 5 realizaciones").

Configuraciones estudiadas: mesa vacia + UN representante final por cada una
de las 3 familias del punto 1.2 (no uno por cada eje explorado dentro de una
familia): R=0.339 (familia A: obstaculo unico, posicion x=L/2 y radio ya
optimizados juntos), embudo_gap=0.45 (familia B: circulo grande + 2 chicos,
radio 0.02 y separacion 0.45 ya optimizados juntos) y competencia_R=0.3
(familia C: relleno + semicirculos libres frente a los arcos, radio libre ya
optimizado). Mismas etiquetas y colores que el grafico conjunto de Fu(t) (ver
fu_curves.CONFIG_COLORS). Sus obstaculos se toman de los propios scripts/
modulos de 1.2 para no duplicar las definiciones.

Metodologia del ajuste, segun docs/Teorica_0.pdf (slide 38, "Difusion: Random
Walk"):

- El sistema es 2D, por lo que la convencion de la catedra es <z^2> = 4 D t.
- Ajuste sobre el tramo de crecimiento SIN ordenada al origen: el modelo de
  Teorica_0 es <z^2> = 4 D t, sin termino independiente (en t=0 el
  desplazamiento es 0 por construccion), asi que se ajusta y = m*t (un solo
  parametro) y D = m / 4.

La mesa (L=1.20 x W=0.68 m) es chica: el DCM satura por confinamiento en
pocos segundos, muy antes de cualquier fraccion fija del tiempo total. Teorica_0
no especifica una ventana de ajuste, asi que se la define en funcion del valor
del DCM: entre FIT_LOW y FIT_HIGH fracciones del valor de saturacion (media del
DCM sobre el ultimo PLATEAU_TAIL_FRACTION del tiempo simulado), evitando la zona
ya saturada.

FIT_LOW_FRACTION=0 (no recorta el arranque) y FIT_HIGH_FRACTION=0.50 se
eligieron comparando el R^2 del ajuste sobre los datos reales de una corrida
para varias ventanas candidatas (0.15-0.65, 0.20-0.50, 0.15-0.50, 0-0.50).
Contra la hipotesis inicial de que habia que recortar el arranque balistico
(<z^2> ~ t^2 para t chico) para no sesgar la pendiente, sacar ese corte dio
SIEMPRE mejor R^2 en las 4 configuraciones de 1.3 (ej. competencia_R=0.3:
R^2=0.24 con 0.15-0.65 vs R^2=0.98 con 0-0.50): como el ajuste ya se fuerza
por el origen (ver diffusion_coefficient) y el DCM real tambien arranca
exactamente en (0,0) por construccion, incluir esos primeros puntos ancla
mejor la recta en vez de sesgarla.

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
    """Formatea un numero a 2 cifras significativas (D se reporta asi, no con
    una cantidad fija de decimales -- con valores que van de ~0.003 a ~0.019
    m^2/s, .6f mostraba 4-5 cifras significativas de mas)."""
    return f"{x:.2g}"


N = 100
MAX_TIME = 100.0
EVERY_EVENTS = 25
BASE_SEED = 20270000

FIT_LOW_FRACTION = 0.0
FIT_HIGH_FRACTION = 0.50
PLATEAU_TAIL_FRACTION = 0.20

BEST_RADIUS = 0.339
BEST_FREE_RADIUS = 0.30

# Un unico representante FINAL por familia (mesa vacia + 3), no uno por eje
# explorado: x=0.6 (posicion, con un radio de referencia todavia sin
# optimizar) y embudo_r=0.02 (circulos chicos tangentes, gap todavia sin
# optimizar) eran resultados INTERMEDIOS de sus respectivos barridos -- ya
# quedaron superados por R=0.339 (misma posicion x=0.6=L/2, radio ya
# optimizado) y embudo_gap=0.45 (mismo radio chico 0.02, gap ya optimizado).
# Family C (competencia_R=0.3) directamente faltaba.
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
    cfg.pop("obstaclesFile", None)  # esta corrida fija sus propios obstaculos inline
    cfg.pop("initialPositionsFile", None)  # esta corrida usa colocacion aleatoria por defecto
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
    """DCM(t) de UNA corrida: promedio sobre las N particulas (frescas y
    usadas) de esa unica realizacion, como pide el enunciado -- no hay
    promedio entre realizaciones aca."""
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
    """Ajusta <z^2> = 4 D t (Teorica_0, slide 38) sin ordenada al origen: el
    modelo no tiene termino independiente, ya que en t=0 el desplazamiento es
    0 por construccion. Minimos cuadrados con y = m*t (un unico parametro):
    m = sum(t*z2) / sum(t^2)."""
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


def run_config(base, label, obstacles, config_index):
    """Una unica realizacion por configuracion (seed determinista por
    indice), tal como pide el enunciado para el punto 1.3 y como lo corrigio
    la catedra."""
    seed = BASE_SEED + config_index
    directory, metadata = run_once(base, obstacles, seed)
    times, msd = msd_curve(directory)
    if times[-1] < MAX_TIME:
        raise ValueError(f"{label} seed={seed}: la corrida no llego a maxTime")
    if metadata["t90"] is None:
        raise ValueError(f"{label} seed={seed}: no alcanzo t90 antes de maxTime")
    print(f"  seed={seed} t90={metadata['t90']:.3f} frames={len(times)}")
    d, slope, intercept, window = diffusion_coefficient(times, msd)
    return {"times": times, "msd": msd, "d": d, "slope": slope,
            "intercept": intercept, "window": window, "t90": metadata["t90"]}


def slug(label):
    return re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_")


def plot_msd_all(results):
    """Un unico grafico de DCM(t) con todas las configuraciones (mesa vacia
    incluida), cada una con su recta de ajuste punteada del mismo color --
    reemplaza los PNG individuales por configuracion que se generaban antes,
    por pedido explicito de la correccion de la catedra."""
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    for label in CONFIGS:
        r = results[label]
        color = fu_curves.CONFIG_COLORS[label]
        ax.plot(r["times"], r["msd"], color=color, linewidth=1.8,
                 label=f"{label} (D={fmt2sf(r['d'])} m^2/s)")
        # La recta se dibuja desde el origen (no desde "lo"): el ajuste ya
        # fuerza el modelo <z^2>=4Dt por el origen (Teorica_0), asi que
        # arrancar el trazo en "lo" lo dejaba flotando en el medio de la
        # curva sin tocar (0,0). Se corta justo en "hi" y no mas alla: pasado
        # ese punto la curva real entra en la zona de saturacion por
        # confinamiento (deja de crecer ~linealmente), asi que el modelo ya
        # no aplica ahi por construccion -- extrapolar la recta mas alla solo
        # hace parecer que el ajuste "falla" cuando en realidad esta fuera de
        # su rango valido a proposito.
        _, hi = r["window"]
        fit_ts = np.array([0.0, hi])
        ax.plot(fit_ts, r["slope"] * fit_ts + r["intercept"], color=color,
                 linestyle="--", linewidth=2.2, alpha=0.75, zorder=1)
    # Eje x fijo en 10s: bastante mas ancho que cualquier ventana de ajuste
    # (todas quedan por debajo de ~2.5s), asi las rectas punteadas se ven
    # claramente concentradas en la primera parte de la curva en vez de
    # ocupar casi todo el ancho del grafico.
    XLIM_MAX = 10.0
    ax.set_xlim(0, XLIM_MAX)
    # Recorta tambien el eje y al maximo DCM que realmente aparece dentro del
    # rango de tiempo mostrado (antes quedaba fijado por el valor de
    # saturacion de mesa vacia a t=100s, muy por encima de lo que se ve en
    # este recorte de x, dejando el grafico vacio arriba).
    ymax = max(r["msd"][r["times"] <= XLIM_MAX].max() for r in results.values())
    ax.set_ylim(0, ymax * 1.08)  # el 0 explicito ancla el origen (0,0) --
    # por donde pasan todas las rectas de ajuste -- a la esquina inferior
    # izquierda, en vez del margen automatico de matplotlib
    ax.set(xlabel="Tiempo simulado [s]", ylabel="DCM [m^2]",
           title="Punto 1.3 - DCM(t) por configuracion (una realizacion)")
    ax.yaxis.set_major_locator(MaxNLocator(nbins=12))  # mas marcas en el eje y
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
        ax.plot(r["t90"], r["d"], "o", color=color, markersize=8, label=label)
    ax.set(xlabel="t90 [s]", ylabel="D [m^2/s]",
           title="Punto 1.3 - Correlacion D vs t90 (una realizacion)")
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
            print(f"  D={fmt2sf(r['d'])} m^2/s (ventana {r['window'][0]:.1f}-{r['window'][1]:.1f} s), "
                  f"t90={r['t90']:.3f} s")
        plot_msd_all(results)
        plot_correlation(results)
        ds = [results[label]["d"] for label in CONFIGS]
        ts = [results[label]["t90"] for label in CONFIGS]
        print("\nResumen:")
        for label in CONFIGS:
            r = results[label]
            print(f"  {label}: D={fmt2sf(r['d'])} m^2/s, t90={r['t90']:.3f} s")
        print(f"Correlacion de Pearson D vs t90 ({len(CONFIGS)} configuraciones): "
              f"r={np.corrcoef(ds, ts)[0, 1]:.3f}")
    finally:
        CONFIG_PATH.write_text(original, encoding="utf-8")
        print("input/config.json restaurado a su contenido original")


if __name__ == "__main__":
    main()
