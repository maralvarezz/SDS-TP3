"""Dibuja la mesa (sin particulas) para una configuracion dada, con el mismo
esquema que la figura del enunciado: rectangulo L x W, arcos punteados de
ancho d centrados en las paredes cortas (x=0 y x=L), cotas L, W y d,
etiquetas "arco" y obstaculos circulares grises con su radio R_k.

La configuracion se pasa como dict con el mismo esquema que
input/config.json (simulation.length/width/goalSize y obstacles), o como
ruta a un JSON con ese esquema:

    draw_table(config)          -> (fig, ax), para componer o guardar a mano
    draw_config(ruta_json)      -> guarda un PNG y devuelve su ruta

Si el JSON usa "obstaclesFile" (archivo "x y R" por linea, ver ConfigLoader),
load_config lo resuelve relativo al directorio del JSON, igual que Java.

Sin argumentos por linea de comando (los parametros se pasan por archivo de
configuracion): ejecutar el script dibuja CONFIG_PATH y guarda el PNG en
output/table_plots/.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[1]

# Opcion local del script (no afecta la simulacion): que configuracion dibujar.
CONFIG_PATH = ROOT / "input" / "config.json"

WALL_WIDTH = 2.6
OBSTACLE_COLOR = "0.6"
SMALL_OBSTACLE = 0.05  # radios menores: la etiqueta R_k se dibuja arriba del circulo


def load_config(path):
    path = Path(path)
    config = json.loads(path.read_text(encoding="utf-8"))
    obstacles_file = config.get("obstaclesFile")
    if obstacles_file:
        obstacles = []
        for line in (path.parent / obstacles_file).read_text(encoding="utf-8").splitlines():
            if line.strip():
                x, y, radius = (float(value) for value in line.split())
                obstacles.append({"x": x, "y": y, "radius": radius})
        config["obstacles"] = obstacles
    return config


def _dimension_arrow(ax, start, end):
    ax.annotate("", xy=end, xytext=start,
                arrowprops=dict(arrowstyle="<->", color="black", lw=1.1, shrinkA=0, shrinkB=0))


def _label_obstacle_radius(ax, index, obstacle, count):
    x, y, r = obstacle["x"], obstacle["y"], obstacle["radius"]
    ax.plot([x, x + r], [y, y], color="black", linestyle=":", linewidth=1.1, zorder=4)
    name = "R_k" if count == 1 else f"R_{index + 1}"
    if r < SMALL_OBSTACLE:
        # En obstaculos chicos la etiqueta no entra sobre el radio: va arriba del circulo.
        ax.text(x, y + r + 0.008, f"${name}$", ha="center", va="bottom", fontsize=9, zorder=5)
    else:
        ax.text(x + r / 2, y + 0.008, f"${name}$", ha="center", va="bottom", fontsize=9, zorder=5)


def draw_table(config, ax=None, show_radius=True, title=None):
    sim = config["simulation"]
    length, width, goal = sim["length"], sim["width"], sim["goalSize"]
    obstacles = config.get("obstacles", [])
    if ax is None:
        fig, ax = plt.subplots(figsize=(9.5, 5))
    else:
        fig = ax.figure

    low, high = (width - goal) / 2, (width + goal) / 2
    wall = dict(color="black", linewidth=WALL_WIDTH, solid_capstyle="projecting", zorder=3)
    ax.plot([0, length], [0, 0], **wall)
    ax.plot([0, length], [width, width], **wall)
    for x in (0, length):
        ax.plot([x, x], [0, low], **wall)
        ax.plot([x, x], [high, width], **wall)
        ax.plot([x, x], [low, high], color="black", linewidth=WALL_WIDTH,
                linestyle=(0, (1, 2.2)), zorder=3)

    for i, obstacle in enumerate(obstacles):
        ax.add_patch(Circle((obstacle["x"], obstacle["y"]), obstacle["radius"],
                            facecolor=OBSTACLE_COLOR, edgecolor="black", linewidth=1.2, zorder=2))
        if show_radius:
            _label_obstacle_radius(ax, i, obstacle, len(obstacles))

    # Cota del arco (d) a la izquierda, con sus guias hasta la pared.
    x_d = -0.06
    for y in (low, high):
        ax.plot([x_d - 0.01, -0.005], [y, y], color="0.55", linewidth=0.8, zorder=1)
    _dimension_arrow(ax, (x_d, low), (x_d, high))
    ax.text(x_d - 0.022, width / 2, "$d$", ha="right", va="center", fontsize=14)
    label = dict(fontsize=11, va="center", bbox=dict(facecolor="0.85", edgecolor="none", pad=2.5))
    ax.text(x_d - 0.075, width / 2, "arco", ha="right", **label)
    ax.text(length + 0.02, width / 2, "arco", ha="left", **label)

    # Cotas de ancho (W) a la derecha y de largo (L) abajo.
    x_w = length + 0.14
    _dimension_arrow(ax, (x_w, 0), (x_w, width))
    ax.text(x_w + 0.03, width / 2, "$W$", ha="left", va="center", fontsize=14)
    y_l = -0.09
    _dimension_arrow(ax, (0, y_l), (length, y_l))
    ax.text(length / 2, y_l - 0.035, "$L$", ha="center", va="top", fontsize=14)

    ax.set_xlim(-0.36, length + 0.25)
    ax.set_ylim(-0.19, width + 0.06)
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=13)
    return fig, ax


def draw_config(path, output=None):
    path = Path(path)
    fig, _ = draw_table(load_config(path))
    if output is None:
        folder = ROOT / "output" / "table_plots"
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / f"table_{path.stem}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}.png"
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)
    print(output)
    return Path(output)


if __name__ == "__main__":
    draw_config(CONFIG_PATH)
