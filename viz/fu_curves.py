"""Almacena y grafica curvas Fu(t) (fraccion usada vs tiempo) de corridas del
punto 1.2, para poder compararlas mas adelante en un unico grafico con una
curva por configuracion, en distintos colores.

No es una fuente de verdad adicional: cada curva guardada se reconstruye
directamente del goals_*.csv y metadata_*.json que ya escribe Java para esa
corrida (misma logica que point_1_2.py). Este modulo solo cachea esa
reconstruccion, indexada por una etiqueta de configuracion, en un JSON
compartido para poder graficar varias configuraciones juntas sin tener que
volver a correr todo.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import one_file, rows

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
CURVES_PATH = OUTPUT / "experiment_1_2_plots" / "fu_curves.json"

# Color fijo por configuracion, compartido por el grafico conjunto de Fu(t) y
# por los graficos individuales (1.2 y 1.3), para que cada configuracion se
# vea igual en todos lados. Etiquetas nuevas usan el ciclo por defecto.
CONFIG_COLORS = {
    "mesa_vacia": "tab:blue",
    "x=0.6": "tab:orange",
    "embudo_r=0.02": "tab:green",
    "R=0.339": "tab:red",
    "embudo_gap=0.45": "tab:purple",
    "competencia_R=0.3": "tab:brown",
}


def _fu_curve(run, metadata):
    data = list(rows(one_file(run, "goals_*.csv")))
    n = metadata["config"]["particles"]["count"]
    final_time = metadata["finalTime"]
    if len(data) != metadata["totalGoals"]:
        raise ValueError(f"El archivo de goles de {run} no coincide con los metadatos")
    times = [0.0] + [float(row["time"]) for row in data] + [final_time]
    fractions = [0.0] + [int(row["totalGoals"]) / n for row in data] + [metadata["totalGoals"] / n]
    return times, fractions


def load_curves():
    if not CURVES_PATH.is_file():
        return {}
    return json.loads(CURVES_PATH.read_text(encoding="utf-8"))


def save_curve(label, run, metadata):
    """Reconstruye la curva Fu(t) de esta corrida (requiere writeGoals=true)
    y la guarda bajo `label` en el almacen compartido de curvas del punto 1.2."""
    times, fractions = _fu_curve(run, metadata)
    curves = load_curves()
    curves[label] = {
        "times": times,
        "fractions": fractions,
        "t90": metadata.get("t90"),
        "n": metadata["config"]["particles"]["count"],
        "obstacles": metadata["config"]["obstacles"],
        "run": str(run),
    }
    CURVES_PATH.parent.mkdir(parents=True, exist_ok=True)
    CURVES_PATH.write_text(json.dumps(curves, indent=2), encoding="utf-8")
    print(f"  curva Fu(t) guardada: '{label}' ({CURVES_PATH})")


def plot_curves(labels=None, name="comparison"):
    curves = load_curves()
    if labels is not None:
        curves = {label: curves[label] for label in labels if label in curves}
    if not curves:
        raise ValueError("No hay curvas guardadas para graficar")
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for i, (label, curve) in enumerate(curves.items()):
        color = CONFIG_COLORS.get(label, colors[i % len(colors)])
        ax.step(curve["times"], curve["fractions"], where="post", label=label, color=color)
        if curve.get("t90") is not None:
            ax.axvline(curve["t90"], linestyle=":", color=color, alpha=0.5)
    ax.axhline(0.9, linestyle="--", color="0.5", linewidth=1, label="90 %")
    ax.set(xlabel="Tiempo simulado [s]", ylabel="Fu = goles / N", ylim=(0, 1.03),
           title="Punto 1.2 - Fu(t) por configuracion")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    folder = OUTPUT / "experiment_1_2_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"fu_curves_{name}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    return path


if __name__ == "__main__":
    plot_curves()
