"""Lectura compartida de outputs Java; no contiene calculos fisicos."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def latest_run():
    return load_run(output=ROOT / "output")


def one_file(run, pattern):
    files = list(run.glob(pattern))
    if len(files) != 1:
        raise ValueError(f"{run}: se esperaba un archivo {pattern}, se encontraron {len(files)}")
    return files[0]


def rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        yield from csv.DictReader(stream)


def load_run(run=None, output=Path("output")):
    if run is None:
        candidates = []
        for path in output.glob("*/metadata_*.json"):
            metadata = json.loads(path.read_text(encoding="utf-8"))
            if metadata.get("status") == "COMPLETED":
                candidates.append((metadata["timestamp"], path.parent))
        if not candidates:
            raise ValueError("No hay corridas completadas")
        run = max(candidates)[1]
    metadata = json.loads(one_file(run, "metadata_*.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "COMPLETED":
        raise ValueError("La corrida no esta completada")
    return run, metadata
