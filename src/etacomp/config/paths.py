from pathlib import Path

APP_DIRNAME = "EtaComp2K25"


def get_data_dir() -> Path:
    base = Path.home() / f".{APP_DIRNAME}"
    (base / "comparators").mkdir(parents=True, exist_ok=True)
    (base / "sessions").mkdir(parents=True, exist_ok=True)
    return base
