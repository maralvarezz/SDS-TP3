"""Anima una corrida completa a partir de los estados grabados por evento.

Correccion de catedra (mail recalcando un error comun): "no esta permitido
ningun tipo de interpolacion, busqueda o uso de tiempos que no correspondan
a eventos. Ni para animar, ni para ningun otro fin." La version anterior de
este script violaba justo eso: muestreaba tiempos de reloj de reproduccion
(frame * speed / fps) e interpolaba linealmente la posicion de cada
particula entre el estado anterior y el siguiente para ese instante
inventado.

Esta version no hace eso. Cada frame del GIF es exactamente un estado que
Java escribio en states_*.csv (un tiempo de evento real, con la posicion tal
cual quedo registrada) -- nunca se inventa ni se busca una posicion en un
tiempo intermedio. Entre dos frames consecutivos las particulas se ven
"quietas" y saltan a la posicion del proximo evento en cuanto este ocurre,
en vez de deslizarse suavemente (eso ultimo seria interpolar).

La UNICA libertad que se toma este script es sobre cuanto tiempo real dura
cada frame en el GIF (no sobre que posicion mostrar): la duracion de cada
frame es proporcional al Delta t simulado real hasta el proximo evento
(escalado por SPEED), acotada entre MIN_FRAME_MS y MAX_FRAME_MS solo por
motivos de reproduccion (un frame de 0 ms no se ve, y un tramo sin eventos
de varios segundos no deberia congelar la animacion). Esa duracion es una
decision de reproduccion del GIF, no una posicion calculada: nunca se
modifica ni se interpola el dato en si.

No requiere everyEvents=1 ni writeCollisions=true (a diferencia de la
version anterior, que reconstruia cada colision una por una para poder
interpolar "suave"): al no interpolar, ya no hace falta el detalle
evento-a-evento -- alcanza con cualquier corrida que tenga writeStates=true.
Un everyEvents mas alto simplemente anima con eventos reales mas espaciados
entre si (sigue siendo un tiempo real, solo que se salta eventos reales en
vez de mostrar todos), lo cual mantiene el tamano del GIF manejable en
configuraciones con muchas colisiones (ver diffusion_animations.py).
"""
import math
from datetime import datetime, timezone
from itertools import groupby

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from PIL import Image

from common import latest_run, one_file, rows

# Opciones de reproduccion locales; no afectan la simulacion ni su configuracion.
FPS = 20                 # solo se usa para el piso de duracion (1000/FPS) y el
                          # hold del ultimo frame -- no se muestrea a esta tasa
SPEED = 2.0               # segundos simulados por segundo real de video
MIN_FRAME_MS = round(1000 / FPS)  # piso de duracion por frame (legibilidad)
MAX_FRAME_MS = 3000        # techo de duracion por frame (que un tramo sin
                            # eventos no congele la animacion varios segundos)


def frames(run, metadata):
    """Itera los estados grabados en states_*.csv, en orden, uno por cada
    (time, event) real -- nunca un tiempo inventado ni buscado entre
    eventos."""
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

    # Primera pasada (liviana, solo tiempos): duracion de cada frame en el
    # GIF, proporcional al Delta t real hasta el proximo evento.
    times = [time for time, _ in frames(run, metadata)]
    if len(times) < 2:
        raise ValueError("Se necesitan al menos 2 estados grabados para animar")
    durations_ms = [
        int(max(MIN_FRAME_MS, min(MAX_FRAME_MS, 1000 * (times[i + 1] - times[i]) / speed)))
        for i in range(len(times) - 1)
    ]
    durations_ms.append(MIN_FRAME_MS)  # el ultimo frame no tiene "siguiente" del
    # cual derivar su Delta t: se sostiene un instante fijo y corto.

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.set(xlim=(0, table["length"]), ylim=(0, table["width"]), xlabel="x [m]", ylabel="y [m]")
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
        # Segunda pasada (re-lee states_*.csv): renderiza y entrega un frame
        # PIL por vez -- nunca se guardan todos los frames renderizados en
        # memoria a la vez, algo importante con corridas de cientos de miles
        # de eventos.
        for time, particles in frames(run, metadata):
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
    return path  # util para orquestar animaciones desde otro script (ver
    # diffusion_animations.py), sin cambiar el comportamiento por linea de
    # comandos existente


if __name__ == "__main__":
    main()
