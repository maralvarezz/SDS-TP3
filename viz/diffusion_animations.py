import json
import re
import shutil
import subprocess
from pathlib import Path

import animation
import diffusion

ROOT = diffusion.ROOT
CONFIG_PATH = diffusion.CONFIG_PATH
JAR = diffusion.JAR
OUTPUT_FOLDER = ROOT / "output" / "experiment_1_3_plots"


def slug(label):
    return re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_")


def build_animation_config(base, obstacles, seed):
    cfg = json.loads(json.dumps(base))
    cfg.pop("obstaclesFile", None)
    cfg.pop("initialPositionsFile", None)
    cfg["simulation"]["maxTime"] = diffusion.MAX_TIME
    cfg["simulation"]["seed"] = seed
    cfg["particles"]["count"] = diffusion.N
    cfg["output"] = {"everyEvents": diffusion.EVERY_EVENTS, "writeStates": True,
                      "writeGoals": True, "writeCollisions": False}
    cfg["obstacles"] = obstacles
    return cfg


def main():
    if not JAR.exists():
        raise FileNotFoundError(f"No se encontro el jar compilado: {JAR}. Ejecutar 'mvn -q clean package' primero")
    base = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    length = base["simulation"]["length"]
    width = base["simulation"]["width"]
    goal = base["simulation"]["goalSize"]
    original = CONFIG_PATH.read_text(encoding="utf-8")
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    results = {}
    try:
        for c, label in enumerate(diffusion.CONFIGS):
            seed = diffusion.BASE_SEED + c
            obstacles = diffusion.BUILDERS[label](length, width, goal)
            print(f"\n=== {label} (seed={seed}, K={len(obstacles)} obstaculos) ===")
            CONFIG_PATH.write_text(json.dumps(build_animation_config(base, obstacles, seed)), encoding="utf-8")
            print("  corriendo Java (puede tardar varios minutos con este config)...")
            result = subprocess.run(["java", "-jar", str(JAR)], cwd=ROOT, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Corrida fallida para {label}: {result.stderr.strip() or result.stdout.strip()}")
            print("  corrida OK, generando animacion (GIF)...")
            gif_path = animation.main()
            dest = OUTPUT_FOLDER / f"animation_{slug(label)}.gif"
            shutil.copyfile(gif_path, dest)
            results[label] = dest
            print(f"  {label}: {dest}")
    finally:
        CONFIG_PATH.write_text(original, encoding="utf-8")
        print("\ninput/config.json restaurado a su contenido original")
    print("\nResumen:")
    for label, path in results.items():
        print(f"  {label}: {path}")


if __name__ == "__main__":
    main()
