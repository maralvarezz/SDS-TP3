"""Dibuja la mesa de cada configuracion estudiada en el punto 1.2 (las mismas
etiquetas de diffusion.BUILDERS y del grafico conjunto de Fu(t)) y la
configuracion de competencia vigente en input/config.json.

Los obstaculos se toman de diffusion.BUILDERS, sin duplicar definiciones. Sin
argumentos por linea de comando: los PNG se guardan en output/table_plots/.
"""
import re
from datetime import datetime, timezone

import matplotlib.pyplot as plt

import diffusion
import draw_table

MAX_LABELED_OBSTACLES = 3  # con mas obstaculos las etiquetas R_k se pisan


def main():
    base = draw_table.load_config(draw_table.CONFIG_PATH)
    sim = base["simulation"]
    length, width, goal = sim["length"], sim["width"], sim["goalSize"]

    tables = {label: builder(length, width, goal) for label, builder in diffusion.BUILDERS.items()}
    tables["competencia (input/config.json)"] = base["obstacles"]

    folder = draw_table.ROOT / "output" / "table_plots"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = f"{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
    for label, obstacles in tables.items():
        config = {"simulation": sim, "obstacles": obstacles}
        fig, _ = draw_table.draw_table(config, show_radius=len(obstacles) <= MAX_LABELED_OBSTACLES,
                                        title=label)
        fig.tight_layout()
        path = folder / f"table_{re.sub(r'[^A-Za-z0-9]+', '_', label).strip('_')}_{stamp}.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        print(path)


if __name__ == "__main__":
    main()
