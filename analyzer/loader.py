import json
import os
from pathlib import Path


def load_file(path: str) -> dict:
    """Load a single analysis JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    filename = Path(path).name
    return {
        "filename": filename,
        "classification": _classify(filename),
        "data": data,
    }


def load_directory(directory: str) -> list[dict]:
    """Load all analysis JSON files from a directory."""
    files = sorted(Path(directory).glob("*.json"))
    return [load_file(str(f)) for f in files]


def load_files(paths: list[str]) -> list[dict]:
    """Load a specific list of files."""
    return [load_file(p) for p in paths]


def _classify(filename: str) -> str:
    """Classify file as light or heavy based on filename."""
    name = filename.lower()
    if name.startswith("light"):
        return "light"
    if name.startswith("heavy"):
        return "heavy"
    return "unknown"
