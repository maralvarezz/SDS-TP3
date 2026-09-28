import math

TOTAL_AREA_RADIUS = 0.15


def radius_for(k):
    return TOTAL_AREA_RADIUS / math.sqrt(k)


def layout(k, length, width):
    r = radius_for(k)
    y = width / 2
    center = length / 2
    if k == 1:
        centers_x = [center]
    elif k == 2:
        offset = length * 5 / 24
        centers_x = [center - offset, center + offset]
    elif k == 3:
        offset = length / 4
        centers_x = [center - offset, center, center + offset]
    else:
        raise ValueError(f"Layout no definido para K={k}")
    return [{"x": x, "y": y, "radius": r} for x in centers_x]


def validate_layout(obstacles, length, width, particle_radius):
    for o in obstacles:
        r = o["radius"]
        if r < particle_radius:
            raise ValueError(f"Restriccion (ii) violada: R={r} < r={particle_radius}")
        if not (r <= o["x"] <= length - r and r <= o["y"] <= width - r):
            raise ValueError(f"Restriccion (i) violada (fuera de dominio): {o}")
    for i in range(len(obstacles)):
        for j in range(i + 1, len(obstacles)):
            a, b = obstacles[i], obstacles[j]
            dist = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
            if dist < a["radius"] + b["radius"]:
                raise ValueError(f"Restriccion (i) violada (solapan): {a} vs {b}")
