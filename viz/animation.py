"""Anima una corrida completa a partir de estados por evento y colisiones registradas."""
import math
from datetime import datetime, timezone
from itertools import groupby

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import PillowWriter
from matplotlib.patches import Circle

from common import latest_run, one_file, rows

# Opciones de reproduccion locales; no afectan la simulacion ni su configuracion.
FPS = 20
SPEED = 2.0


def frames(run, metadata):
    n = metadata["config"]["particles"]["count"]
    collisions = iter(rows(one_file(run, "collisions_*.csv")))
    previous_event = 0
    previous_time = 0.0
    initial_ids = None
    grouped = groupby(rows(one_file(run, "states_*.csv")),
                      key=lambda row: (float(row["time"]), int(row["event"])))
    for (time, event), group in grouped:
        particles = sorted(group, key=lambda row: int(row["id"]))
        ids = [int(row["id"]) for row in particles]
        if len(ids) != n or len(set(ids)) != n:
            raise ValueError(f"Estado incompleto en evento {event}")
        if initial_ids is None:
            if time != 0 or event != 0:
                raise ValueError("Falta el estado inicial")
            initial_ids = ids
        else:
            if ids != initial_ids or time < previous_time:
                raise ValueError("IDs o tiempos inconsistentes en states")
            if event == previous_event + 1:
                collision = next(collisions, None)
                if collision is None or int(collision["event"]) != event or float(collision["time"]) != time:
                    raise ValueError(f"Falta la colision correspondiente al evento {event}")
            elif not (event == previous_event and time == metadata["finalTime"]):
                raise ValueError("Faltan estados intermedios: usar everyEvents=1")
        previous_time, previous_event = time, event
        yield time, [(float(p["x"]), float(p["y"]), p["state"]) for p in particles]
    if initial_ids is None or previous_event != metadata["totalEvents"] or previous_time != metadata["finalTime"]:
        raise ValueError("Falta el estado final completo")
    if next(collisions, None) is not None:
        raise ValueError("Hay colisiones sin estado asociado")


def main():
    fps, speed = FPS, SPEED
    if type(fps) is not int or fps <= 0 or type(speed) not in (int, float) or not math.isfinite(speed) or speed <= 0:
        raise ValueError("FPS debe ser entero positivo y SPEED positivo y finito")
    run, metadata = latest_run()
    output = metadata["config"]["output"]
    if not output["writeStates"] or not output["writeCollisions"] or output["everyEvents"] != 1:
        raise ValueError("Esta corrida no permite reconstruir todos los choques. Generar otra con "
                     "writeStates=true, writeCollisions=true y everyEvents=1")
    table = metadata["config"]["simulation"]
    radius = metadata["config"]["particles"]["radius"]
    stream = frames(run, metadata)
    current = next(stream)
    following = next(stream, None)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.set(xlim=(0, table["length"]), ylim=(0, table["width"]), xlabel="x [m]", ylabel="y [m]")
    ax.set_aspect("equal")
    for obstacle in metadata["config"]["obstacles"]:
        ax.add_patch(Circle((obstacle["x"], obstacle["y"]), obstacle["radius"], color="0.5"))
    low = (table["width"] - table["goalSize"]) / 2
    for x in (0, table["length"]):
        ax.plot([x, x], [low, low + table["goalSize"]], color="tab:green", linewidth=4, clip_on=False)
    circles = []
    for x, y, state in current[1]:
        circle = Circle((x, y), radius, color="tab:blue")
        ax.add_patch(circle)
        circles.append(circle)
    title = ax.set_title("")
    fig.tight_layout()
    folder = run / "plots"
    folder.mkdir(exist_ok=True)
    path = folder / f"animation_{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}.gif"
    end = metadata["finalTime"]
    count = math.ceil(end * fps / speed) + 1
    writer = PillowWriter(fps=fps)
    try:
        with writer.saving(fig, str(path), dpi=90):
            for frame in range(count):
                time = min(frame * speed / fps, end)
                # Consumir todos los eventos hasta este instante, incluidos los simultaneos.
                while following is not None and following[0] <= time:
                    current = following
                    following = next(stream, None)
                fraction = 0 if following is None else (time - current[0]) / (following[0] - current[0])
                used = 0
                for i, (x, y, state) in enumerate(current[1]):
                    if following is not None:
                        nx, ny, _ = following[1][i]
                        x, y = x + fraction * (nx - x), y + fraction * (ny - y)
                    circles[i].center = x, y
                    circles[i].set_color("tab:red" if state == "USED" else "tab:blue")
                    used += state == "USED"
                title.set_text(f"t = {time:.2f} s | usadas: {used}/{len(circles)}")
                writer.grab_frame()
        print(path)
    finally:
        plt.close(fig)
        stream.close()


if __name__ == "__main__":
    main()
