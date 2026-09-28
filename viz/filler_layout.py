import math

from hexagonal_packing import _lattice

FILLER_RADIUS = 0.02
MARGIN_FACTOR = 1.001


def goal_semicircle_layout(free_radius, length, width,
                            filler_radius=FILLER_RADIUS, margin_factor=MARGIN_FACTOR):
    spacing = 2 * filler_radius * margin_factor
    candidates = _lattice(length, width, filler_radius, spacing)
    goal_centers = [(0.0, width / 2), (length, width / 2)]
    obstacles = []
    for x, y in candidates:
        if all(math.hypot(x - gx, y - gy) >= free_radius + filler_radius for gx, gy in goal_centers):
            obstacles.append({"x": x, "y": y, "radius": filler_radius})
    return obstacles


FUNNEL_DEPTH = 0.45
FUNNEL_FAR_HALF_WIDTH = 0.30
GUIDE_RADIUS = 0.025
X_GUIDE = 0.10


def _funnel_free(x, y, goal_x, width, depth, far_half_width, goal_size, mirrored):
    xi = (goal_x - x) if mirrored else (x - goal_x)
    if not (0 <= xi <= depth):
        return False
    half_width = goal_size / 2 + (far_half_width - goal_size / 2) * (xi / depth)
    return abs(y - width / 2) <= half_width


def guide_obstacles(length, width, goal_size,
                     guide_radius=GUIDE_RADIUS, x_guide=X_GUIDE):
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


ELLIPSE_B = 0.32


def goal_ellipse_layout(a, length, width, b=ELLIPSE_B,
                         filler_radius=FILLER_RADIUS, margin_factor=MARGIN_FACTOR):
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
