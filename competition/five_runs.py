import sys
from statistics import mean

try:
    from .run_competition import run_competition
except ImportError:
    from run_competition import run_competition


SEEDS = (708753, 4987748289618984079, 698814, 699183, 698897)


def format_t90(result):
    t90 = result["t90"]
    return f"{t90:.2f} s" if t90 is not None else "no alcanzado"


def main():
    results = []
    try:
        for index, seed in enumerate(SEEDS, start=1):
            print(f"\n----- corrida {index}/{len(SEEDS)} | seed: {seed} -----", flush=True)
            result = run_competition(seed, show_progress=True)
            results.append(result)
            print("=" * 40)
            print(f"CORRIDA {index}: t90 = {format_t90(result)}")
            print("=" * 40, flush=True)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print("\n----- resumen -----")
    for index, result in enumerate(results, start=1):
        print(f"Corrida {index}: t90 = {format_t90(result)}")

    reached = [result["t90"] for result in results if result["t90"] is not None]
    if len(reached) == len(SEEDS):
        print(f"\nPromedio de t90 ({len(SEEDS)} corridas): {mean(reached):.2f} s")
    else:
        print(f"\nPromedio de t90 de las 5 corridas: no definido; "
              f"{len(SEEDS) - len(reached)} no alcanzaron el 90% antes de tmax")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
