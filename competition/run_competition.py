"""Ejecuta una corrida de competencia con configuracion fija.

Uso:
    python competition/run_competition.py <seed>

La unica variacion admitida por este wrapper es la semilla. Puede recibirse
cualquier entero; si no entra en el rango long de Java se normaliza de forma
deterministica. Los parametros de competencia y la distribucion de obstaculos
salen de input/competition_config.json e input/obstacles.txt.
"""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPETITION_CONFIG_PATH = ROOT / "input" / "competition_config.json"
OBSTACLES_PATH = ROOT / "input" / "obstacles.txt"
JAR_PATH = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
JAVA_TIMEOUT_SECONDS = 25

COMPETITION_SIMULATION = {
    "length": 1.20,
    "width": 0.68,
    "goalSize": 0.20,
    "maxTime": 100.0,
}
COMPETITION_PARTICLES = {
    "count": 100,
    "radius": 0.0175,
    "mass": 0.025,
    "initialSpeed": 1.0,
}
COMPETITION_OUTPUT = {
    "everyEvents": 1_000_000,
    "writeStates": False,
    "writeGoals": True,
    "writeCollisions": False,
}
LONG_MIN = -(2**63)
LONG_RANGE = 2**64


def integer(value):
    try:
        return int(value, 10)
    except ValueError as error:
        raise argparse.ArgumentTypeError("la seed debe ser un entero") from error


def to_java_long(value):
    return ((value - LONG_MIN) % LONG_RANGE) + LONG_MIN


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ejecuta la simulacion de competencia usando solo la seed indicada.",
    )
    parser.add_argument("seed", type=integer, help="Semilla entera para el randomizer")
    return parser.parse_args()


def build_competition_config(seed):
    return {
        "simulation": {**COMPETITION_SIMULATION, "seed": seed},
        "particles": COMPETITION_PARTICLES,
        "output": COMPETITION_OUTPUT,
        "obstaclesFile": "obstacles.txt",
        "obstacles": [],
    }


def validate_inputs():
    if not JAR_PATH.is_file():
        raise FileNotFoundError(
            f"No se encontro el jar compilado: {JAR_PATH}. Ejecutar 'mvn clean package' primero."
        )
    if not OBSTACLES_PATH.is_file():
        raise FileNotFoundError(f"No se encontro la distribucion de competencia: {OBSTACLES_PATH}")


def one_file(directory, pattern):
    files = list(directory.glob(pattern))
    if len(files) != 1:
        raise RuntimeError(f"{directory}: se esperaba un archivo {pattern}, se encontraron {len(files)}")
    return files[0]


def run_directory_from_stdout(stdout):
    for line in stdout.splitlines():
        if line.startswith("Archivos: "):
            return Path(line[len("Archivos: "):].strip())
    raise RuntimeError("Java no informo la carpeta de salida")


def t90_from_goals(directory):
    with one_file(directory, "goals_*.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if float(row["usedFraction"]) >= 0.9:
                return float(row["time"])
    return None


def print_run_summary(directory):
    metadata = json.loads(one_file(directory, "metadata_*.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "COMPLETED":
        raise RuntimeError(f"La corrida no quedo completada: {directory}")

    t90 = t90_from_goals(directory)

    print("----- competencia -----")
    print(f"seed: {metadata['seed']}")
    print(f"t90: {t90:.2f}" if t90 is not None else "t90: no alcanzado")
    print("-----------------------")


def run_competition(seed):
    validate_inputs()
    java_seed = to_java_long(seed)
    competition_config = build_competition_config(java_seed)

    COMPETITION_CONFIG_PATH.write_text(json.dumps(competition_config, indent=2) + "\n", encoding="utf-8")
    try:
        result = subprocess.run(
            ["java", "-jar", str(JAR_PATH), str(COMPETITION_CONFIG_PATH.relative_to(ROOT))],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=JAVA_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"La corrida Java supero el limite de {JAVA_TIMEOUT_SECONDS} segundos"
        ) from error
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"La corrida fallo con codigo de salida {result.returncode}: {details}")
    print_run_summary(run_directory_from_stdout(result.stdout))


def main():
    args = parse_args()
    try:
        run_competition(args.seed)
    except (OSError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
