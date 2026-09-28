import math

SAFETY_MARGIN = 1e-6


def _row_count(width, radius, row_spacing):
    available = width - 2 * radius - SAFETY_MARGIN
    if available < 0:
        return 0
    return int(available / row_spacing) + 1


def _col_count(length, radius, spacing, offset):
    available = length - 2 * radius - offset - SAFETY_MARGIN
    if available < 0:
        return 0
    return int(available / spacing) + 1


def _count_for_spacing(length, width, radius, spacing):
    row_spacing = spacing * math.sqrt(3) / 2
    total = 0
    for row in range(_row_count(width, radius, row_spacing)):
        offset = spacing / 2 if row % 2 == 1 else 0.0
        total += _col_count(length, radius, spacing, offset)
    return total


def _lattice(length, width, radius, spacing):
    row_spacing = spacing * math.sqrt(3) / 2
    positions = []
    for row in range(_row_count(width, radius, row_spacing)):
        y = radius + row * row_spacing
        offset = spacing / 2 if row % 2 == 1 else 0.0
        for k in range(_col_count(length, radius, spacing, offset)):
            x = radius + offset + k * spacing
            positions.append((x, y))
    return positions


def max_count(length, width, radius, margin_factor=1.001):
    return _count_for_spacing(length, width, radius, 2 * radius * margin_factor)


def hexagonal_positions(length, width, radius, n, margin_factor=1.001):
    min_spacing = 2 * radius * margin_factor
    feasible_max = _count_for_spacing(length, width, radius, min_spacing)
    if n > feasible_max:
        raise ValueError(f"N={n} supera el maximo hexagonal para este dominio ({feasible_max})")
    low, high = min_spacing, max(length, width)
    for _ in range(60):
        mid = (low + high) / 2
        if _count_for_spacing(length, width, radius, mid) >= n:
            low = mid
        else:
            high = mid
    positions = _lattice(length, width, radius, low)[:n]
    for x, y in positions:
        if not (radius <= x <= length - radius and radius <= y <= width - radius):
            raise AssertionError(f"Posicion generada fuera de la mesa: ({x}, {y})")
    return positions


if __name__ == "__main__":
    for n in (50, 100, 200, 300, 400, 500, 600, 700):
        try:
            positions = hexagonal_positions(1.20, 0.68, 0.0175, n)
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            print(f"N={n}: {len(positions)} ok, x=[{min(xs):.4f},{max(xs):.4f}] y=[{min(ys):.4f},{max(ys):.4f}]")
        except ValueError as error:
            print(f"N={n}: {error}")
    print("maximo teorico:", max_count(1.20, 0.68, 0.0175))
