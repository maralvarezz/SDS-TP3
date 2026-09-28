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

CONFIG_COLORS = {
    "mesa_vacia": "tab:blue",
    "x=0.6": "tab:orange",
    "embudo_r=0.02": "tab:green",
    "R=0.339": "tab:red",
    "embudo_gap=0.45": "tab:purple",
    "competencia_R=0.3": "tab:brown",
}

DISPLAY_NAMES = {
    "mesa_vacia": "Mesa vacia",
    "R=0.339": "Obstaculo unico",
    "embudo_gap=0.45": "Embudo",
    "competencia_R=0.3": "Competencia",
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


def plot_curves(labels=None, name="comparison", title=None):
    curves = load_curves()
    if labels is not None:
        curves = {label: curves[label] for label in labels if label in curves}
    if not curves:
        raise ValueError("No hay curvas guardadas para graficar")
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for i, (label, curve) in enumerate(curves.items()):
        color = CONFIG_COLORS.get(label, colors[i % len(colors)])
        ax.step(curve["times"], curve["fractions"], where="post",
                label=DISPLAY_NAMES.get(label, label), color=color)
        if curve.get("t90") is not None:
            ax.axvline(curve["t90"], linestyle=":", color=color, alpha=0.5)
    ax.axhline(0.9, linestyle="--", color="0.5", linewidth=1, label="90 %")
    ax.set(xlabel="Tiempo simulado (s)", ylabel="Fu", ylim=(0, 1.03))
    if title:
        ax.set_title(title)
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
