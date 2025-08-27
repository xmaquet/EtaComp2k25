from pathlib import Path
import json
from typing import Type, TypeVar

from ..config.paths import get_data_dir
from ..models.comparator import Comparator
from ..models.session import Session

T = TypeVar("T", Comparator, Session)


def save_model(model: T, subdir: str, filename: str) -> Path:
    dest = get_data_dir() / subdir / filename
    dest.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    return dest


def load_model(cls: Type[T], subdir: str, filename: str) -> T:
    path = get_data_dir() / subdir / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    return cls.model_validate(data)
