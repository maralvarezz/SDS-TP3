"""Exporta los obstaculos de input/config.json al formato de entrega de la
competencia (punto 24 del enunciado): una linea "xk yk Rk" por obstaculo.

input/config.json sigue siendo la unica fuente de verdad; este archivo TXT es
solo un artefacto de entrega y no debe usarse como configuracion durante el
desarrollo.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
OUTPUT_PATH = ROOT / "competition_config.txt"


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    obstacles = config["obstacles"]
    if not obstacles:
        raise ValueError("input/config.json no tiene obstaculos (K debe ser > 0 para la competencia)")
    lines = [f"{o['x']:.3f} {o['y']:.3f} {o['radius']:.3f}" for o in obstacles]
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUTPUT_PATH)
    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
