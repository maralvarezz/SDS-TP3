import argparse
import csv
import json
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "viz"))
from filler_layout import goal_semicircle_layout
from obstacle_layouts import validate_layout

COMPETITION_CONFIG_PATH = ROOT / "input" / "competition_config.json"
JAR_PATH = ROOT / "sims" / "target" / "sds_tp3_g8.jar"
JAVA_TIMEOUT_SECONDS = 25
POLL_SECONDS = 0.05
COMPETITION_FREE_RADIUS = 0.30

COMPETITION_SIMULATION = {
    "length": 1.20,
    "width": 0.68,
    "goalSize": 0.20,
    "maxTime": 40.0,
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
    parser.add_argument("seed", nargs="?", type=integer,
                        help="Semilla entera para el randomizer (aleatoria si se omite)")
    return parser.parse_args()


def build_competition_config(seed):
    obstacles = goal_semicircle_layout(
        COMPETITION_FREE_RADIUS,
        COMPETITION_SIMULATION["length"],
        COMPETITION_SIMULATION["width"],
    )
    validate_layout(
        obstacles,
        COMPETITION_SIMULATION["length"],
        COMPETITION_SIMULATION["width"],
        COMPETITION_PARTICLES["radius"],
    )
    return {
        "simulation": {**COMPETITION_SIMULATION, "seed": seed},
        "particles": COMPETITION_PARTICLES,
        "output": COMPETITION_OUTPUT,
        "obstacles": obstacles,
    }


def validate_inputs():
    if not JAR_PATH.is_file():
        raise FileNotFoundError(
            f"No se encontro el jar compilado: {JAR_PATH}. Ejecutar 'mvn clean package' primero."
        )


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


def read_run_result(directory):
    metadata = json.loads(one_file(directory, "metadata_*.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "COMPLETED":
        raise RuntimeError(f"La corrida no quedo completada: {directory}")

    t90 = t90_from_goals(directory)
    return {
        "seed": metadata["seed"],
        "t90": t90,
    }


def print_run_result(result, include_header=True):
    if include_header:
        print("----- competencia -----")
        print(f"seed: {result['seed']}")
    print(f"t90: {result['t90']:.2f}s" if result["t90"] is not None else "t90: no alcanzado")
    print("-----------------------")


def print_new_conversions(directory, printed, particle_count):
    files = list(directory.glob("goals_*.csv"))
    if not files:
        return printed
    contents = one_file(directory, "goals_*.csv").read_text(encoding="utf-8")
    complete = contents[:contents.rfind("\n") + 1]
    for row in csv.DictReader(complete.splitlines()):
        total = int(row["totalGoals"])
        if total > printed:
            print(f"convertidas: {total} / {particle_count}", flush=True)
            printed = total
    return printed


def run_competition(seed, show_progress=False):
    validate_inputs()
    java_seed = to_java_long(seed)
    competition_config = build_competition_config(java_seed)

    COMPETITION_CONFIG_PATH.write_text(json.dumps(competition_config, indent=2) + "\n", encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="competition_") as logs, \
            (Path(logs) / "stdout.txt").open("w", encoding="utf-8") as stdout, \
            (Path(logs) / "stderr.txt").open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(
            ["java", "-jar", str(JAR_PATH), str(COMPETITION_CONFIG_PATH.relative_to(ROOT))],
            cwd=ROOT,
            stdout=stdout,
            stderr=stderr,
        )
        started = time.monotonic()
        directory = None
        printed = 0
        try:
            while True:
                finished = process.poll() is not None
                if directory is None:
                    output = (Path(logs) / "stdout.txt").read_text(encoding="utf-8", errors="replace")
                    complete = output[:output.rfind("\n") + 1]
                    if any(line.startswith("Archivos: ") for line in complete.splitlines()):
                        directory = run_directory_from_stdout(complete)
                if show_progress and directory is not None:
                    printed = print_new_conversions(directory, printed, competition_config["particles"]["count"])
                if finished:
                    break
                if time.monotonic() - started >= JAVA_TIMEOUT_SECONDS:
                    raise RuntimeError(
                        f"La corrida Java supero el limite de {JAVA_TIMEOUT_SECONDS} segundos"
                    )
                time.sleep(POLL_SECONDS)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
        output = (Path(logs) / "stdout.txt").read_text(encoding="utf-8", errors="replace")
        if process.returncode != 0:
            details = (Path(logs) / "stderr.txt").read_text(encoding="utf-8", errors="replace").strip() or output.strip()
            raise RuntimeError(f"La corrida fallo con codigo de salida {process.returncode}: {details}")
        return read_run_result(run_directory_from_stdout(output))


def main():
    args = parse_args()
    seed = args.seed if args.seed is not None else to_java_long(secrets.randbits(64))
    try:
        print("----- competencia -----", flush=True)
        print(f"seed: {to_java_long(seed)}", flush=True)
        print_run_result(run_competition(seed, show_progress=True), include_header=False)
    except (OSError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
