"""Genera la disposicion de obstaculos de la familia "competencia" del punto
1.2: dos semicirculos libres frente a cada arco (x=0 y x=L, centrados en
y=W/2) y el resto de la mesa cubierto por un relleno de obstaculos chicos
empaquetados hexagonalmente, tangentes entre si.

La idea (propuesta por el usuario, ver conversacion) es indirecta: Java no
sabe que existe una "zona libre" ni un "relleno"; el motor solo ve una lista
de obstaculos circulares (igual que cualquier otra configuracion). El efecto
de bloqueo surge exclusivamente de InitialStateGenerator.java, que genera
cada particula por rechazo (RSA) probando candidatos uniformes en TODA la
mesa y descartando cualquiera que se solape con un obstaculo -- si el
relleno tapa casi toda el area salvo los dos semicirculos, en la practica
las N particulas terminan ubicadas ahi.

El relleno se genera reusando el mismo empaquetado hexagonal que
hexagonal_packing.py usa para posiciones de particulas (misma geometria de
grilla, aqui aplicada a centros de obstaculos): tangentes entre si con un
margen de seguridad, por lo que los huecos entre 3 obstaculos vecinos
(inradio ~= 0.155 * filler_radius) son mucho mas chicos que el radio de una
particula y no dejan pasar ninguna.

Restricciones del punto 1.2 (verificadas con validate_layout):
i.  K obstaculos integramente dentro del dominio y sin solaparse entre si
    (el propio armado en grilla tangente ya lo garantiza).
ii. Rk >= r_particula (filler_radius=0.02 > 0.0175) y que permita generar
    las N particulas -- verificado empiricamente por fuera de Java (ver
    scratch de factibilidad RSA) para el rango de free_radius usado por
    goal_semicircle_comparison.py: OK desde free_radius=0.24 m en adelante.
"""
import math

from hexagonal_packing import _lattice

FILLER_RADIUS = 0.02  # > r_particula (0.0175), mismo valor que SMALL_RADIUS en la familia B
MARGIN_FACTOR = 1.001  # separa apenas mas que la tangencia exacta, evita solapar por redondeo


def goal_semicircle_layout(free_radius, length, width,
                            filler_radius=FILLER_RADIUS, margin_factor=MARGIN_FACTOR):
    """Obstaculos de relleno para dejar libres dos semicirculos de radio
    `free_radius`, centrados en cada arco ((0, width/2) y (length, width/2)).
    Devuelve una lista de dicts {"x", "y", "radius"} lista para
    cfg["obstacles"]."""
    spacing = 2 * filler_radius * margin_factor
    candidates = _lattice(length, width, filler_radius, spacing)
    goal_centers = [(0.0, width / 2), (length, width / 2)]
    obstacles = []
    for x, y in candidates:
        if all(math.hypot(x - gx, y - gy) >= free_radius + filler_radius for gx, gy in goal_centers):
            obstacles.append({"x": x, "y": y, "radius": filler_radius})
    return obstacles


# --- Variantes propuestas para mejorar el mejor semicirculo (free_radius=0.30,
# <t90>=13.16 s, ver conversacion): en vez de un semicirculo simetrico, donde
# buena parte del borde recto de cada pared corta (fuera de los d=0.20 m del
# arco) es "pared muerta" que no suma gol, se prueban 3 variantes que apuntan
# a mejorar el "apunte" hacia el arco sin volver a los problemas de
# apiñamiento que empeoraban el t90 a free_radius chico:
#
# 1. "funnel": la zona libre es un trapezoide que calza exactamente con el
#    ancho del arco (d) en la pared y se abre linealmente hasta
#    far_half_width a una profundidad `depth` dentro de la mesa. Toda la
#    pared recta que toca la cavidad es el arco (no hay pared muerta). Con
#    depth=0.45 y far_half_width=0.30 el area libre total (0.36 m^2 para los
#    2 arcos) termina siendo mayor que la del semicirculo R=0.30 (0.2827
#    m^2), asi que no deberia apianar mas que el mejor caso ya medido.
# 2. "semicircle_guides": se mantiene el semicirculo R=0.30 (el mejor medido)
#    y se agregan 2 obstaculos chicos "guia" justo por fuera de cada borde
#    del arco (misma idea que el "paragolpes" ya descartado de la familia B,
#    pero ahora adentro de la cavidad libre de la familia C) para desviar
#    particulas hacia adentro del arco en vez de dejarlas rebotar al azar.
# 3. "funnel_guides": combina 1 y 2.
FUNNEL_DEPTH = 0.45
FUNNEL_FAR_HALF_WIDTH = 0.30
GUIDE_RADIUS = 0.025
X_GUIDE = 0.10  # distancia de cada guia a la pared corta de su arco


