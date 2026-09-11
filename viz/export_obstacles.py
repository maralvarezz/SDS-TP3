"""Genera el artefacto de entrega de la competencia (punto 24 del enunciado):
una linea "xk yk Rk" por obstaculo.

input/config.json sigue siendo la unica fuente de verdad. Si usa
"obstaclesFile" (ver ConfigLoader), ese archivo YA esta en el formato de
entrega exacto, asi que simplemente se copia. Si los obstaculos estan
embebidos inline en el array "obstacles", se los formatea al mismo formato.
En ningun caso este script se convierte en una fuente de verdad adicional.
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "input" / "config.json"
OUTPUT_PATH = ROOT / "competition_config.txt"


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    obstacles_file = config.get("obstaclesFile")
    if obstacles_file:
        source = (CONFIG_PATH.parent / obstacles_file).resolve()
        if not source.is_file():
            raise FileNotFoundError(f"obstaclesFile referenciado en config.json no existe: {source}")
        shutil.copyfile(source, OUTPUT_PATH)
    else:
        obstacles = config["obstacles"]
        if not obstacles:
            raise ValueError("input/config.json no tiene obstaculos (K debe ser > 0 para la competencia)")
        lines = [f"{o['x']:.3f} {o['y']:.3f} {o['radius']:.3f}" for o in obstacles]
        OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUTPUT_PATH)
    print(OUTPUT_PATH.read_text(encoding="utf-8"), end="")


if __name__ == "__main__":
    main()
