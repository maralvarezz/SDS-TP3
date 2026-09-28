import math
from datetime import datetime, timezone
from itertools import groupby

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from PIL import Image

from common import latest_run, one_file, rows

FPS = 20
SPEED = 1.0
MIN_FRAME_MS = round(1000 / FPS)
MAX_FRAME_MS = 3000


def frames(run, metadata):
    n = metadata["config"]["particles"]["count"]
    previous_time = None
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
        elif ids != initial_ids or time < previous_time:
            raise ValueError("IDs o tiempos inconsistentes en states")
        previous_time = time
        yield time, [(float(p["x"]), float(p["y"]), p["state"]) for p in particles]
    if initial_ids is None or previous_time != metadata["finalTime"]:
        raise ValueError("Falta el estado final")


def main():
    fps, speed = FPS, SPEED
    if type(fps) is not int or fps <= 0 or type(speed) not in (int, float) or not math.isfinite(speed) or speed <= 0:
        raise ValueError("FPS debe ser entero positivo y SPEED positivo y finito")
    run, metadata = latest_run()
    output = metadata["config"]["output"]
    if not output["writeStates"]:
        raise ValueError("Esta corrida no grabo estados. Generar otra con writeStates=true")
    table = metadata["config"]["simulation"]
    radius = metadata["config"]["particles"]["radius"]

    times = [time for time, _ in frames(run, metadata)]
    if len(times) < 2:
        raise ValueError("Se necesitan al menos 2 estados grabados para animar")

    selected = [0]
    last_shown_time = times[0]
    for i in range(1, len(times) - 1):
        if (times[i] - last_shown_time) * 1000 / speed >= MIN_FRAME_MS:
            selected.append(i)
            last_shown_time = times[i]
    if selected[-1] != len(times) - 1:
        selected.append(len(times) - 1)

    durations_ms = [
        int(max(MIN_FRAME_MS, min(MAX_FRAME_MS, 1000 * (times[selected[k + 1]] - times[selected[k]]) / speed)))
        for k in range(len(selected) - 1)
    ]
    durations_ms.append(MIN_FRAME_MS)
    selected_set = frozenset(selected)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.set(xlim=(0, table["length"]), ylim=(0, table["width"]), xlabel="x (m)", ylabel="y (m)")
    ax.set_aspect("equal")
    fig.set_dpi(90)
    for obstacle in metadata["config"]["obstacles"]:
        ax.add_patch(Circle((obstacle["x"], obstacle["y"]), obstacle["radius"], color="0.5"))
    low = (table["width"] - table["goalSize"]) / 2
    for x in (0, table["length"]):
        ax.plot([x, x], [low, low + table["goalSize"]], color="tab:green", linewidth=4, clip_on=False)
    title = ax.set_title("")
    fig.tight_layout()
    circles = []
    canvas = fig.canvas

    def render_frames():
        for idx, (time, particles) in enumerate(frames(run, metadata)):
            if idx not in selected_set:
                continue
            if not circles:
                for x, y, state in particles:
                    circle = Circle((x, y), radius, color="tab:blue")
                    ax.add_patch(circle)
                    circles.append(circle)
            used = 0
            for circle, (x, y, state) in zip(circles, particles):
                circle.center = x, y
                circle.set_color("tab:red" if state == "USED" else "tab:blue")
                used += state == "USED"
            title.set_text(f"t = {time:.2f} s | usadas: {used}/{len(circles)}")
            canvas.draw()
            width, height = canvas.get_width_height()
            yield Image.frombuffer("RGBA", (width, height), canvas.buffer_rgba(),
                                    "raw", "RGBA", 0, 1).convert("RGB")

    folder = run / "plots"
    folder.mkdir(exist_ok=True)
    path = folder / f"animation_{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}.gif"
    try:
        frame_images = render_frames()
        first = next(frame_images)
        first.save(str(path), save_all=True, append_images=frame_images,
                   duration=durations_ms, loop=0)
        print(path)
    finally:
        plt.close(fig)
    return path


if __name__ == "__main__":
    main()