def _funnel_free(x, y, goal_x, width, depth, far_half_width, goal_size, mirrored):
    xi = (goal_x - x) if mirrored else (x - goal_x)
    if not (0 <= xi <= depth):
        return False
    half_width = goal_size / 2 + (far_half_width - goal_size / 2) * (xi / depth)
    return abs(y - width / 2) <= half_width


def guide_obstacles(length, width, goal_size,
                     guide_radius=GUIDE_RADIUS, x_guide=X_GUIDE):
    """2 obstaculos chicos por arco (4 en total), tangentes a cada borde del
    arco desde afuera, a `x_guide` de la pared corta correspondiente --
    misma geometria que el "paragolpes" de la familia B, reusada aqui dentro
    de la zona libre de la familia C."""
    y_lo = width / 2 - goal_size / 2 - guide_radius
    y_hi = width / 2 + goal_size / 2 + guide_radius
    obstacles = []
    for goal_x, mirrored in ((0.0, False), (length, True)):
        x = goal_x + x_guide if not mirrored else goal_x - x_guide
        obstacles.append({"x": x, "y": y_lo, "radius": guide_radius})
        obstacles.append({"x": x, "y": y_hi, "radius": guide_radius})
    return obstacles


def family_c_layout(variant, length, width, goal_size,
                     free_radius=0.30, depth=FUNNEL_DEPTH, far_half_width=FUNNEL_FAR_HALF_WIDTH,
                     filler_radius=FILLER_RADIUS, margin_factor=MARGIN_FACTOR,
                     guide_radius=GUIDE_RADIUS, x_guide=X_GUIDE):
    """Arma la lista completa de obstaculos (relleno + guias, si aplica) para
    una de las variantes de la familia C: "semicircle" (la ya corrida),
    "funnel", "semicircle_guides" o "funnel_guides"."""
    if variant not in ("semicircle", "funnel", "semicircle_guides", "funnel_guides"):
        raise ValueError(f"variante desconocida: {variant}")

    guides = guide_obstacles(length, width, goal_size, guide_radius, x_guide) \
        if variant in ("semicircle_guides", "funnel_guides") else []

    def is_free(x, y):
        for goal_x, mirrored in ((0.0, False), (length, True)):
            if variant in ("semicircle", "semicircle_guides"):
                if math.hypot(x - goal_x, y - width / 2) <= free_radius:
                    return True
            else:
                if _funnel_free(x, y, goal_x, width, depth, far_half_width, goal_size, mirrored):
                    return True
        return False

    spacing = 2 * filler_radius * margin_factor
    candidates = _lattice(length, width, filler_radius, spacing)
    filler = []
    for x, y in candidates:
        if is_free(x, y):
            continue
        if any(math.hypot(x - g["x"], y - g["y"]) < filler_radius + g["radius"] + 1e-6 for g in guides):
            continue
        filler.append({"x": x, "y": y, "radius": filler_radius})
    return filler + guides


# --- Variante "elipse": el semicirculo (free_radius=0.30) es el mejor
# resultado medido hasta ahora, pero esta acotado por el ancho de la mesa
# (W/2=0.34 m): no puede crecer mas sin tocar las paredes horizontales. La
# mesa es bastante mas larga que ancha (L=1.20 vs W=0.68), asi que en vez de
# angostar la boca (el "funnel", que empeoro todo por crear un cuello de
# botella) se prueba estirar la cavidad en profundidad: una media elipse con
# el mismo semieje b que el semicirculo (no toca las paredes horizontales,
# sin cuello de botella en la boca -- el ancho en x=0 es igual, 2b) pero un
# semieje a mayor en la direccion longitudinal, dandole a las particulas mas
# area para no apianarse sin repetir el error del embudo.
ELLIPSE_B = 0.32  # mismo margen de seguridad que el semicirculo (W/2 - 0.02)


def goal_ellipse_layout(a, length, width, b=ELLIPSE_B,
                         filler_radius=FILLER_RADIUS, margin_factor=MARGIN_FACTOR):
    """Obstaculos de relleno para dejar libres dos medias elipses (semieje
    mayor `a` en x, semieje menor `b` en y) frente a cada arco. Con a=b se
    reduce al semicirculo de goal_semicircle_layout."""
    spacing = 2 * filler_radius * margin_factor
    candidates = _lattice(length, width, filler_radius, spacing)
    obstacles = []
    for x, y in candidates:
        free = False
        for goal_x, mirrored in ((0.0, False), (length, True)):
            xi = (goal_x - x) if mirrored else (x - goal_x)
            if 0 <= xi <= a and (xi / a) ** 2 + ((y - width / 2) / b) ** 2 <= 1:
                free = True
                break
        if not free:
            obstacles.append({"x": x, "y": y, "radius": filler_radius})
    return obstacles
