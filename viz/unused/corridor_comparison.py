"""Punto 1.2: configuracion "pasillo". Dos filas de circulos iguales (radio rho)
pegados a las paredes largas, una arriba y otra abajo, a lo largo de toda la
mesa, que dejan un unico pasillo libre en el medio que une los dos arcos.

Geometria: cada fila tiene n circulos con centros en y = rho*MARGIN (abajo) e
y = W - rho*MARGIN (arriba), repartidos parejo entre x = rho*MARGIN y
x = L - rho*MARGIN, con separacion >= 2*rho*MARGIN (casi tangentes, sin
solaparse). El pasillo libre mide W - 4*rho*MARGIN. Para no tapar los arcos
(d=0.20 m centrado en W/2) el borde interno de las filas no debe pasar de
y = W/2 - d/2, o sea rho <= (W - d) / 4 = 0.12 m.

Restricciones verificadas para cada rho antes de correr: (i) obstaculos
dentro del dominio y sin solaparse, (ii) rho >= r_particula (ver
obstacle_layouts.validate_layout), y que se puedan generar las N particulas.

N=100, maxTime=100s. La corrida, reintentos y estadisticas se reutilizan de
goal_bumpers_comparison.py (mismos parametros N y tmax que el resto del 1.2).

Java no conoce este experimento ni recibe argumentos por linea de comando:
cada corrida se dispara reescribiendo la unica fuente de verdad,
input/config.json, y ejecutando el jar sin argumentos. El config original se
restaura al final.
"""
import json
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import fu_curves
import goal_bumpers_comparison as runner
from obstacle_layouts import validate_layout

MARGIN = 1.001  # evita tangencia exacta (con paredes y entre circulos) por redondeo
RADII = [0.04, 0.06, 0.08, 0.10, 0.12]
REALIZATIONS = 10
BASE_SEED = 20271000
COLOR = "tab:pink"  # ver fu_curves.CONFIG_COLORS


def layout(rho, length, width):
    edge = rho * MARGIN
    n = int((length - 2 * edge) // (2 * edge)) + 1
    step = (length - 2 * edge) / (n - 1)
    xs = [edge + i * step for i in range(n)]
    return [{"x": x, "y": y, "radius": rho} for y in (edge, width - edge) for x in xs]


def realize():
    base = json.loads(runner.CONFIG_PATH.read_text(encoding="utf-8"))
    length = base["simulation"]["length"]
    width = base["simulation"]["width"]
    particle_radius = base["particles"]["radius"]

    results = {"empty": []}
    for i in range(REALIZATIONS):
        seed = BASE_SEED + i
        print(f"mesa vacia realizacion {i + 1}/{REALIZATIONS} seed={seed}")
        metadata, directory = runner.run_with_retries(base, [], seed)
        results["empty"].append(metadata)
        print(f"  t90={metadata['t90']}")
        if i == 0:
            fu_curves.save_curve("mesa_vacia", directory, metadata)

    for rho in RADII:
        obstacles = layout(rho, length, width)
        validate_layout(obstacles, length, width, particle_radius)
        print(f"rho={rho}: {len(obstacles)} obstaculos, pasillo libre={width - 4 * rho * MARGIN:.3f} m")
        runs = []
        for i in range(REALIZATIONS):
            seed = BASE_SEED + int(round(rho * 10000)) + i
            print(f"rho={rho} realizacion {i + 1}/{REALIZATIONS} seed={seed}")
            metadata, directory = runner.run_with_retries(base, obstacles, seed)
            runs.append(metadata)
            print(f"  t90={metadata['t90']}")
            if i == 0:
                fu_curves.save_curve(f"pasillo_r={rho}", directory, metadata)
        results[rho] = runs
    return results


def plot(results):
    empty_mean, empty_std, empty_n = runner.t90_stats(results["empty"], "mesa vacia")
    rs, means, stds, counts = [], [], [], []
    for rho in RADII:
        m, s, n = runner.t90_stats(results[rho], f"rho={rho}")
        if m is None:
            continue
        rs.append(rho)
        means.append(m)
        stds.append(s)
        counts.append(n)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.errorbar(rs, means, yerr=stds, fmt="o-", capsize=4, color=COLOR,
                label="Pasillo: 2 filas de circulos en las paredes largas")
    if empty_mean is not None:
        ax.axhline(empty_mean, color="tab:blue", linestyle="--", label=f"Mesa vacia (<t90>={empty_mean:.2f} s)")
        ax.axhspan(empty_mean - empty_std, empty_mean + empty_std, color="tab:blue", alpha=0.15)
    ax.set(xlabel="Radio de los circulos rho [m]", ylabel="<t90> [s]",
           title=f"Punto 1.2 - Pasillo central (N={runner.N})")
    ax.grid(alpha=0.25)
    ax.legend()
    folder = runner.OUTPUT / "experiment_1_2_plots"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = folder / f"corridor_comparison_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)
    for rho, m, s, n in zip(rs, means, stds, counts):
        print(f"rho={rho}: <t90>={m:.3f} s, std={s:.3f} s, n={n}")
    if empty_mean is not None:
        print(f"mesa vacia: <t90>={empty_mean:.3f} s, std={empty_std:.3f} s, n={empty_n}")
    if rs:
        best = min(range(len(rs)), key=lambda i: means[i])
        print(f"Mejor radio explorado: rho={rs[best]} con <t90>={means[best]:.3f} s")
    return path


def main():
    if not runner.JAR.exists():
        raise FileNotFoundError(f"No se encontro el jar compilado: {runner.JAR}. Ejecutar 'mvn -q clean package' primero")
    original = runner.CONFIG_PATH.read_text(encoding="utf-8")
    try:
        results = realize()
        plot(results)
    finally:
        runner.CONFIG_PATH.write_text(original, encoding="utf-8")
        print("input/config.json restaurado a su contenido original")


if __name__ == "__main__":
    main()
