"""Grafico de fraccion usada y t90 de una corrida Java completada."""
from datetime import datetime, timezone

from common import latest_run, one_file, rows
from observables import t90_from_goals

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def save(fig, folder, name):
    fig.tight_layout()
    path = folder / f"{name}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)


def goals_plot(run, metadata, folder):
    data = list(rows(one_file(run, "goals_*.csv")))
    n = metadata["config"]["particles"]["count"]
    final_time = metadata["finalTime"]
    times = [0] + [float(row["time"]) for row in data] + [final_time]
    fractions = [0] + [int(row["totalGoals"]) / n for row in data] + [metadata["totalGoals"] / n]
    if len(data) != metadata["totalGoals"]:
        raise ValueError("El archivo de goles no coincide con los metadatos")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.step(times, fractions, where="post", label="Fracción usada", color="tab:blue")
    ax.axhline(0.9, linestyle="--", color="0.5", label="90 %")
    t90 = t90_from_goals(run)
    if t90 is not None:
        ax.axvline(t90, linestyle=":", color="tab:red", label=f"t90 = {t90:.3f} s")
    else:
        ax.text(0.98, 0.1, "No se alcanzó t90", ha="right", transform=ax.transAxes)
    ax.set(xlabel="Tiempo simulado [s]", ylabel="Fu = goles / N",
           ylim=(0, 1.03), xlim=(0, final_time), title="Punto 1.2 · Evolución hacia t90")
    ax.grid(alpha=0.25)
    ax.legend()
    save(fig, folder, "fraccion_usada")


def main():
    run, metadata = latest_run()
    folder = run / "plots"
    folder.mkdir(exist_ok=True)
    print(f"Corrida: {run}")
    if metadata["config"]["output"]["writeGoals"]:
        goals_plot(run, metadata, folder)
    else:
        print("Sin registro de goles: no se genera la curva Fu(t)")



if __name__ == "__main__":
    main()
