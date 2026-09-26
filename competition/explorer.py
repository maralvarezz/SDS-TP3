"""Explora un rango consecutivo de seeds y muestra las 5 mejores.

Uso:
    python competition/explorer.py <seed_inicial> <cantidad>
"""
import argparse
import sys

try:
    from .run_competition import integer, run_competition
except ImportError:
    from run_competition import integer, run_competition


TOP_COUNT = 5


def parse_args():
    parser = argparse.ArgumentParser(
        description="Explora seeds consecutivas de competencia y rankea las mejores 5 por t90.",
    )
    parser.add_argument("initial_seed", type=integer, help="Primera seed a evaluar")
    parser.add_argument("quantity", type=integer, help="Cantidad de seeds consecutivas a explorar")
    return parser.parse_args()


def explore_seeds(initial_seed, quantity):
    if quantity <= 0:
        raise ValueError("quantity debe ser positivo")

    results = []
    for offset in range(quantity):
        seed = initial_seed + offset
        print(f"Explorando seed {seed} ({offset + 1}/{quantity})...")
        result = run_competition(seed)
        results.append(result)

    return sorted(
        results,
        key=lambda item: (item["t90"] is None, item["t90"] if item["t90"] is not None else float("inf")),
    )[:TOP_COUNT]


def print_ranking(results):
    print("\n----- ranking -----")
    for position, result in enumerate(results, start=1):
        t90 = f"{result['t90']:.2f}" if result["t90"] is not None else "no alcanzado"
        print(f"{position}. seed: {result['seed']} | t90: {t90}")
    print("-------------------")


def main():
    args = parse_args()
    try:
        print_ranking(explore_seeds(args.initial_seed, args.quantity))
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
