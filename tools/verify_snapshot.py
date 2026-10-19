"""Vérifie les octets de l'étude importée, sans données brutes ni dépendances."""
from pathlib import Path
import hashlib
import json


def main():
    root = Path(__file__).resolve().parents[1]
    record = json.loads((root / "snapshots/fvg-import-2026-10-19.json").read_text(encoding="utf-8"))
    failures = []
    for name, expected in record["files"].items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            failures.append(name)
    if failures:
        raise SystemExit("FAIL: " + ", ".join(failures))
    print(f"PASS: {len(record['files'])} fichiers importés, SHA-256 identiques.")


if __name__ == "__main__":
    main()
